// Records tab (Stats > Records): Top 5 hub, full leaderboards, team records, match records, captains.
// Uses helpers defined in stats.html / common.js: TEAMS, PLAYERS, SEASONS, tname, pname, tlink, plink, isPlaceholder,
// escapeHtml, matchLink, teamLink, playerLink, matchLabelShort.
var REC = { loaded: false, data: null, view: "hub", team: "all", minM: 2, sort: null };

var REC_MENU = [
  ["Player records", [["goals", "Goals"], ["assists", "Assists"], ["contrib", "Goal contributions"], ["potm", "Player of the match"], ["discipline", "Cards & fouls"], ["avail", "Availability"]]],
  ["Team records", [["teams", "Results summary"], ["teamdisc", "Discipline"]]],
  ["Match records", [["matchrec", "Match records"]]],
  ["Individual", [["captains", "Captains"]]]
];

async function recFetchAll(table, matchIds) {
  var out = [], CH = 150;
  for (var i = 0; i < matchIds.length; i += CH) {
    var ids = matchIds.slice(i, i + CH), from = 0;
    for (;;) {
      var r = await window.sb.from(table).select("*").in("match_id", ids).range(from, from + 999);
      var d = r.data || [];
      out = out.concat(d);
      if (d.length < 1000) break;
      from += 1000;
    }
  }
  return out;
}

async function loadRecords() {
  var box = document.getElementById("rec-body");
  box.innerHTML = '<p class="muted">Loading…</p>';
  var sid = document.getElementById("rec-season").value, all = sid === "all";
  var mq = window.sb.from("matches").select("*"), rq = window.sb.from("team_season_rosters").select("*");
  if (!all) { mq = mq.eq("season_id", sid); rq = rq.eq("season_id", sid); }
  var res = await Promise.all([mq, rq]);
  var matches = res[0].data || [], roster = res[1].data || [];
  REC.shoot = null;
  if (!all && matches.length && !matches.some(function (m) { return m.status === "scheduled" || m.status === "postponed"; })) {
    var so = await window.sb.from("tiebreak_shootout_order").select("*").eq("season_id", sid);
    if (!so.error) { REC.shoot = {}; (so.data || []).forEach(function (r) { REC.shoot[r.team_id] = r.position; }); }
  }
  var ids = matches.map(function (m) { return m.id; });
  var apps = ids.length ? await recFetchAll("match_appearances", ids) : [];
  var events = ids.length ? await recFetchAll("match_events", ids) : [];
  REC.data = recBuild(matches, roster, apps, events);
  REC.loaded = true;
  var seen = {};
  REC.data.teams.forEach(function (t) { seen[t.id] = true; });
  var keep = REC.team;
  var opts = Object.keys(seen).sort(function (a, b) { return tname(a).localeCompare(tname(b)); });
  document.getElementById("rec-team").innerHTML = '<option value="all">All teams</option>' + opts.map(function (id) { return '<option value="' + id + '">' + escapeHtml(tname(id)) + "</option>"; }).join("");
  REC.team = opts.indexOf(keep) >= 0 ? keep : "all";
  document.getElementById("rec-team").value = REC.team;
  renderRecords();
}

function recBuild(matches, roster, apps, events) {
  var M = {}; matches.forEach(function (m) { M[m.id] = m; });
  var done = matches.filter(function (m) { return m.status === "completed" && m.home_score != null && m.away_score != null; });
  var appBy = {}, teamHas = {};
  apps.forEach(function (a) { appBy[a.match_id + "|" + a.player_id] = a; teamHas[a.match_id + "|" + a.team_id] = true; });
  var srank = {}; SEASONS.slice().reverse().forEach(function (s, i) { srank[s.id] = i; });
  var P = {};      // player id -> totals
  var slot = function (pid) {
    return P[pid] = P[pid] || { id: pid, team_id: null, tr: -1, played: 0, won: 0, drawn: 0, lost: 0, rested: 0, absent: 0, injury: 0, goals: 0, pens: 0, h1: 0, h2: 0, assists: 0, potm: 0, saves: 0, yellow: 0, red: 0, fouls: 0, og: 0, hat: 0, best: 0, bestMatch: null, cap: 0, capW: 0, capD: 0, capL: 0, capGF: 0, capPotm: 0, capDone: 0, gm: {} };
  };
  var potmAt = {};
  events.forEach(function (e) { if (e.event_type === "player_of_match") potmAt[e.match_id + "|" + e.player_id] = true; });
  roster.filter(function (r) { return TEAMS[r.team_id] && !isPlaceholder(TEAMS[r.team_id]); }).forEach(function (r) {
    var o = slot(r.player_id), rk = srank[r.season_id] || 0;
    if (rk >= o.tr) { o.tr = rk; o.team_id = r.team_id; }
    done.forEach(function (m) {
      if (m.season_id !== r.season_id || (m.home_team_id !== r.team_id && m.away_team_id !== r.team_id)) return;
      var a = appBy[m.id + "|" + r.player_id], st = a ? (a.status || "played") : (teamHas[m.id + "|" + r.team_id] ? "absent" : "played");
      if (st === "rested") { o.rested++; if (a && a.absent_reason === "injury") o.injury++; return; }
      if (st === "absent") { o.absent++; if (a && a.absent_reason === "injury") o.injury++; return; }
      o.played++;
      var mine = m.home_team_id === r.team_id ? m.home_score : m.away_score, theirs = m.home_team_id === r.team_id ? m.away_score : m.home_score;
      if (mine > theirs) o.won++; else if (mine < theirs) o.lost++; else o.drawn++;
    });
  });
  var known = function (pid) { return !!P[pid]; };
  var gk = { goal: "goals", assist: "assists", player_of_match: "potm", save: "saves", yellow_card: "yellow", red_card: "red", foul: "fouls", own_goal: "og" };
  events.forEach(function (e) {
    var k = gk[e.event_type];
    if (!k || !M[e.match_id] || !known(e.player_id)) return;
    var o = P[e.player_id];
    o[k]++;
    if (e.event_type === "goal") {
      if (e.is_penalty) o.pens++;
      var h = e.half; if (e.minute != null && (h == null || h === 0)) h = e.minute <= 10 ? 1 : 2;
      if (h === 1) o.h1++; else if (h === 2) o.h2++;
      o.gm[e.match_id] = (o.gm[e.match_id] || 0) + 1;
    }
  });
  Object.keys(P).forEach(function (pid) {
    var o = P[pid];
    Object.keys(o.gm).forEach(function (mid) {
      if (o.gm[mid] > o.best) { o.best = o.gm[mid]; o.bestMatch = mid; }
      if (o.gm[mid] >= 3) o.hat++;
    });
  });
  // captains
  apps.forEach(function (a) {
    if (!a.is_captain || !known(a.player_id) || !M[a.match_id]) return;
    var o = P[a.player_id], m = M[a.match_id];
    o.cap++;
    if (m.status === "completed" && m.home_score != null && m.away_score != null) {
      var mine = m.home_team_id === a.team_id ? m.home_score : m.away_score, theirs = m.home_team_id === a.team_id ? m.away_score : m.home_score;
      o.capDone++; o.capGF += mine;
      if (mine > theirs) o.capW++; else if (mine < theirs) o.capL++; else o.capD++;
    }
    if (potmAt[m.id + "|" + a.player_id]) o.capPotm++;
  });
  // teams
  var T = {};
  var tslot = function (id) { return T[id] = T[id] || { id: id, p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, cs: 0, yellow: 0, red: 0, fouls: 0, og: 0, rested: 0, absent: 0 }; };
  done.forEach(function (m) {
    [[m.home_team_id, m.home_score, m.away_score], [m.away_team_id, m.away_score, m.home_score]].forEach(function (x) {
      if (!TEAMS[x[0]] || isPlaceholder(TEAMS[x[0]])) return;
      var t = tslot(x[0]);
      t.p++; t.gf += x[1]; t.ga += x[2]; if (x[2] === 0) t.cs++;
      if (x[1] > x[2]) t.w++; else if (x[1] < x[2]) t.l++; else t.d++;
    });
  });
  events.forEach(function (e) {
    if (!M[e.match_id] || !T[e.team_id]) return;
    if (e.event_type === "yellow_card") T[e.team_id].yellow++; else if (e.event_type === "red_card") T[e.team_id].red++;
    else if (e.event_type === "foul") T[e.team_id].fouls++; else if (e.event_type === "own_goal") T[e.team_id].og++;
  });
  Object.keys(P).forEach(function (pid) { var o = P[pid]; if (T[o.team_id]) { T[o.team_id].rested += o.rested; T[o.team_id].absent += o.absent; } });
  return { M: M, done: done, events: events, players: Object.keys(P).map(function (k) { return P[k]; }), teams: Object.keys(T).map(function (k) { return T[k]; }) };
}

// ---------- helpers ----------
function recTeamOk(o) { return REC.team === "all" || o.team_id === REC.team; }
function recRate(num, den) { return den ? Math.round(1000 * num / den) / 1000 : 0; }
function recFmt(x, d) { return (Math.round(x * Math.pow(10, d)) / Math.pow(10, d)).toFixed(d); }
function recElig(o) { return o.played >= REC.minM; }

// standard competition ranking on a numeric key (1, 2, 2, 4), ties flagged
function recRanks(rows, val, dir) {
  var out = [], tied = [];
  rows.forEach(function (r, i) {
    var v = val(r);
    var first = i;
    while (first > 0 && val(rows[first - 1]) === v) first--;
    out.push(first + 1);
  });
  rows.forEach(function (r, i) { tied.push((i > 0 && out[i - 1] === out[i]) || (i + 1 < rows.length && out[i + 1] === out[i])); });
  return { ranks: out, tied: tied };
}

// generic leaderboard table. cols: [{k, t, title, l (left aligned), get(r) html, val(r) sort value, hl}]
function recTable(id, cols, rows, defKey, emptyText) {
  if (!rows.length) return '<p class="muted">' + emptyText + "</p>";
  var st = REC.sort && REC.sort.view === id ? REC.sort : { view: id, key: defKey, dir: -1 };
  var col = cols.filter(function (c) { return c.k === st.key; })[0] || cols.filter(function (c) { return c.k === defKey; })[0];
  var sorted = rows.slice().sort(function (a, b) {
    var x = col.val(a), y = col.val(b);
    if (typeof x === "string" || typeof y === "string") return st.dir * String(x).localeCompare(String(y)) || pname(a.id).localeCompare(pname(b.id));
    if (x == null) x = -Infinity; if (y == null) y = -Infinity;
    return st.dir * (x - y) || pname(a.id || "").localeCompare(pname(b.id || ""));
  });
  var rk = recRanks(sorted, function (r) { return col.val(r); }, st.dir);
  var arrow = function (c) { return c.k === col.k ? (st.dir > 0 ? " ▲" : " ▼") : ""; };
  var h = '<div class="table-scroll"><table class="data-table rec-table"><thead><tr><th class="num">#</th>' +
    cols.map(function (c) { return '<th class="' + (c.l ? "team-name " : "") + 'sortable' + (c.k === col.k ? " sorted" : "") + '" data-rsort="' + c.k + '" data-rview="' + id + '" title="' + (c.title || "") + '">' + c.t + arrow(c) + "</th>"; }).join("") +
    "</tr></thead><tbody>" +
    sorted.map(function (r, i) {
      return '<tr><td class="ms-n num">' + rk.ranks[i] + (rk.tied[i] ? "=" : "") + "</td>" +
        cols.map(function (c) { return '<td class="' + (c.l ? "team-name" : "num") + '">' + (c.hl ? "<strong>" + c.get(r) + "</strong>" : c.get(r)) + "</td>"; }).join("") + "</tr>";
    }).join("") + "</tbody></table></div>";
  return h;
}

var recPCols = function (extra) {
  return [{ k: "name", t: "Player", l: 1, get: function (r) { return plink(r.id); }, val: function (r) { return pname(r.id); } },
          { k: "team", t: "Team", l: 1, get: function (r) { return tlink(r.team_id); }, val: function (r) { return tname(r.team_id); } },
          { k: "played", t: "Matches", title: "Matches played", get: function (r) { return r.played; }, val: function (r) { return r.played; } }].concat(extra);
};
var recBestCell = function (r) { return r.best ? '<a href="match.html?id=' + r.bestMatch + '">' + r.best + " (D" + REC.data.M[r.bestMatch].match_day + "·M" + REC.data.M[r.bestMatch].match_number + ")</a>" : "–"; };

// ---------- player stat definitions (hub cards + leaderboards) ----------
function recStats() {
  var per = function (k) { return function (r) { return recElig(r) ? recRate(r[k], r.played) : null; }; };
  var perShow = function (k) { return function (r) { return recElig(r) ? recFmt(recRate(r[k], r.played), 2) : "–"; }; };
  return {
    goals: { title: "Most goals", key: "goals", min: 1, show: function (r) { return r.goals; }, val: function (r) { return r.goals; },
      cols: recPCols([{ k: "goals", t: "Goals", hl: 1, get: function (r) { return r.goals; }, val: function (r) { return r.goals; } },
        { k: "pm", t: "Per match", title: "Goals per match (needs the minimum matches)", get: perShow("goals"), val: per("goals") },
        { k: "pens", t: "Penalties", get: function (r) { return r.pens; }, val: function (r) { return r.pens; } },
        { k: "h1", t: "1st half", get: function (r) { return r.h1; }, val: function (r) { return r.h1; } },
        { k: "h2", t: "2nd half", get: function (r) { return r.h2; }, val: function (r) { return r.h2; } },
        { k: "best", t: "Best match", title: "Most goals in one match", get: recBestCell, val: function (r) { return r.best; } },
        { k: "hat", t: "Hat-tricks", get: function (r) { return r.hat; }, val: function (r) { return r.hat; } }]) },
    assists: { title: "Most assists", key: "assists", min: 1, show: function (r) { return r.assists; }, val: function (r) { return r.assists; },
      cols: recPCols([{ k: "assists", t: "Assists", hl: 1, get: function (r) { return r.assists; }, val: function (r) { return r.assists; } },
        { k: "pm", t: "Per match", title: "Assists per match (needs the minimum matches)", get: perShow("assists"), val: per("assists") }]) },
    contrib: { title: "Goal contributions (G+A)", key: "contrib", min: 1, show: function (r) { return r.goals + r.assists; }, val: function (r) { return r.goals + r.assists; },
      cols: recPCols([{ k: "contrib", t: "G+A", hl: 1, get: function (r) { return r.goals + r.assists; }, val: function (r) { return r.goals + r.assists; } },
        { k: "goals", t: "Goals", get: function (r) { return r.goals; }, val: function (r) { return r.goals; } },
        { k: "assists", t: "Assists", get: function (r) { return r.assists; }, val: function (r) { return r.assists; } },
        { k: "pm", t: "Per match", get: function (r) { return recElig(r) ? recFmt(recRate(r.goals + r.assists, r.played), 2) : "–"; }, val: function (r) { return recElig(r) ? recRate(r.goals + r.assists, r.played) : null; } }]) },
    potm: { title: "Player of the match awards", key: "potm", min: 1, show: function (r) { return r.potm; }, val: function (r) { return r.potm; },
      cols: recPCols([{ k: "potm", t: "POTM", hl: 1, get: function (r) { return r.potm; }, val: function (r) { return r.potm; } },
        { k: "pm", t: "Per match", get: perShow("potm"), val: per("potm") }]) },
    fouls: { title: "Most fouls", key: "fouls", min: 1, show: function (r) { return r.fouls; }, val: function (r) { return r.fouls; }, cols: null },
    cards: { title: "Yellow & red cards", key: "cards", min: 1, show: function (r) { return (r.yellow ? r.yellow + " Y" : "") + (r.yellow && r.red ? " " : "") + (r.red ? r.red + " R" : ""); }, val: function (r) { return r.red * 3 + r.yellow; }, cols: null },
    captain: { title: "Most matches as captain", wide: true, key: "cap", min: 1, show: function (r) { return r.cap; }, val: function (r) { return r.cap; }, cols: null }
  };
}

function recTop(def, n) {
  var rows = REC.data.players.filter(function (o) { return recTeamOk(o) && (def.minElig ? (recElig(o)) : (o.played + o.rested + o.absent + o.goals + o.assists + o.potm + o.saves + o.yellow + o.red + o.fouls + o.cap > 0)); });
  if (!def.asc && def.min) rows = rows.filter(function (o) { return def.val(o) >= def.min; });
  rows.sort(function (a, b) { return (def.asc ? 1 : -1) * (def.val(a) - def.val(b)) || (def.asc ? b.played - a.played : 0) || pname(a.id).localeCompare(pname(b.id)); });
  var rk = recRanks(rows, def.val);
  return rows.slice(0, n).map(function (r, i) { return { r: r, rank: rk.ranks[i], tied: rk.tied[i] }; });
}

function recCard(def, view) {
  var top = recTop(def, 5);
  var h = '<div class="rc' + (def.wide ? " wide" : "") + '"><h3>' + def.title + ' <a href="#" data-rview-go="' + view + '">View all ›</a></h3>';
  if (!top.length) return h + '<p class="muted" style="margin:6px 0 0;font-size:.85rem;">Nothing recorded yet.</p></div>';
  if (def.wide) h += '<div class="rcols">';
  top.forEach(function (x, i) {
    h += '<div class="rr' + (i === 0 ? " first" : "") + '"><span>' + plink(x.r.id) + '<span class="rt">' + tlink(x.r.team_id) + "</span></span><b>" + def.show(x.r) + "</b></div>";
  });
  return h + (def.wide ? "</div>" : "") + "</div>";
}

// ---------- views ----------
function recHub() {
  var S = recStats();
  var order = [["goals", "goals"], ["assists", "assists"], ["contrib", "contrib"], ["potm", "potm"], ["fouls", "discipline"], ["cards", "discipline"], ["captain", "captains"]];
  return '<p class="muted" style="margin:0 0 10px;">Every stat in one place: each card shows the top 5. Open a card for the full leaderboard. Per-match rates only rank players with at least ' + REC.minM + " match" + (REC.minM === 1 ? "" : "es") + ".</p>" +
    '<div class="rec-grid">' + order.map(function (o) { return recCard(S[o[0]], o[1]); }).join("") + "</div>";
}

function recPlayerBoard(statKey) {
  var def = recStats()[statKey];
  var rows = REC.data.players.filter(function (o) { return recTeamOk(o) && def.val(o) >= 1; });
  return '<div class="card-title" style="margin-top:0;">' + def.title + "</div>" +
    recTable(statKey, def.cols, rows, def.key, "Nothing recorded yet.") +
    '<p class="note">Ties share a rank. Click a heading to sort. Per match needs ' + REC.minM + "+ matches. Names, teams and matches are links.</p>";
}

function recDiscipline() {
  var rows = REC.data.players.filter(function (o) { return recTeamOk(o) && (o.yellow + o.red + o.fouls + o.og) > 0; });
  var cols = recPCols([{ k: "yellow", t: "Yellow", get: function (r) { return r.yellow; }, val: function (r) { return r.yellow; } },
    { k: "red", t: "Red", get: function (r) { return r.red; }, val: function (r) { return r.red; } },
    { k: "fouls", t: "Fouls", get: function (r) { return r.fouls; }, val: function (r) { return r.fouls; } },
    { k: "og", t: "Own goals", get: function (r) { return r.og; }, val: function (r) { return r.og; } },
    { k: "cpm", t: "Cards / match", title: "Cards per match (needs the minimum matches)", get: function (r) { return recElig(r) ? recFmt(recRate(r.yellow + r.red, r.played), 2) : "–"; }, val: function (r) { return recElig(r) ? recRate(r.yellow + r.red, r.played) : null; } }]);
  return '<div class="card-title" style="margin-top:0;">Cards &amp; fouls</div>' + recTable("discipline", cols, rows, "yellow", "No cards or fouls recorded yet.") +
    '<p class="note">Sorted by yellow cards by default. Click a heading to re-sort.</p>';
}

function recAvail() {
  var rows = REC.data.players.filter(function (o) { return recTeamOk(o) && (o.rested + o.absent) > 0; });
  var cols = recPCols([{ k: "rested", t: "Rested", get: function (r) { return r.rested; }, val: function (r) { return r.rested; } },
    { k: "absent", t: "Absent", get: function (r) { return r.absent; }, val: function (r) { return r.absent; } },
    { k: "missed", t: "Missed", hl: 1, get: function (r) { return r.rested + r.absent; }, val: function (r) { return r.rested + r.absent; } },
    { k: "injury", t: "Injury", title: "Missed matches marked as an injury", get: function (r) { return r.injury; }, val: function (r) { return r.injury; } }]);
  return '<div class="card-title" style="margin-top:0;">Availability</div>' + recTable("avail", cols, rows, "missed", "Nobody has been rested or absent yet.");
}

// Team results summary = the Standings table (same points, order, tie-breaks and ranks), plus clean sheets, win % and form.
function recStandRows() {
  var D = REC.data, srank = {};
  SEASONS.slice().reverse().forEach(function (x, i) { srank[x.id] = i; });
  var played = Object.keys(D.M).map(function (k) { return D.M[k]; }).filter(function (m) { return m.status === "completed" || m.status === "forfeited"; })
    .sort(function (a, b) { return ((srank[a.season_id] || 0) - (srank[b.season_id] || 0)) || (a.match_day - b.match_day) || (a.match_number - b.match_number); });
  var S = {}, ok = function (id) { return TEAMS[id] && !isPlaceholder(TEAMS[id]); };
  var slot = function (id) { return S[id] = S[id] || { team: TEAMS[id], id: id, p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, gd: 0, pts: 0, cs: 0, form: [] }; };
  played.forEach(function (m) {
    var se = SEASONS.filter(function (x) { return x.id === m.season_id; })[0] || {}, pw = se.points_win != null ? se.points_win : 2, pd = se.points_draw != null ? se.points_draw : 1, pl = se.points_loss != null ? se.points_loss : 0;
    [[m.home_team_id, m.home_score, m.away_score], [m.away_team_id, m.away_score, m.home_score]].forEach(function (x) {
      if (!ok(x[0])) return;
      var t = slot(x[0]), r;
      t.p++;
      if (m.status === "forfeited") r = m.forfeited_by_team_id === x[0] ? "L" : "W";
      else { t.gf += x[1]; t.ga += x[2]; if (x[2] === 0) t.cs++; r = x[1] > x[2] ? "W" : x[1] < x[2] ? "L" : "D"; }
      if (r === "W") { t.w++; t.pts += pw; } else if (r === "D") { t.d++; t.pts += pd; } else { t.l++; t.pts += pl; }
      t.form.push(r);
    });
  });
  var rows = Object.keys(S).map(function (k) { S[k].gd = S[k].gf - S[k].ga; return S[k]; });
  rows.sort(function (a, b) { return a.team.name.localeCompare(b.team.name); });   // same starting order as the Standings page, so fully level teams line up too
  rows.sort(function (a, b) { return (b.pts - a.pts) || (b.gd - a.gd) || (b.gf - a.gf) || (a.ga - b.ga); });
  rows = resolveTies(rows, played, REC.shoot || null);
  var ranks = [];
  rows.forEach(function (r, i) { ranks[i] = (i > 0 && r.unresolved && rows[i - 1].unresolved && r.tieKey === rows[i - 1].tieKey) ? ranks[i - 1] : i + 1; });
  rows.forEach(function (r, i) { r.rank = ranks[i]; r.tiedRank = !!(r.unresolved); });
  return rows;
}

function recTeams() {
  var rows = recStandRows();
  if (!rows.length) return '<div class="card-title" style="margin-top:0;">Team results summary</div><p class="muted">No completed matches yet.</p>';
  var chip = function (f) { return '<span class="fchip ' + f + '">' + f + "</span>"; };
  var cols = [{ k: "name", t: "Team", l: 1, get: function (r) { return tlink(r.id); }, val: function (r) { return tname(r.id); } },
    { k: "pts", t: "Pts", hl: 1, title: "Points", get: function (r) { return r.pts; }, val: function (r) { return r.pts; } },
    { k: "p", t: "P", title: "Played", get: function (r) { return r.p; }, val: function (r) { return r.p; } },
    { k: "w", t: "W", get: function (r) { return r.w; }, val: function (r) { return r.w; } },
    { k: "d", t: "D", get: function (r) { return r.d; }, val: function (r) { return r.d; } },
    { k: "l", t: "L", get: function (r) { return r.l; }, val: function (r) { return r.l; } },
    { k: "gd", t: "GD", title: "Goal difference", get: function (r) { return (r.gd > 0 ? "+" : "") + r.gd; }, val: function (r) { return r.gd; } },
    { k: "gf", t: "GF", title: "Goals for", get: function (r) { return r.gf; }, val: function (r) { return r.gf; } },
    { k: "ga", t: "GA", title: "Goals against", get: function (r) { return r.ga; }, val: function (r) { return r.ga; } },
    { k: "cs", t: "Clean sheets", title: "Matches where the team conceded no goals", sep: 1, get: function (r) { return r.cs; }, val: function (r) { return r.cs; } },
    { k: "winp", t: "Win %", get: function (r) { return r.p ? Math.round(1000 * r.w / r.p) / 10 + "%" : "–"; }, val: function (r) { return r.p ? r.w / r.p : null; } },
    { k: "form", t: "Form", title: "Last 5 results, newest on the right", nosort: 1, get: function (r) { return '<span class="fchips">' + r.form.slice(-5).map(chip).join("") + "</span>"; }, val: function (r) { return 0; } }];
  var st = REC.sort && REC.sort.view === "teams" ? REC.sort : null, show = rows.slice(), rank, tied;
  if (st) {
    var col = cols.filter(function (c) { return c.k === st.key; })[0] || cols[1];
    show.sort(function (a, b) { var x = col.val(a), y = col.val(b); if (typeof x === "string" || typeof y === "string") return st.dir * String(x).localeCompare(String(y)); if (x == null) x = -Infinity; if (y == null) y = -Infinity; return st.dir * (x - y) || (b.pts - a.pts); });
    var rk = recRanks(show, function (r) { return col.val(r); }); rank = rk.ranks; tied = rk.tied;
  } else { rank = show.map(function (r) { return r.rank; }); tied = show.map(function (r) { return r.tiedRank; }); }
  var arrow = function (c) { return st && c.k === st.key ? (st.dir > 0 ? " ▲" : " ▼") : ""; };
  var h = '<div class="card-title" style="margin-top:0;">Team results summary</div>' +
    (st ? '<p style="margin:0 0 8px;"><a href="#" data-rview-go="teams">&#8634; Back to standings order</a></p>' : "") +
    '<div class="table-scroll"><table class="data-table rec-table"><thead><tr><th class="num">#</th>' +
    cols.map(function (c) { return '<th class="' + (c.l ? "team-name " : "") + (c.nosort ? "" : "sortable") + (st && c.k === st.key ? " sorted" : "") + (c.sep ? " sep" : "") + '"' + (c.nosort ? "" : ' data-rsort="' + c.k + '" data-rview="teams"') + ' title="' + (c.title || "") + '">' + c.t + arrow(c) + "</th>"; }).join("") +
    "</tr></thead><tbody>" +
    show.map(function (r, i) {
      return '<tr><td class="ms-n num">' + rank[i] + (tied[i] ? "=" : "") + "</td>" +
        cols.map(function (c) { return '<td class="' + (c.l ? "team-name" : "num") + (c.sep ? " sep" : "") + '">' + (c.hl ? "<strong>" + c.get(r) + "</strong>" : c.get(r)) + "</td>"; }).join("") + "</tr>";
    }).join("") + "</tbody></table></div>" +
    '<p class="note">Completed matches only. Same table and order as the <a href="index.html">Standings page</a> (win = 2 pts, draw = 1, loss = 0; ties split by goal difference, goals scored, goals conceded, then head-to-head). Click a heading to re-sort. Team names open the team page.</p>';
  return h;
}

function recTeamDisc() {
  var rows = REC.data.teams.slice();
  var cols = [{ k: "name", t: "Team", l: 1, get: function (r) { return tlink(r.id); }, val: function (r) { return tname(r.id); } },
    { k: "p", t: "P", get: function (r) { return r.p; }, val: function (r) { return r.p; } },
    { k: "yellow", t: "Yellow", get: function (r) { return r.yellow; }, val: function (r) { return r.yellow; } },
    { k: "red", t: "Red", get: function (r) { return r.red; }, val: function (r) { return r.red; } },
    { k: "fouls", t: "Fouls", get: function (r) { return r.fouls; }, val: function (r) { return r.fouls; } },
    { k: "og", t: "Own goals", get: function (r) { return r.og; }, val: function (r) { return r.og; } },
    { k: "rested", t: "Rested", title: "Player-matches rested", get: function (r) { return r.rested; }, val: function (r) { return r.rested; } },
    { k: "absent", t: "Absent", title: "Player-matches absent", get: function (r) { return r.absent; }, val: function (r) { return r.absent; } }];
  return '<div class="card-title" style="margin-top:0;">Team discipline &amp; availability</div>' + recTable("teamdisc", cols, rows, "yellow", "No matches yet.");
}

function recMatchRecords() {
  var D = REC.data, done = D.done.filter(function (m) { return REC.team === "all" || m.home_team_id === REC.team || m.away_team_id === REC.team; });
  var line = function (m) { return tlink(m.home_team_id) + " " + m.home_score + "–" + m.away_score + " " + tlink(m.away_team_id) + " · " + matchLink(m); };
  var block = function (title, items, fmt) {
    if (!items.length) return '<div class="rec-r"><span>' + title + '<small>Nothing recorded yet</small></span></div>';
    return '<div class="rec-r"><span>' + title + items.map(function (x) { return "<small>" + x.html + "</small>"; }).join("") + '</span><span class="rv">' + fmt(items[0]) + "</span></div>";
  };
  var byMargin = done.slice().sort(function (a, b) { return Math.abs(b.home_score - b.away_score) - Math.abs(a.home_score - a.away_score); }).filter(function (m) { return m.home_score !== m.away_score; }).slice(0, 3)
    .map(function (m) { return { m: m, v: Math.abs(m.home_score - m.away_score), html: line(m) }; });
  var byGoals = done.slice().sort(function (a, b) { return (b.home_score + b.away_score) - (a.home_score + a.away_score); }).filter(function (m) { return m.home_score + m.away_score > 0; }).slice(0, 3)
    .map(function (m) { return { m: m, v: m.home_score + m.away_score, html: line(m) }; });
  var goalless = done.filter(function (m) { return m.home_score === 0 && m.away_score === 0; });
  var ev = D.events.filter(function (e) { return e.event_type === "goal" && e.minute != null && D.M[e.match_id] && (REC.team === "all" || e.team_id === REC.team || D.M[e.match_id].home_team_id === REC.team || D.M[e.match_id].away_team_id === REC.team); });
  var t = function (e) { return e.minute * 60 + (e.second || 0); };
  var fmtT = function (e) { return e.minute + "'" + (e.second != null ? (e.second < 10 ? "0" : "") + e.second + '"' : ""); };
  var gl = function (e) { return plink(e.player_id) + " (" + tlink(e.team_id) + ") · " + matchLink(D.M[e.match_id]) + " · " + fmtT(e); };
  var fastest = ev.slice().sort(function (a, b) { return t(a) - t(b); }).slice(0, 3).map(function (e) { return { e: e, html: gl(e) }; });
  var latest = ev.slice().sort(function (a, b) { return t(b) - t(a); }).slice(0, 3).map(function (e) { return { e: e, html: gl(e) }; });
  var tossN = 0, tossW = 0;
  done.forEach(function (m) { if (!m.toss_winner_team_id) return; tossN++; var w = m.home_score > m.away_score ? m.home_team_id : m.home_score < m.away_score ? m.away_team_id : null; if (w === m.toss_winner_team_id) tossW++; });
  var allGoals = ev.length;
  var h = '<div class="card-title" style="margin-top:0;">Match records</div>' +
    block("Biggest win", byMargin, function (x) { return "+" + x.v; }) +
    block("Most goals in a match", byGoals, function (x) { return x.v + " goals"; }) +
    block("Fastest goal", fastest, function (x) { return fmtT(x.e); }) +
    block("Latest goal", latest, function (x) { return fmtT(x.e); }) +
    '<div class="rec-r"><span>Goalless draws' + (goalless.length ? goalless.map(function (m) { return "<small>" + line(m) + "</small>"; }).join("") : "<small>None so far</small>") + '</span><span class="rv">' + goalless.length + "</span></div>" +
    '<div class="rec-r"><span>Toss winner went on to win<small>Matches with a recorded toss; draws count as not won</small></span><span class="rv">' + tossW + " of " + tossN + "</span></div>";
  return h + '<p class="note">Fastest and latest goals use only goals with a recorded minute (' + allGoals + " of the goals shown). Completed matches only.</p>";
}

function recCaptains() {
  var rows = REC.data.players.filter(function (o) { return recTeamOk(o) && o.cap > 0; });
  var cols = [{ k: "name", t: "Player", l: 1, get: function (r) { return plink(r.id); }, val: function (r) { return pname(r.id); } },
    { k: "team", t: "Team", l: 1, get: function (r) { return tlink(r.team_id); }, val: function (r) { return tname(r.team_id); } },
    { k: "cap", t: "Matches", hl: 1, title: "Matches captained", get: function (r) { return r.cap; }, val: function (r) { return r.cap; } },
    { k: "w", t: "Won", get: function (r) { return r.capW; }, val: function (r) { return r.capW; } },
    { k: "d", t: "Drawn", get: function (r) { return r.capD; }, val: function (r) { return r.capD; } },
    { k: "l", t: "Lost", get: function (r) { return r.capL; }, val: function (r) { return r.capL; } },
    { k: "wp", t: "Win %", get: function (r) { return r.capDone ? Math.round(1000 * r.capW / r.capDone) / 10 + "%" : "–"; }, val: function (r) { return r.capDone ? r.capW / r.capDone : null; } },
    { k: "gf", t: "Goals for", title: "Goals scored by the team while he captained", get: function (r) { return r.capGF; }, val: function (r) { return r.capGF; } },
    { k: "pm", t: "POTM", get: function (r) { return r.capPotm; }, val: function (r) { return r.capPotm; } }];
  return '<div class="card-title" style="margin-top:0;">Captains</div>' + recTable("captains", cols, rows, "cap", "No captains recorded yet.") +
    '<p class="note">The full captain history (every change, match by match) is in Milestones &rsaquo; Captains.</p>';
}

function renderRecords() {
  var box = document.getElementById("rec-body");
  if (!REC.loaded) return;
  var views = { hub: recHub, goals: function () { return recPlayerBoard("goals"); }, assists: function () { return recPlayerBoard("assists"); }, contrib: function () { return recPlayerBoard("contrib"); },
    potm: function () { return recPlayerBoard("potm"); }, discipline: recDiscipline, avail: recAvail, teams: recTeams,
    teamdisc: recTeamDisc, matchrec: recMatchRecords, captains: recCaptains };
  box.innerHTML = (REC.view !== "hub" ? '<p style="margin:0 0 8px;"><a href="#" data-rview-go="hub">&lsaquo; All records</a></p>' : "") + views[REC.view]();
  document.querySelectorAll("#rec-menu a").forEach(function (a) { a.classList.toggle("on", a.dataset.rview === REC.view); });
  document.getElementById("rec-hubbtn").classList.toggle("on", REC.view === "hub");
  box.querySelectorAll("th[data-rsort]").forEach(function (th) {
    th.addEventListener("click", function () {
      var k = th.dataset.rsort, v = th.dataset.rview;
      if (REC.sort && REC.sort.view === v && REC.sort.key === k) REC.sort.dir = -REC.sort.dir;
      else REC.sort = { view: v, key: k, dir: (k === "name" || k === "team") ? 1 : -1 };
      renderRecords();
    });
  });
  box.querySelectorAll("[data-rview-go]").forEach(function (a) {
    a.addEventListener("click", function (ev) { ev.preventDefault(); recGo(a.dataset.rviewGo); });
  });
}
function recGo(view) { REC.view = view; REC.sort = null; renderRecords(); window.scrollTo({ top: document.getElementById("sec-records").offsetTop - 10 }); }

function initRecords(seasonOpts) {
  document.getElementById("rec-season").innerHTML = seasonOpts + '<option value="all">All seasons (career)</option>';
  document.getElementById("rec-menu").innerHTML = '<a href="#" id="rec-hubbtn" class="on">Records home</a>' + REC_MENU.map(function (g) {
    return "<h4>" + g[0] + "</h4>" + g[1].map(function (i) { return '<a href="#" data-rview="' + i[0] + '">' + i[1].replace("&", "&amp;") + "</a>"; }).join("");
  }).join("");
  document.getElementById("rec-menu").addEventListener("click", function (ev) {
    var a = ev.target.closest("a"); if (!a) return;
    ev.preventDefault();
    recGo(a.id === "rec-hubbtn" ? "hub" : a.dataset.rview);
  });
  document.getElementById("rec-season").addEventListener("change", loadRecords);
  document.getElementById("rec-team").addEventListener("change", function () { REC.team = this.value; renderRecords(); });
  document.getElementById("rec-min").addEventListener("change", function () { REC.minM = parseInt(this.value, 10) || 1; renderRecords(); });
}
