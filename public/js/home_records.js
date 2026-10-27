// Standings page > "Tournament records" section. Reuses the Records tab engine (records.js: recBuild, recStats, recTop, recStandRows).
// Needs globals defined on index.html: TEAMS, PLAYERS, SEASONS, isPlaceholder, tname, pname, tlink, plink.
async function loadHomeRecords(seasonId) {
  var box = document.getElementById("home-records");
  if (!box) return;
  var all = seasonId === "all";
  var mq = window.sb.from("matches").select("*"), rq = window.sb.from("team_season_rosters").select("*");
  if (!all) { mq = mq.eq("season_id", seasonId); rq = rq.eq("season_id", seasonId); }
  var res = await Promise.all([mq, rq, window.sb.from("players").select("id, full_name")]);
  var matches = res[0].data || [], roster = res[1].data || [];
  PLAYERS = {}; (res[2].data || []).forEach(function (p) { PLAYERS[p.id] = p; });
  var ids = matches.map(function (m) { return m.id; });
  var apps = ids.length ? await recFetchAll("match_appearances", ids) : [];
  var events = ids.length ? await recFetchAll("match_events", ids) : [];
  REC.team = "all"; REC.minM = 1; REC.sort = null; REC.shoot = null;
  REC.data = recBuild(matches, roster, apps, events);
  renderHomeRecords(matches, all);
}

function hrBoard(title, icon, def, color) {
  var top = recTop(def, 5), total = recTop(def, 9999).length, mx = top.length ? def.val(top[0].r) : 1;
  var h = '<div class="card hr-card"><div class="card-title" style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;"><span>' + icon + " " + title + '</span><a class="hr-all" href="stats.html#records">All &rarr;</a></div>';
  if (!top.length) return h + '<p class="muted" style="margin:0;">Nothing recorded yet.</p></div>';
  top.forEach(function (x) {
    var v = def.val(x.r);
    h += '<div class="hr-lead"><div class="hr-rk' + (x.rank === 1 ? " one" : "") + '">' + (x.tied ? "T" : "") + x.rank + '</div><div class="hr-who">' + plink(x.r.id) + "<small>" + tlink(x.r.team_id) + '</small><div class="hr-bar"><i style="width:' + (mx ? v / mx * 100 : 0) + '%;background:' + color + '"></i></div></div><div class="hr-n" style="color:' + color + '">' + v + "</div></div>";
  });
  if (total > top.length) h += '<div class="muted" style="font-size:.72rem;margin-top:8px;">+' + (total - top.length) + " more on the full list (tied on the same total). T = tied.</div>";
  return h + "</div>";
}

function hrRec(label, html, big) {
  return '<div class="hr-rec"><div><div class="hr-k">' + label + '</div><div class="hr-v">' + html + '</div></div><div class="hr-big">' + big + "</div></div>";
}

function renderHomeRecords(matches, all) {
  var box = document.getElementById("home-records"), D = REC.data, S = recStats();
  if (!D.done.length) { box.innerHTML = '<div class="hr-head">Tournament records</div><div class="card"><p class="muted" style="margin:0;">Records appear after the first result.</p></div>'; return; }
  var rows = recStandRows();
  var goals = D.done.reduce(function (s, m) { return s + m.home_score + m.away_score; }, 0), n = D.done.length;
  var cs = rows.reduce(function (s, r) { return s + r.cs; }, 0);
  var goalless = D.done.filter(function (m) { return m.home_score === 0 && m.away_score === 0; });
  var total = matches.length, lastDay = Math.max.apply(null, D.done.map(function (m) { return m.match_day; })), maxDay = Math.max.apply(null, matches.map(function (m) { return m.match_day; }));
  var tiles = [[n, "matches played"], [goals, "goals"], [(goals / n).toFixed(2), "goals per match"], [cs, "clean sheets"]].map(function (t) { return '<div class="hr-tile"><b>' + t[0] + "</b><span>" + t[1] + "</span></div>"; }).join("");
  var glance = '<div class="card"><div class="card-title">Tournament at a glance</div><div class="hr-tiles">' + tiles + "</div>" +
    (all ? "" : '<div class="hr-prog"><i style="width:' + Math.min(100, n / total * 100) + '%"></i></div><div class="muted" style="font-size:.72rem;">' + n + " of " + total + " matches played &middot; Match Day " + lastDay + " of " + maxDay + " &middot; " + goalless.length + " goalless draw" + (goalless.length === 1 ? "" : "s") + "</div>") + "</div>";
  // team records (ties listed together)
  var best = function (f, asc) {
    var v = rows.slice().sort(function (a, b) { return asc ? f(a) - f(b) : f(b) - f(a); });
    if (!v.length) return { v: 0, teams: [] };
    var top = f(v[0]);
    return { v: top, teams: v.filter(function (r) { return f(r) === top; }) };
  };
  var tl = function (b) { return b.teams.map(function (r) { return tlink(r.id); }).join(", "); };
  var tr = [["Best attack", best(function (r) { return r.gf; })], ["Best defence", best(function (r) { return r.ga; }, true)], ["Most clean sheets", best(function (r) { return r.cs; })],
    ["Best goal difference", best(function (r) { return r.gd; })], ["Most wins", best(function (r) { return r.w; })], ["Most draws", best(function (r) { return r.d; })]];
  var teamRec = !rows.length ? "" : '<div class="card"><div class="card-title">Team records</div>' + tr.map(function (x) { return hrRec(x[0], tl(x[1]), (x[0] === "Best goal difference" && x[1].v > 0 ? "+" : "") + x[1].v); }).join("") + "</div>";
  // match records
  var line = function (m) { return tlink(m.home_team_id) + " " + matchLink(m, m.home_score + "–" + m.away_score) + " " + tlink(m.away_team_id); };
  var more = function (arr, f) { return arr.slice(0, 2).map(f).join("<br>") + (arr.length > 2 ? '<br><span class="muted">+' + (arr.length - 2) + " more with the same margin</span>" : ""); };
  var maxMargin = Math.max.apply(null, D.done.map(function (m) { return Math.abs(m.home_score - m.away_score); }));
  var bw = D.done.filter(function (m) { return Math.abs(m.home_score - m.away_score) === maxMargin; });
  var maxGoals = Math.max.apply(null, D.done.map(function (m) { return m.home_score + m.away_score; }));
  var hs = D.done.filter(function (m) { return m.home_score + m.away_score === maxGoals; });
  var timed = D.events.filter(function (e) { return (e.event_type === "goal" || e.event_type === "own_goal") && e.minute != null && D.M[e.match_id]; });
  var tt = function (e) { return e.minute * 60 + (e.second || 0); }, ft = function (e) { return e.second != null ? e.minute + ":" + (e.second < 10 ? "0" : "") + e.second : e.minute + "'"; };
  var fast = timed.slice().sort(function (a, b) { return tt(a) - tt(b); })[0], late = timed.slice().sort(function (a, b) { return tt(b) - tt(a); })[0];
  var gl = function (e) { return plink(e.player_id) + ' <span class="muted">' + tname(D.M[e.match_id].home_team_id) + " v " + tname(D.M[e.match_id].away_team_id) + " &middot; " + matchLink(D.M[e.match_id]) + "</span>"; };
  var matchRec = '<div class="card"><div class="card-title">Match records</div>' +
    (maxMargin > 0 ? hrRec("Biggest win", more(bw, line), "+" + maxMargin) : "") + (maxGoals > 0 ? hrRec("Highest-scoring match", more(hs, line), maxGoals) : "") +
    (fast ? hrRec("Fastest goal", gl(fast), ft(fast)) : "") + (late ? hrRec("Latest goal", gl(late), ft(late)) : "") +
    hrRec("Goalless draws", '<span class="muted">' + goalless.length + " of " + n + " matches</span>", goalless.length) + "</div>";
  box.innerHTML = '<div class="hr-head">Tournament records</div><div class="muted hr-sub">Live from every result. Tap any name for the full profile; <a href="stats.html#records">see all records &rarr;</a></div>' + glance +
    '<div class="hr-grid">' + hrBoard("Golden Boot", "&#129351;", S.goals, "var(--ev-goal)") + hrBoard("Top playmakers", "&#127919;", S.assists, "var(--ev-assist)") + hrBoard("Player of the match", "&#11088;", S.potm, "var(--amber)") + hrBoard("Goal contributions", "&#128293;", S.contrib, "#8EE0B0") + "</div>" +
    '<div class="hr-grid">' + teamRec + matchRec + "</div>";
}
