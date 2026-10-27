// Rivalry tab (Stats > Rivalry): pick two teams, see their head-to-head, and a preview of the next meeting.
// Uses helpers from stats.html / common.js: TEAMS, PLAYERS, SEASONS, isPlaceholder, escapeHtml, playerLink, matchLink,
// teamLink, formatKickoff, recFetchAll (records.js).
var RIV = { loaded: false, loading: false, matches: [], events: [], a: null, b: null };

function rivSort(a, b) {
  var sa = SEASONS.findIndex(function (s) { return s.id === a.season_id; }), sb = SEASONS.findIndex(function (s) { return s.id === b.season_id; });
  if (sa !== sb) return sb - sa;   // SEASONS is newest first, so higher index = older
  return (a.match_day - b.match_day) || (a.match_number - b.match_number);
}
function rivDone(m) { return m.status === "completed" && m.home_score != null && m.away_score != null; }
function rivTeams() {
  var seen = {};
  RIV.matches.forEach(function (m) { [m.home_team_id, m.away_team_id].forEach(function (id) { if (TEAMS[id] && !isPlaceholder(TEAMS[id])) seen[id] = true; }); });
  return Object.keys(seen).sort(function (x, y) { return TEAMS[x].name.localeCompare(TEAMS[y].name); });
}
function rivCode(id) { return (TEAMS[id] ? TEAMS[id].name : "?").split(/\s+/)[0].slice(0, 3); }
function rivLogo(id, px) {
  var t = TEAMS[id] || { name: "?" };
  if (t.crest_url) return '<img src="' + escapeHtml(t.crest_url) + '" alt="" style="width:' + px + 'px;height:' + px + 'px;object-fit:contain;">';
  return '<span class="rv-ph" style="width:' + px + 'px;height:' + px + 'px;font-size:' + Math.round(px / 2.4) + 'px;">' + escapeHtml(t.name.charAt(0)) + "</span>";
}
function rivFor(m, t) { return m.home_team_id === t ? m.home_score : m.away_score; }
function rivRes(m, t) {
  var o = m.home_team_id === t ? m.away_team_id : m.home_team_id, f = rivFor(m, t), a = rivFor(m, o);
  return f > a ? "W" : f < a ? "L" : "D";
}

async function loadRivalry() {
  document.getElementById("riv-out").innerHTML = '<p class="muted">Loading…</p>';
  var sid = document.getElementById("riv-season").value, all = sid === "all";
  var mq = window.sb.from("matches").select("*");
  if (!all) mq = mq.eq("season_id", sid);
  var res = await mq;
  RIV.matches = (res.data || []).slice().sort(rivSort);
  var ids = RIV.matches.map(function (m) { return m.id; });
  RIV.events = ids.length ? await recFetchAll("match_events", ids) : [];
  RIV.loaded = true;
  var ok = rivTeams();
  if (ok.indexOf(RIV.a) < 0) RIV.a = null;
  if (ok.indexOf(RIV.b) < 0) RIV.b = null;
  if (!RIV.a && RIV.b) { RIV.a = RIV.b; RIV.b = null; }
  rivHash();
  renderRivalry();
}

function rivPick(id) {
  if (RIV.a === id) { RIV.a = RIV.b; RIV.b = null; }
  else if (RIV.b === id) RIV.b = null;
  else if (!RIV.a) RIV.a = id;
  else RIV.b = id;   // a third tap replaces Team B
  rivHash();
  renderRivalry();
}
function rivHash() {
  try { history.replaceState(null, "", "#rivalry" + (RIV.a ? "/" + RIV.a + (RIV.b ? "/" + RIV.b : "") : "")); } catch (e) {}
}

// Poisson goals model for the preview: each team's attack and defence from the completed matches, shrunk toward the league average.
function rivModel(a, b) {
  var done = RIV.matches.filter(function (m) { return rivDone(m) && TEAMS[m.home_team_id] && TEAMS[m.away_team_id] && !isPlaceholder(TEAMS[m.home_team_id]) && !isPlaceholder(TEAMS[m.away_team_id]); });
  if (!done.length) return null;
  var gf = {}, ga = {}, n = {}, tot = 0, K = 6;
  done.forEach(function (m) {
    [[m.home_team_id, m.home_score, m.away_score], [m.away_team_id, m.away_score, m.home_score]].forEach(function (x) {
      gf[x[0]] = (gf[x[0]] || 0) + x[1]; ga[x[0]] = (ga[x[0]] || 0) + x[2]; n[x[0]] = (n[x[0]] || 0) + 1; tot += x[1];
    });
  });
  var avg = tot / (2 * done.length);
  if (!(avg > 0)) return null;
  var att = function (t) { return ((gf[t] || 0) + K * avg) / ((n[t] || 0) + K) / avg; };
  var def = function (t) { return ((ga[t] || 0) + K * avg) / ((n[t] || 0) + K) / avg; };
  var la = avg * att(a) * def(b), lb = avg * att(b) * def(a);
  var pois = function (l, k) { var p = Math.exp(-l); for (var i = 1; i <= k; i++) p *= l / i; return p; };
  var w = 0, d = 0, l = 0;
  for (var i = 0; i < 14; i++) for (var j = 0; j < 14; j++) { var p = pois(la, i) * pois(lb, j); if (i > j) w += p; else if (i === j) d += p; else l += p; }
  var s = w + d + l, pw = Math.round(w / s * 100), pl = Math.round(l / s * 100);
  return { w: pw, d: 100 - pw - pl, l: pl, games: done.length };
}

function rivPairAssists(evs) {
  var used = {}, ga = {}, ass = evs.filter(function (e) { return e.event_type === "assist"; });
  var goals = evs.filter(function (e) { return e.event_type === "goal" || e.event_type === "own_goal"; });
  goals.forEach(function (g) {
    var h = ass.filter(function (a) { return !used[a.id] && ((g.related_player_id && a.player_id === g.related_player_id) || a.related_player_id === g.player_id); })[0];
    if (h) { used[h.id] = 1; ga[g.id] = h; }
  });
  goals.forEach(function (g) {
    if (ga[g.id]) return;
    var og = g.event_type === "own_goal";
    var h = ass.filter(function (a) { return !used[a.id] && (og ? a.team_id !== g.team_id : a.team_id === g.team_id) && a.player_id !== g.player_id; })[0];
    if (h) { used[h.id] = 1; ga[g.id] = h; }
  });
  return ga;
}

function rivRow(lab, a, b, fmt, lowerBetter) {
  var fa = fmt ? fmt(a) : a, fb = fmt ? fmt(b) : b, mx = Math.max(a, b) || 1;
  var wa = a !== b && (lowerBetter ? a < b : a > b), wb = a !== b && (lowerBetter ? b < a : b > a);
  return '<div class="rv-cr"><div class="rv-side l"><span class="rv-v ' + (wa || a === b ? "win" : "lose") + '">' + fa + '</span><div class="rv-bar"><i style="width:' + (a / mx * 100) + '%;background:var(--rv-a);opacity:' + (wa || a === b ? 1 : 0.45) + '"></i></div></div>' +
    '<div class="rv-lab">' + lab + '</div><div class="rv-side"><div class="rv-bar"><i style="width:' + (b / mx * 100) + '%;background:var(--rv-b);opacity:' + (wb || a === b ? 1 : 0.45) + '"></i></div><span class="rv-v ' + (wb || a === b ? "win" : "lose") + '">' + fb + "</span></div></div>";
}

function renderRivalry() {
  if (!RIV.loaded) return;
  var ids = rivTeams(), A = RIV.a, B = RIV.b;
  var pk = document.getElementById("riv-picker"), msg = document.getElementById("riv-msg"), out = document.getElementById("riv-out");
  if (!ids.length) { pk.innerHTML = ""; msg.innerHTML = ""; out.innerHTML = '<div class="card rv-empty">No matches in this season yet.</div>'; return; }
  pk.innerHTML = ids.map(function (id) {
    var cls = A === id ? "a" : B === id ? "b" : "";
    return '<button type="button" class="rv-tm ' + cls + '" data-team="' + id + '">' + (cls ? '<div class="rv-tag">TEAM ' + cls.toUpperCase() + "</div>" : "") + rivLogo(id, 64) + "<span>" + escapeHtml(TEAMS[id].name) + "</span></button>";
  }).join("");
  msg.innerHTML = !A ? '<div class="rv-msg">Tap the first team to start.</div>'
    : !B ? '<div class="rv-msg"><b>' + escapeHtml(TEAMS[A].name) + "</b>&nbsp;selected. Now select another team to compare against.</div>"
    : '<div class="rv-msg ok"><b>' + escapeHtml(TEAMS[A].name) + "</b>&nbsp;vs&nbsp;<b>" + escapeHtml(TEAMS[B].name) + '</b>&nbsp;&middot; tap a team to change it <a href="#" id="riv-reset" style="margin-left:auto;">Reset</a></div>';
  if (!A || !B) { out.innerHTML = '<div class="card rv-empty"><div class="rv-vs">VS</div><div>' + (!A ? "Pick two teams to see their head-to-head." : "Pick one more team.") + "</div></div>"; return; }

  var pair = function (m) { return (m.home_team_id === A && m.away_team_id === B) || (m.home_team_id === B && m.away_team_id === A); };
  var ms = RIV.matches.filter(function (m) { return pair(m) && rivDone(m); });
  var upcoming = RIV.matches.filter(function (m) { return pair(m) && !rivDone(m) && m.status !== "cancelled"; });
  var mid = {}; ms.forEach(function (m) { mid[m.id] = true; });
  var evs = RIV.events.filter(function (e) { return mid[e.match_id]; });
  var wa = 0, wb = 0, dr = 0, ga = 0, gb = 0, csa = 0, csb = 0;
  ms.forEach(function (m) {
    var x = rivFor(m, A), y = rivFor(m, B); ga += x; gb += y;
    if (x > y) wa++; else if (y > x) wb++; else dr++;
    if (y === 0) csa++; if (x === 0) csb++;
  });
  var c = { yc: [0, 0], rc: [0, 0], fl: [0, 0], as: [0, 0], po: [0, 0] }, sc = {}, pm = {};
  var add = function (k, t) { c[k][t === A ? 0 : 1]++; };
  evs.forEach(function (e) {
    if (e.team_id !== A && e.team_id !== B) return;
    if (e.event_type === "yellow_card") add("yc", e.team_id);
    else if (e.event_type === "red_card") add("rc", e.team_id);
    else if (e.event_type === "foul") add("fl", e.team_id);
    else if (e.event_type === "assist") add("as", e.team_id);
    else if (e.event_type === "player_of_match") { add("po", e.team_id); var k = e.team_id + "|" + e.player_id; pm[k] = (pm[k] || 0) + 1; }
    else if (e.event_type === "goal") { var k2 = e.team_id + "|" + e.player_id; sc[k2] = (sc[k2] || 0) + 1; }
  });
  var n = ms.length, lead = wa > wb ? A : wb > wa ? B : null, nm = function (id) { return escapeHtml(TEAMS[id].name); };
  var verdict = !n ? "They have not met yet this season."
    : lead ? "<b>" + nm(lead) + "</b> lead the rivalry " + Math.max(wa, wb) + "–" + Math.min(wa, wb) + (dr ? " with " + dr + " draw" + (dr > 1 ? "s" : "") : "") + "."
    : dr === n ? "Every meeting so far has ended level – <b>nothing between them</b>."
    : "<b>All square</b> – " + wa + " win" + (wa > 1 ? "s" : "") + " each" + (dr ? " and " + dr + " draw" + (dr > 1 ? "s" : "") : "") + ".";
  var top = function (map, t) {
    return Object.keys(map).filter(function (k) { return k.split("|")[0] === t; }).map(function (k) { return [k.split("|")[1], map[k]]; })
      .sort(function (x, y) { return y[1] - x[1] || (PLAYERS[x[0]] ? PLAYERS[x[0]].full_name : "").localeCompare(PLAYERS[y[0]] ? PLAYERS[y[0]].full_name : ""); });
  };
  var list = function (arr) {
    return arr.length ? arr.slice(0, 3).map(function (x) { return '<div class="rv-pr"><span>' + plink(x[0]) + "</span><b>" + x[1] + "</b></div>"; }).join("") : '<div class="rv-pr"><span class="muted">None yet</span><b>–</b></div>';
  };
  var col = function (t) {
    return '<div class="rv-col"><h3>' + rivLogo(t, 22) + teamLink(t, TEAMS[t].name) + '</h3><div class="rv-lbl" style="margin:6px 0 2px">Scorers</div>' + list(top(sc, t)) +
      '<div class="rv-lbl" style="margin:10px 0 2px">Player of the match</div>' + list(top(pm, t)) + "</div>";
  };
  var meet = ms.map(function (m) {
    var me = evs.filter(function (e) { return e.match_id === m.id; }), pa = rivPairAssists(me), bits = [];
    me.forEach(function (e) {
      if (e.event_type === "goal") { var as = pa[e.id]; bits.push('<span><i class="evm goal"></i>' + plink(e.player_id) + (as ? ' <i class="evm assist" style="margin-left:6px"></i>' + plink(as.player_id) : "") + "</span>"); }
      else if (e.event_type === "own_goal") bits.push('<span><i class="evm og"></i>' + plink(e.player_id) + " (og)</span>");
      else if (e.event_type === "yellow_card") bits.push('<span><i class="evm yellow"></i>' + plink(e.player_id) + "</span>");
      else if (e.event_type === "red_card") bits.push('<span><i class="evm red"></i>' + plink(e.player_id) + "</span>");
    });
    var r = rivRes(m, A), pill = r === "W" ? rivCode(A) + " won" : r === "L" ? rivCode(B) + " won" : "Draw";
    var hl = r === "D" ? "D" : "W";
    return '<div class="rv-mt"><div class="rv-top"><span>' + matchLink(m) + '</span><span class="rv-pill ' + hl + '">' + escapeHtml(pill) + "</span></div>" +
      '<div class="rv-sc"><div class="rv-t">' + rivLogo(m.home_team_id, 26) + teamLink(m.home_team_id, TEAMS[m.home_team_id].name) + '</div><div class="rv-n">' + m.home_score + " – " + m.away_score +
      '</div><div class="rv-t r">' + teamLink(m.away_team_id, TEAMS[m.away_team_id].name) + rivLogo(m.away_team_id, 26) + '</div></div><div class="rv-ev">' + (bits.length ? bits.join("") : "<span>No goals · 0–0</span>") + "</div></div>";
  }).join("") || '<p class="muted" style="margin:0;">No completed meetings yet.</p>';

  var rec = function (t) {
    var w = 0, d = 0, l = 0;
    RIV.matches.filter(function (m) { return rivDone(m) && (m.home_team_id === t || m.away_team_id === t); }).forEach(function (m) { var r = rivRes(m, t); if (r === "W") w++; else if (r === "D") d++; else l++; });
    return w + "W " + d + "D " + l + "L";
  };
  var form = function (t) {
    var l = RIV.matches.filter(function (m) { return rivDone(m) && (m.home_team_id === t || m.away_team_id === t); }).slice(-5).reverse();
    return l.length ? l.map(function (m) { var r = rivRes(m, t); return '<span class="rv-pill ' + r + '">' + r + "</span>"; }).join("") : '<span class="muted">No matches yet</span>';
  };
  var total = n + upcoming.length;
  var next = upcoming.map(function (m, i) {
    return '<div class="rv-nx"><div><b>Meeting ' + (n + i + 1) + " of " + total + "</b> &middot; " + matchLink(m) + "<br><small>" + (m.kickoff_at ? escapeHtml(formatKickoff(m.kickoff_at)) : "Kickoff time to be confirmed") + '</small></div><span class="rv-pill U">UPCOMING</span></div>';
  }).join("") || '<p class="muted" style="margin:0;">No more meetings scheduled.</p>';
  var pr = upcoming.length ? rivModel(A, B) : null, preview = "";
  if (pr) {
    preview = '<div class="rv-idea"><b>MATCH PREVIEW.</b> Model estimate for ' + matchLabelShort(upcoming[0]) + ", from only " + pr.games + ' completed matches – treat it as a coin flip, not a forecast.' +
      '<div class="rv-pb"><div style="background:var(--rv-a);flex:' + pr.w + '">' + pr.w + '%</div><div style="background:#8a8a90;flex:' + pr.d + '">' + pr.d + '%</div><div style="background:var(--rv-b);flex:' + pr.l + '">' + pr.l + '%</div></div>' +
      '<div class="rv-splitl"><span>' + nm(A) + " win</span><span>Draw</span><span>" + nm(B) + " win</span></div></div>";
  }
  var f = function (x) { return x.toFixed(1); };
  out.innerHTML =
    '<div class="card"><div class="rv-lbl">Head to head &middot; ' + n + " meeting" + (n === 1 ? "" : "s") + '</div>' +
    '<div class="rv-hero"><div>' + rivLogo(A, 84) + '<div class="rv-nm" style="color:var(--rv-a)">' + teamLink(A, TEAMS[A].name) + '</div><div class="rv-rec">Record ' + rec(A) + "</div></div>" +
    '<div><div class="rv-big"><span class="' + (wa >= wb ? "la" : "") + '">' + wa + "</span><i>–</i><span class=\"" + (wb >= wa ? "lb" : "") + '">' + wb + '</span></div><div class="rv-sub">wins · ' + dr + " draw" + (dr === 1 ? "" : "s") + '</div><div class="rv-sub" style="margin-top:6px"><b style="color:var(--chalk-white)">' + ga + " – " + gb + "</b> goals</div></div>" +
    "<div>" + rivLogo(B, 84) + '<div class="rv-nm" style="color:var(--rv-b)">' + teamLink(B, TEAMS[B].name) + '</div><div class="rv-rec">Record ' + rec(B) + "</div></div></div>" +
    '<div class="rv-split"><div style="flex:' + (wa || 0.0001) + ';background:var(--rv-a)"></div><div style="flex:' + (dr || 0.0001) + ';background:#6b6b70"></div><div style="flex:' + (wb || 0.0001) + ';background:var(--rv-b)"></div></div>' +
    '<div class="rv-splitl"><span>' + rivCode(A) + " " + wa + "</span><span>Draws " + dr + "</span><span>" + wb + " " + rivCode(B) + '</span></div><div class="rv-verdict">' + verdict + "</div></div>" +
    '<div class="card"><div class="rv-lbl">Side by side</div>' + rivRow("Wins", wa, wb) + rivRow("Draws", dr, dr) + rivRow("Goals", ga, gb) +
    rivRow("Goals / match", n ? ga / n : 0, n ? gb / n : 0, f) + rivRow("Clean sheets", csa, csb) + rivRow("Assists", c.as[0], c.as[1]) + rivRow("Player of match", c.po[0], c.po[1]) +
    rivRow("Yellow cards", c.yc[0], c.yc[1], null, true) + (c.rc[0] + c.rc[1] ? rivRow("Red cards", c.rc[0], c.rc[1], null, true) : "") + rivRow("Fouls", c.fl[0], c.fl[1], null, true) + "</div>" +
    '<div class="card"><div class="rv-lbl">Every meeting</div>' + meet + "</div>" +
    '<div class="card"><div class="rv-lbl">Heroes of this rivalry</div><div class="rv-pl">' + col(A) + col(B) + "</div></div>" +
    '<div class="card"><div class="rv-lbl">Current form (last 5, newest first)</div><div class="rv-fm"><div><div class="rv-fn" style="color:var(--rv-a)">' + nm(A) + '</div><div class="rv-form">' + form(A) + '</div></div><div><div class="rv-fn" style="color:var(--rv-b)">' + nm(B) + '</div><div class="rv-form">' + form(B) + "</div></div></div></div>" +
    '<div class="card"><div class="rv-lbl">Still to come</div>' + next + preview + "</div>";
}

function initRivalry(seasonOpts) {
  document.getElementById("riv-season").innerHTML = seasonOpts + '<option value="all">All seasons (career)</option>';
  document.getElementById("riv-season").addEventListener("change", function () { loadRivalry(); });
  document.getElementById("riv-picker").addEventListener("click", function (ev) { var b = ev.target.closest("button[data-team]"); if (b) rivPick(b.dataset.team); });
  document.getElementById("riv-msg").addEventListener("click", function (ev) {
    if (ev.target.id === "riv-reset") { ev.preventDefault(); RIV.a = RIV.b = null; rivHash(); renderRivalry(); }
  });
  // deep link: #rivalry/<teamA id>/<teamB id>
  var m = /^#rivalry\/([^\/]+)(?:\/([^\/]+))?/.exec(location.hash || "");
  if (m) { RIV.a = m[1]; RIV.b = m[2] || null; }
}
