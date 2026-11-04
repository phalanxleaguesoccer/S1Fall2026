// Trivia tab (Stats > Trivia): fun league facts, each a card that expands to full detail with links.
// trivBuild(ctx) is a PURE function (no DOM, no network) so it can be tested; renderTrivia() draws the cards.
// ctx = { matches, events, apps, tname(id), pname(id), ml(match,label), pl(id,name), tl(id,name), esc(s) }
// Everything is derived from the match scorecards: scores, toss, goal/assist/card events and lineups.
// Timeline facts (comebacks, fastest goal, who scored first) only use matches whose goal events add up to the final score.
var TRIV = { cat: "all", open: null, items: [], loaded: false };
var TRIV_CATS = [["all", "All"], ["goals", "Goals"], ["toss", "Toss & kick-off"], ["drama", "Comebacks & drama"], ["players", "Players"], ["teams", "Teams"], ["check", "Data check"]];
var TRIV_HALF = 600;   // seconds in one half (same as LIVE_HALF_SECONDS)

function trivBuild(c) {
  var esc = c.esc, T = c.tname, P = c.pname;
  var M = {}; c.matches.forEach(function (m) { M[m.id] = m; });
  var done = c.matches.filter(function (m) { return m.status === "completed" && m.home_score != null && m.away_score != null; })
    .sort(function (a, b) { return (a.match_day - b.match_day) || (a.match_number - b.match_number); });
  var isDone = {}; done.forEach(function (m) { isDone[m.id] = true; });
  var ev = c.events.filter(function (e) { return isDone[e.match_id]; });
  var n = done.length;
  function other(m, t) { return m.home_team_id === t ? m.away_team_id : m.home_team_id; }
  function gf(m, t) { return m.home_team_id === t ? m.home_score : m.away_score; }
  function plural(k, w, ws) { return k + " " + (k === 1 ? w : (ws || w + "s")); }
  function pct(a, b) { return b ? Math.round(100 * a / b) + "%" : "–"; }
  function score(m) { return m.home_score + "–" + m.away_score; }
  function line(m) { return esc(T(m.home_team_id)) + " " + score(m) + " " + esc(T(m.away_team_id)); }
  function mlink(m) { return c.ml(m, "Day " + m.match_day + " · M" + m.match_number); }
  function rows(list, head, cls) {
    if (!list.length) return '<p class="muted">Nothing to show yet.</p>';
    return '<div class="table-scroll"><table class="data-table triv-table"><thead><tr>' + head.map(function (h, i) { return '<th class="' + (i === 0 ? "" : "num") + '">' + h + "</th>"; }).join("") +
      "</tr></thead><tbody>" + list.map(function (r) { return "<tr>" + r.map(function (x, i) { return '<td class="' + (i === 0 ? "" : "num") + '">' + x + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table></div>";
  }
  function top(arr, key, k) { return arr.slice().sort(function (a, b) { return key(b) - key(a); }).slice(0, k); }
  function winners(arr, key) { var mx = Math.max.apply(null, arr.map(key)); return arr.filter(function (x) { return key(x) === mx; }); }
  function names(list, f) { return list.map(f).join(", "); }
  function note(t) { return '<p class="muted triv-note">' + t + "</p>"; }

  // ---- goal timeline per match ----
  var goalsBy = {};
  ev.forEach(function (e) {
    if (e.event_type !== "goal" && e.event_type !== "own_goal") return;
    var m = M[e.match_id]; if (!m) return;
    var sec = e.minute != null ? e.minute * 60 + (e.second || 0) : (e.time_remaining != null && e.half ? (e.half === 2 ? 2 * TRIV_HALF : TRIV_HALF) - e.time_remaining : null);
    var half = e.half || (sec != null ? (sec >= TRIV_HALF ? 2 : 1) : null);
    (goalsBy[m.id] = goalsBy[m.id] || []).push({ team: e.event_type === "goal" ? e.team_id : other(m, e.team_id), pid: e.player_id, og: e.event_type === "own_goal", pen: !!e.is_penalty, sec: sec, half: half, rel: e.related_player_id, m: m });
  });
  function gkey(g) { return (g.half || 3) * 100000 + (g.sec == null ? 99999 : g.sec); }
  Object.keys(goalsBy).forEach(function (id) { goalsBy[id].sort(function (a, b) { return gkey(a) - gkey(b); }); });
  function inHalf(g) { return g.half === 2 ? g.sec - TRIV_HALF : g.sec; }
  function clock(s) { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2); }
  var timed = done.filter(function (m) { var g = goalsBy[m.id] || []; return g.length === m.home_score + m.away_score && g.every(function (x) { return x.sec != null; }); });
  var isTimed = {}; timed.forEach(function (m) { isTimed[m.id] = true; });
  // "ordered" = we can tell the order of every goal: each goal has a half, and inside a half without exact times all goals belong to one team.
  var ordered = done.filter(function (m) {
    var g = goalsBy[m.id] || []; if (g.length !== m.home_score + m.away_score) return false;
    if (!g.every(function (x) { return x.half != null; })) return false;
    return [1, 2].every(function (h) { var a = g.filter(function (x) { return x.half === h; }); if (a.every(function (x) { return x.sec != null; })) return true; var t = {}; a.forEach(function (x) { t[x.team] = 1; }); return Object.keys(t).length <= 1; });
  });
  var isOrdered = {}; ordered.forEach(function (m) { isOrdered[m.id] = true; });
  var untimed = done.filter(function (m) { return !isTimed[m.id] && (m.home_score + m.away_score) > 0; });
  var unordered = done.filter(function (m) { return !isOrdered[m.id] && (m.home_score + m.away_score) > 0; });
  var timeNote = unordered.length ? "Goal order is only known for " + ordered.length + " of " + n + " matches. Not counted (goals missing or order unclear): " + unordered.map(mlink).join(", ") + "." : "";

  // ---- team rows (one per team per match) ----
  var teamIds = {}; done.forEach(function (m) { teamIds[m.home_team_id] = 1; teamIds[m.away_team_id] = 1; });
  var TEAMS = Object.keys(teamIds).sort(function (a, b) { return T(a).localeCompare(T(b)); });
  var tm = [];
  done.forEach(function (m) {
    [m.home_team_id, m.away_team_id].forEach(function (t) {
      var f = gf(m, t), a = gf(m, other(m, t)), tw = m.toss_winner_team_id && m.toss_choice ? m.toss_winner_team_id : null;
      var kick = tw ? (m.toss_choice === "kickoff" ? tw : other(m, tw)) : null;
      tm.push({ m: m, t: t, opp: other(m, t), f: f, a: a, res: f > a ? "W" : f < a ? "L" : "D", tossWon: tw ? tw === t : null, kicked: kick ? kick === t : null, choice: tw === t ? m.toss_choice : null });
    });
  });
  function tally(list) { var o = { p: list.length, w: 0, d: 0, l: 0 }; list.forEach(function (r) { o[r.res.toLowerCase()]++; }); return o; }
  function wdl(o) { return o.w + "-" + o.d + "-" + o.l; }
  var items = [];
  function add(id, cat, icon, title, headline, sub, detail) { items.push({ id: id, cat: cat, icon: icon, title: title, headline: headline, sub: sub, detail: detail }); }

  // =============== GOALS ===============
  // 1. Most goals in the league
  var teamGoals = TEAMS.map(function (t) { var r = tm.filter(function (x) { return x.t === t; }); return { t: t, g: r.reduce(function (s, x) { return s + x.f; }, 0), ga: r.reduce(function (s, x) { return s + x.a; }, 0), p: r.length }; });
  var pg = {}; ev.forEach(function (e) { if (e.event_type === "goal") { var k = e.player_id; pg[k] = pg[k] || { pid: k, g: 0, ms: {} }; pg[k].g++; pg[k].ms[e.match_id] = 1; } });
  var pgl = Object.keys(pg).map(function (k) { return pg[k]; }).sort(function (a, b) { return b.g - a.g || Object.keys(a.ms).length - Object.keys(b.ms).length; });
  var tw = winners(teamGoals, function (x) { return x.g; }), pw = pgl.length ? winners(pgl, function (x) { return x.g; }) : [];
  add("lg", "goals", "⚽", "Most goals in the league",
    tw.length ? names(tw, function (x) { return esc(T(x.t)); }) + " · " + tw[0].g : "–",
    pw.length ? "Top scorer: " + names(pw, function (x) { return esc(P(x.pid)); }) + " (" + pw[0].g + ")" : "",
    "<h4>Teams</h4>" + rows(teamGoals.slice().sort(function (a, b) { return b.g - a.g; }).map(function (x, i) { return [(i + 1) + ". " + c.tl(x.t, T(x.t)), x.g, x.p, (x.g / x.p).toFixed(2), x.ga]; }), ["Team", "Goals", "Played", "Per match", "Against"]) +
    "<h4>Players (goals on scorecards)</h4>" + rows(pgl.slice(0, 10).map(function (x, i) { return [(i + 1) + ". " + c.pl(x.pid, P(x.pid)), x.g, Object.keys(x.ms).length]; }), ["Player", "Goals", "Matches scored in"]) +
    note("League total: " + plural(teamGoals.reduce(function (s, x) { return s + x.g; }, 0), "goal") + " in " + plural(n, "match", "matches") + "."));

  // 2. Most goals in a day
  var days = {}; done.forEach(function (m) { var d = days[m.match_day] = days[m.match_day] || { day: m.match_day, g: 0, ms: [], t: {} }; d.g += m.home_score + m.away_score; d.ms.push(m); d.t[m.home_team_id] = (d.t[m.home_team_id] || 0) + m.home_score; d.t[m.away_team_id] = (d.t[m.away_team_id] || 0) + m.away_score; });
  var dayList = Object.keys(days).map(function (k) { return days[k]; }).sort(function (a, b) { return a.day - b.day; });
  var teamDays = []; dayList.forEach(function (d) { Object.keys(d.t).forEach(function (t) { teamDays.push({ day: d.day, t: t, g: d.t[t] }); }); });
  var pday = {}; ev.forEach(function (e) { if (e.event_type !== "goal") return; var m = M[e.match_id]; var k = e.player_id + "|" + m.match_day; pday[k] = pday[k] || { pid: e.player_id, day: m.match_day, g: 0 }; pday[k].g++; });
  var pdl = Object.keys(pday).map(function (k) { return pday[k]; });
  var bd = dayList.length ? winners(dayList, function (d) { return d.g; }) : [], btd = teamDays.length ? winners(teamDays, function (x) { return x.g; }) : [];
  add("day", "goals", "📅", "Most goals in a day",
    bd.length ? "Day " + bd.map(function (d) { return d.day; }).join(" & Day ") + " · " + bd[0].g + " goals" : "–",
    (btd.length ? "Team: " + names(btd, function (x) { return esc(T(x.t)) + " (Day " + x.day + ")"; }) + " scored " + btd[0].g : "") + (pdl.length ? " · Player: " + names(winners(pdl, function (x) { return x.g; }), function (x) { return esc(P(x.pid)) + " (Day " + x.day + ")"; }) + " scored " + Math.max.apply(null, pdl.map(function (x) { return x.g; })) : ""),
    "<h4>All goals on each match day</h4>" + rows(dayList.map(function (d) { return ["Day " + d.day, d.g, d.ms.length, (d.g / d.ms.length).toFixed(2), d.ms.map(mlink).join(" · ")]; }), ["Day", "Goals", "Matches", "Per match", "Matches"]) +
    "<h4>Biggest team days (goals scored in the day's 2 matches)</h4>" + rows(top(teamDays, function (x) { return x.g; }, 6).map(function (x) { return [c.tl(x.t, T(x.t)), x.g, "Day " + x.day]; }), ["Team", "Goals", "Day"]) +
    (pdl.length ? "<h4>Biggest player days</h4>" + rows(top(pdl, function (x) { return x.g; }, 5).map(function (x) { return [c.pl(x.pid, P(x.pid)), x.g, "Day " + x.day]; }), ["Player", "Goals", "Day"]) : ""));

  // 3. Most goals in a match
  var byTot = done.slice().sort(function (a, b) { return (b.home_score + b.away_score) - (a.home_score + a.away_score); });
  var recTot = byTot.length ? byTot[0].home_score + byTot[0].away_score : 0;
  var recMatches = byTot.filter(function (m) { return m.home_score + m.away_score === recTot; });
  var pmatch = {}; ev.forEach(function (e) { if (e.event_type !== "goal") return; var k = e.player_id + "|" + e.match_id; pmatch[k] = pmatch[k] || { pid: e.player_id, m: M[e.match_id], g: 0 }; pmatch[k].g++; });
  var pml = Object.keys(pmatch).map(function (k) { return pmatch[k]; }).sort(function (a, b) { return b.g - a.g; });
  var margin = done.slice().sort(function (a, b) { return Math.abs(b.home_score - b.away_score) - Math.abs(a.home_score - a.away_score); });
  add("match", "goals", "🔥", "Most goals in a match",
    recTot ? recTot + " goals" : "–",
    (recMatches.length ? "League: " + recMatches.map(function (m) { return line(m); }).join(" · ") : "") + (pml.length ? " · Player: " + names(winners(pml, function (x) { return x.g; }), function (x) { return esc(P(x.pid)); }) + " (" + pml[0].g + ")" : "") + (function () { var tb = []; done.forEach(function (m) { tb.push({ t: m.home_team_id, g: m.home_score, m: m }); tb.push({ t: m.away_team_id, g: m.away_score, m: m }); }); var w = tb.length ? winners(tb, function (x) { return x.g; }) : []; return w.length ? " · Team: " + names(w, function (x) { return esc(T(x.t)); }) + " (" + w[0].g + ")" : ""; })(),
    "<h4>Highest-scoring matches</h4>" + rows(byTot.slice(0, 8).map(function (m) { return [mlink(m), line(m), m.home_score + m.away_score]; }), ["Match", "Result", "Goals"]) +
    "<h4>Biggest winning margins</h4>" + rows(margin.filter(function (m) { return m.home_score !== m.away_score; }).slice(0, 6).map(function (m) { return [mlink(m), line(m), Math.abs(m.home_score - m.away_score)]; }), ["Match", "Result", "Margin"]) +
    (pml.length ? "<h4>Most goals by one player in a match</h4>" + rows(pml.slice(0, 6).map(function (x) { return [c.pl(x.pid, P(x.pid)), x.g, mlink(x.m)]; }), ["Player", "Goals", "Match"]) : ""));

  // 4. Most goals in a half
  var halves = [];
  ordered.forEach(function (m) { [1, 2].forEach(function (h) { var gs = (goalsBy[m.id] || []).filter(function (g) { return g.half === h; }); if (gs.length) { var by = {}; gs.forEach(function (g) { by[g.team] = (by[g.team] || 0) + 1; }); halves.push({ m: m, h: h, tot: gs.length, by: by }); } }); });
  var th = []; halves.forEach(function (x) { Object.keys(x.by).forEach(function (t) { th.push({ m: x.m, h: x.h, t: t, g: x.by[t] }); }); });
  var h1 = 0, h2 = 0; ordered.forEach(function (m) { (goalsBy[m.id] || []).forEach(function (g) { if (g.half === 2) h2++; else h1++; }); });
  var halfPl = [];
  var bth = th.length ? winners(th, function (x) { return x.g; }) : [], bh = halves.length ? winners(halves, function (x) { return x.tot; }) : [];
  add("half", "goals", "⏱️", "Most goals in a half",
    bh.length ? bh[0].tot + " goals" : "–",
    (function () { var pp = {}; ordered.forEach(function (m) { (goalsBy[m.id] || []).forEach(function (g) { if (g.og) return; var k = g.pid + "|" + m.id + "|" + g.half; pp[k] = pp[k] || { pid: g.pid, g: 0, h: g.half, m: m }; pp[k].g++; }); }); var l = Object.keys(pp).map(function (k) { return pp[k]; }); halfPl = l; return ""; })() + (halfPl.length ? "Player: " + names(winners(halfPl, function (x) { return x.g; }), function (x) { return esc(P(x.pid)); }) + " (" + Math.max.apply(null, halfPl.map(function (x) { return x.g; })) + ") · " : "") + (bth.length ? "Team: " + bth[0].g + " by " + names(bth, function (x) { return esc(T(x.t)) + " (" + (x.h === 1 ? "1st" : "2nd") + " half, D" + x.m.match_day + " M" + x.m.match_number + ")"; }) : ""),
    "<h4>Busiest halves (both teams)</h4>" + rows(halves.slice().sort(function (a, b) { return b.tot - a.tot; }).slice(0, 6).map(function (x) { return [mlink(x.m), (x.h === 1 ? "1st half" : "2nd half"), line(x.m), x.tot]; }), ["Match", "Half", "Result", "Goals in half"]) +
    "<h4>Best half by one team</h4>" + rows(th.slice().sort(function (a, b) { return b.g - a.g; }).slice(0, 6).map(function (x) { return [c.tl(x.t, T(x.t)), x.g, (x.h === 1 ? "1st half" : "2nd half"), mlink(x.m)]; }), ["Team", "Goals", "Half", "Match"]) +
    (halfPl.length ? "<h4>Best half by one player</h4>" + rows(halfPl.slice().sort(function (a, b) { return b.g - a.g; }).slice(0, 6).map(function (x) { return [c.pl(x.pid, P(x.pid)), x.g, (x.h === 1 ? "1st half" : "2nd half"), mlink(x.m)]; }), ["Player", "Goals", "Half", "Match"]) : "") +
    "<h4>Which half has more goals?</h4>" + rows([["1st half", h1, pct(h1, h1 + h2)], ["2nd half", h2, pct(h2, h1 + h2)]], ["Half", "Goals", "Share"]) + note(timeNote));

  // =============== TOSS & KICK-OFF ===============
  var tossM = done.filter(function (m) { return m.toss_winner_team_id && m.toss_choice; });
  var tossNote = tossM.length < n ? "Toss is recorded for " + tossM.length + " of " + n + " matches played. The team that does not win the toss and the team that chooses Side is assumed to kick off second: a toss winner who picks Start kicks off; one who picks Side lets the opponent kick off." : "";
  // 5. wins when starting kick-off
  var kickers = tm.filter(function (r) { return r.kicked === true; }), nonk = tm.filter(function (r) { return r.kicked === false; });
  var kt = tally(kickers), nt = tally(nonk);
  add("kickwins", "toss", "🟢", "Wins when starting the kick-off",
    kt.p ? kt.w + " of " + kt.p + " (" + pct(kt.w, kt.p) + ")" : "–",
    kt.p ? "Kick-off side record " + wdl(kt) + " (W-D-L) vs " + wdl(nt) + " for the side that did not start" : "No toss recorded yet",
    "<h4>Record of the team that started the match</h4>" + rows([["Started (kicked off)", kt.p, kt.w, kt.d, kt.l, pct(kt.w, kt.p)], ["Did not start", nt.p, nt.w, nt.d, nt.l, pct(nt.w, nt.p)]], ["", "Matches", "Won", "Drawn", "Lost", "Win %"]) +
    "<h4>By team (matches where they kicked off)</h4>" + rows(TEAMS.map(function (t) { var o = tally(kickers.filter(function (r) { return r.t === t; })); return [c.tl(t, T(t)), o.p, o.w, o.d, o.l, pct(o.w, o.p)]; }), ["Team", "Kicked off", "Won", "Drawn", "Lost", "Win %"]) +
    "<h4>Every match where a team started</h4>" + rows(kickers.map(function (r) { return [mlink(r.m), esc(T(r.t)), r.f + "–" + r.a, r.res === "W" ? "Won" : r.res === "D" ? "Drew" : "Lost"]; }), ["Match", "Team that started", "Score (their goals first)", "Result"]) + note(tossNote));

  // 6. toss winners choosing Start vs Side
  var tr = tm.filter(function (r) { return r.tossWon === true; });
  var chK = tr.filter(function (r) { return r.choice === "kickoff"; }).length, chS = tr.length - chK;
  add("tosschoice", "toss", "🪙", "Toss winners who chose Start (kick-off)",
    tr.length ? chK + " of " + tr.length + " (" + pct(chK, tr.length) + ")" : "–",
    tr.length ? chS + " chose Side instead" : "No toss recorded yet",
    "<h4>What each team chose after winning the toss</h4>" + rows(TEAMS.map(function (t) { var a = tr.filter(function (r) { return r.t === t; }), k = a.filter(function (r) { return r.choice === "kickoff"; }).length; return [c.tl(t, T(t)), a.length, k, a.length - k]; }), ["Team", "Tosses won", "Chose Start", "Chose Side"]) +
    "<h4>Every toss</h4>" + rows(tossM.map(function (m) { return [mlink(m), esc(T(m.toss_winner_team_id)), m.toss_choice === "kickoff" ? "Start / kick-off" : "Side", line(m)]; }), ["Match", "Toss won by", "Chose", "Result"]) + note(tossNote));

  // 7 & 8. toss winners winning / losing
  var ts = tally(tr);
  function tossTeamRows() { return TEAMS.map(function (t) { var o = tally(tr.filter(function (r) { return r.t === t; })); var nw = tally(tm.filter(function (r) { return r.tossWon === false && r.t === t; })); return [c.tl(t, T(t)), o.p, o.w, o.d, o.l, pct(o.w, o.p), nw.p ? pct(nw.w, nw.p) : "–"]; }); }
  var tossHead = ["Team", "Tosses won", "Won match", "Drew", "Lost", "Win %", "Win % when losing toss"];
  var tossList = "<h4>Every match, by the toss winner</h4>" + rows(tr.map(function (r) { return [mlink(r.m), esc(T(r.t)), r.f + "–" + r.a, r.res === "W" ? "Won" : r.res === "D" ? "Drew" : "Lost"]; }), ["Match", "Toss winner", "Their goals first", "Result"]);
  add("tosswon", "toss", "🏆", "Toss winners who won the match",
    ts.p ? ts.w + " of " + ts.p + " (" + pct(ts.w, ts.p) + ")" : "–", ts.p ? "Winning the toss, then the match: " + wdl(ts) + " (W-D-L)" : "No toss recorded yet",
    "<h4>By team</h4>" + rows(tossTeamRows(), tossHead) + tossList + note(tossNote));
  add("tosslost", "toss", "🪙", "Toss winners who lost the match",
    ts.p ? ts.l + " of " + ts.p + " (" + pct(ts.l, ts.p) + ")" : "–", ts.p ? ts.d + " drawn · winning the toss is " + (ts.w > ts.l ? "worth something" : ts.w < ts.l ? "no guarantee" : "dead level") : "No toss recorded yet",
    "<h4>By team</h4>" + rows(tossTeamRows(), tossHead) + tossList + note(tossNote));

  // =============== COMEBACKS & DRAMA ===============
  // 9. results after trailing
  var cb = [];
  ordered.forEach(function (m) {
    var sc = {}; sc[m.home_team_id] = 0; sc[m.away_team_id] = 0; var maxDef = {}; maxDef[m.home_team_id] = 0; maxDef[m.away_team_id] = 0; var tl = [];
    (goalsBy[m.id] || []).forEach(function (g) { sc[g.team]++; var h = sc[m.home_team_id], a = sc[m.away_team_id]; [m.home_team_id, m.away_team_id].forEach(function (t) { var d = sc[other(m, t)] - sc[t]; if (d > maxDef[t]) maxDef[t] = d; }); tl.push(h + "–" + a + " " + (g.half === 1 ? "1H " : "2H ") + (g.sec != null ? clock(inHalf(g)) + " " : "") + esc(P(g.pid)) + (g.og ? " (og)" : "")); });
    [m.home_team_id, m.away_team_id].forEach(function (t) { if (maxDef[t] > 0) { var f = gf(m, t), a = gf(m, other(m, t)); cb.push({ m: m, t: t, def: maxDef[t], res: f > a ? "W" : f < a ? "L" : "D", tl: tl }); } });
  });
  var cbW = cb.filter(function (x) { return x.res === "W"; }), cbD = cb.filter(function (x) { return x.res === "D"; });
  var cbHead = cbW.length ? "Won " + plural(cbW.length, "time") : cbD.length ? "None yet" : "None yet";
  var cbSub = cbW.length ? "Biggest deficit overturned: " + Math.max.apply(null, cbW.map(function (x) { return x.def; })) + " goal(s) – " + names(winners(cbW, function (x) { return x.def; }), function (x) { return esc(T(x.t)); }) :
    (cbD.length ? "No team has won after trailing. " + plural(cbD.length, "team") + " fought back to draw." : "No team has come back from behind yet.");
  add("comeback", "drama", "🔄", "Winning after trailing", cbHead, cbSub,
    "<h4>Wins after being behind</h4>" + (cbW.length ? rows(cbW.map(function (x) { return [mlink(x.m), esc(T(x.t)), "Down by " + x.def, line(x.m)]; }), ["Match", "Team", "Deficit", "Final"]) : '<p class="muted">No team has won a match after trailing yet.</p>') +
    "<h4>Draws after being behind</h4>" + (cbD.length ? rows(cbD.map(function (x) { return [mlink(x.m), esc(T(x.t)), "Down by " + x.def, line(x.m)]; }), ["Match", "Team", "Deficit", "Final"]) : '<p class="muted">None yet.</p>') +
    "<h4>Teams that trailed and still lost</h4>" + rows(TEAMS.map(function (t) { var a = cb.filter(function (x) { return x.t === t; }); return [c.tl(t, T(t)), a.length, a.filter(function (x) { return x.res === "W"; }).length, a.filter(function (x) { return x.res === "D"; }).length, a.filter(function (x) { return x.res === "L"; }).length]; }), ["Team", "Matches trailed in", "Won", "Drew", "Lost"]) +
    (cb.length ? "<h4>Goal-by-goal</h4>" + cb.filter(function (x) { return x.res !== "L"; }).map(function (x) { return "<p>" + mlink(x.m) + " · " + esc(T(x.t)) + ": " + x.tl.join(" → ") + "</p>"; }).join("") : "") + note(timeNote));

  // d1. fastest / latest goal
  var all = []; timed.forEach(function (m) { (goalsBy[m.id] || []).forEach(function (g) { all.push(g); }); });
  var fast = all.slice().sort(function (a, b) { return inHalf(a) - inHalf(b); }), late = all.slice().sort(function (a, b) { return inHalf(b) - inHalf(a); });
  function glRow(g) { return [c.pl(g.pid, P(g.pid)) + (g.og ? " (own goal)" : ""), (g.half === 1 ? "1st" : "2nd") + " half " + clock(inHalf(g)), mlink(g.m), line(g.m)]; }
  add("fast", "drama", "⚡", "Fastest and latest goals",
    fast.length ? "Fastest: " + clock(inHalf(fast[0])) : "–",
    fast.length ? "Latest: " + esc(P(late[0].pid)) + " at " + clock(inHalf(late[0])) + " of the " + (late[0].half === 1 ? "1st" : "2nd") + " half (" + clock(TRIV_HALF - inHalf(late[0])) + " left)" : "",
    "<h4>Quickest goals after a half starts</h4>" + rows(fast.slice(0, 5).map(glRow), ["Scorer", "When", "Match", "Result"]) +
    "<h4>Latest goals in a half</h4>" + rows(late.slice(0, 5).map(glRow), ["Scorer", "When", "Match", "Result"]) + note(timeNote));

  // d2. goals in the final minute of a half / decisive late goals
  var lastMin = all.filter(function (g) { return inHalf(g) >= TRIV_HALF - 60; });
  add("clutch", "drama", "🧨", "Last-minute goals",
    plural(lastMin.length, "goal") + " in the last minute of a half",
    lastMin.length ? lastMin.length + " of " + all.length + " timed goals (" + pct(lastMin.length, all.length) + ")" : "",
    "<h4>Goals in the final 60 seconds of a half</h4>" + rows(lastMin.sort(function (a, b) { return inHalf(b) - inHalf(a); }).map(function (g) { return glRow(g).concat([g.half === 2 ? "Late 2nd-half goal" : "Just before half-time"]); }), ["Scorer", "When", "Match", "Result", "Note"]) + note(timeNote));

  // d3. scoring first
  var sf = { w: 0, d: 0, l: 0 }, hl = { w: 0, d: 0, l: 0 }, sfList = [];
  ordered.forEach(function (m) {
    var g = goalsBy[m.id] || []; if (!g.length) return;
    var first = g[0].team, f = gf(m, first), a = gf(m, other(m, first)); var r = f > a ? "w" : f < a ? "l" : "d"; sf[r]++; sfList.push([mlink(m), esc(T(first)), line(m), r === "w" ? "Went on to win" : r === "d" ? "Drew" : "Lost"]);
    var h1g = g.filter(function (x) { return x.half === 1; }), ht = {}; ht[m.home_team_id] = 0; ht[m.away_team_id] = 0; h1g.forEach(function (x) { ht[x.team]++; });
    var lead = ht[m.home_team_id] > ht[m.away_team_id] ? m.home_team_id : ht[m.away_team_id] > ht[m.home_team_id] ? m.away_team_id : null;
    if (lead) { var ff = gf(m, lead), aa = gf(m, other(m, lead)); hl[ff > aa ? "w" : ff < aa ? "l" : "d"]++; }
  });
  var sfT = sf.w + sf.d + sf.l, hlT = hl.w + hl.d + hl.l;
  add("scorefirst", "drama", "🥇", "Score first, win the match?",
    sfT ? sf.w + " of " + sfT + " (" + pct(sf.w, sfT) + ")" : "–", sfT ? "Teams that scored first: " + sf.w + " won, " + sf.d + " drew, " + sf.l + " lost" : "",
    "<h4>Scoring the first goal</h4>" + rows([["Won", sf.w], ["Drew", sf.d], ["Lost", sf.l]], ["Result", "Matches"]) +
    "<h4>Leading at half-time</h4>" + (hlT ? rows([["Won", hl.w], ["Drew", hl.d], ["Lost", hl.l]], ["Result", "Matches"]) : '<p class="muted">No half-time leads recorded yet.</p>') +
    "<h4>Match by match</h4>" + rows(sfList, ["Match", "Scored first", "Result", "What happened"]) + note(timeNote));

  // d4. goalless & clean sheets
  var nil = done.filter(function (m) { return m.home_score === 0 && m.away_score === 0; });
  var cs = TEAMS.map(function (t) { var r = tm.filter(function (x) { return x.t === t; }); return { t: t, cs: r.filter(function (x) { return x.a === 0; }).length, ng: r.filter(function (x) { return x.f === 0; }).length, p: r.length }; });
  var bcs = cs.length ? winners(cs, function (x) { return x.cs; }) : [];
  add("clean", "teams", "🧤", "Clean sheets and goalless draws",
    bcs.length ? names(bcs, function (x) { return esc(T(x.t)); }) + " · " + bcs[0].cs + " clean sheets" : "–", plural(nil.length, "0–0 draw") + " in " + plural(n, "match", "matches"),
    "<h4>Clean sheets by team</h4>" + rows(cs.slice().sort(function (a, b) { return b.cs - a.cs; }).map(function (x) { return [c.tl(x.t, T(x.t)), x.cs, x.p, pct(x.cs, x.p), x.ng]; }), ["Team", "Clean sheets", "Played", "Rate", "Matches without a goal"]) +
    "<h4>Goalless draws</h4>" + (nil.length ? rows(nil.map(function (m) { return [mlink(m), line(m)]; }), ["Match", "Result"]) : '<p class="muted">No 0–0 draws yet.</p>'));

  // =============== PLAYERS ===============
  // p1. hat-tricks and braces
  var multi = pml.filter(function (x) { return x.g >= 2; });
  add("hat", "players", "🎩", "Hat-tricks and braces",
    multi.length ? plural(multi.filter(function (x) { return x.g >= 3; }).length, "hat-trick") + " · " + plural(multi.filter(function (x) { return x.g === 2; }).length, "brace") : "None yet",
    multi.length ? "Best: " + names(multi.filter(function (x) { return x.g === multi[0].g; }), function (x) { return esc(P(x.pid)); }) + " (" + multi[0].g + " in " + (multi.filter(function (x) { return x.g === multi[0].g; })[0].m ? "one match" : "") + ")" : "",
    "<h4>Players with 2+ goals in a match</h4>" + rows(multi.map(function (x) { return [c.pl(x.pid, P(x.pid)), x.g >= 3 ? "Hat-trick" : "Brace", x.g, mlink(x.m), line(x.m)]; }), ["Player", "Type", "Goals", "Match", "Result"]));

  // p2. best duo
  var duo = {}; ev.forEach(function (e) { if (e.event_type === "goal" && e.related_player_id) { var k = e.related_player_id + ">" + e.player_id; duo[k] = duo[k] || { a: e.related_player_id, s: e.player_id, n: 0, ms: [] }; duo[k].n++; duo[k].ms.push(M[e.match_id]); } });
  var duos = Object.keys(duo).map(function (k) { return duo[k]; }).sort(function (a, b) { return b.n - a.n; });
  add("duo", "players", "🤝", "Best scorer–assist duo",
    duos.length ? esc(P(duos[0].a)) + " → " + esc(P(duos[0].s)) : "–", duos.length ? duos[0].n + " goal" + (duos[0].n > 1 ? "s" : "") + " together" : "",
    "<h4>Most goals created by one passer for one scorer</h4>" + rows(duos.slice(0, 8).map(function (x) { return [c.pl(x.a, P(x.a)) + " → " + c.pl(x.s, P(x.s)), x.n, x.ms.map(mlink).join(" · ")]; }), ["Assist → Goal", "Goals", "Matches"]));

  // p3. Player of the match
  var po = {}; ev.forEach(function (e) { if (e.event_type === "player_of_match") { po[e.player_id] = po[e.player_id] || { pid: e.player_id, ms: [] }; po[e.player_id].ms.push(M[e.match_id]); } });
  var pol = Object.keys(po).map(function (k) { return po[k]; }).sort(function (a, b) { return b.ms.length - a.ms.length; });
  var lostPotm = ev.filter(function (e) { if (e.event_type !== "player_of_match") return false; var m = M[e.match_id]; return gf(m, e.team_id) < gf(m, other(m, e.team_id)); });
  add("potm", "players", "🌟", "Most Player of the Match awards",
    pol.length ? names(winners(pol, function (x) { return x.ms.length; }), function (x) { return esc(P(x.pid)); }) + " · " + pol[0].ms.length : "–",
    lostPotm.length ? plural(lostPotm.length, "award") + " went to a player on the losing side" : "Every award so far went to the winning side or a draw",
    "<h4>Awards</h4>" + rows(pol.slice(0, 10).map(function (x) { return [c.pl(x.pid, P(x.pid)), x.ms.length, x.ms.map(mlink).join(" · ")]; }), ["Player", "Awards", "Matches"]));

  // p4. penalties and own goals
  var pens = ev.filter(function (e) { return e.event_type === "goal" && e.is_penalty; }), ogs = ev.filter(function (e) { return e.event_type === "own_goal"; });
  add("pen", "players", "🎯", "Penalties and own goals",
    plural(pens.length, "penalty goal", "penalty goals") + " · " + plural(ogs.length, "own goal"), ogs.length ? "Own goals gifted to the opponent in " + plural(ogs.length, "match", "matches") : "No own goals yet",
    "<h4>Penalty goals</h4>" + (pens.length ? rows(pens.map(function (e) { return [c.pl(e.player_id, P(e.player_id)), esc(T(e.team_id)), mlink(M[e.match_id])]; }), ["Scorer", "Team", "Match"]) : '<p class="muted">None.</p>') +
    "<h4>Own goals</h4>" + (ogs.length ? rows(ogs.map(function (e) { return [c.pl(e.player_id, P(e.player_id)), esc(T(e.team_id)), mlink(M[e.match_id])]; }), ["Player", "Team", "Match"]) : '<p class="muted">None.</p>'));

  // p5. ever-present
  var gp = {}; var teamMatches = {}; tm.forEach(function (r) { teamMatches[r.t] = (teamMatches[r.t] || 0) + 1; });
  c.apps.forEach(function (a) { if (isDone[a.match_id] && a.status === "played") { gp[a.player_id] = gp[a.player_id] || { pid: a.player_id, n: 0, teams: {} }; gp[a.player_id].n++; gp[a.player_id].teams[a.team_id] = 1; } });
  var gpl = Object.keys(gp).map(function (k) { return gp[k]; });
  var evp = gpl.filter(function (x) { var ts = Object.keys(x.teams); return ts.length === 1 && x.n === teamMatches[ts[0]]; });
  var maxTm = Math.max.apply(null, [0].concat(Object.keys(teamMatches).map(function (k) { return teamMatches[k]; })));
  add("ever", "players", "🛡️", "Ever-presents",
    evp.length ? plural(evp.length, "player") + " played every match" : "None yet",
    "Every team has played " + maxTm + " matches so far",
    "<h4>Played every match for their team</h4>" + rows(evp.sort(function (a, b) { return P(a.pid).localeCompare(P(b.pid)); }).map(function (x) { return [c.pl(x.pid, P(x.pid)), x.n, esc(T(Object.keys(x.teams)[0]))]; }), ["Player", "Games", "Team"]) +
    "<h4>Most games played</h4>" + rows(top(gpl, function (x) { return x.n; }, 8).map(function (x) { return [c.pl(x.pid, P(x.pid)), x.n, esc(Object.keys(x.teams).map(function (t) { return T(t); }).join(" / "))]; }), ["Player", "Games", "Team"]));

  // =============== TEAMS ===============
  // s1. streaks
  function streaks(t) { var r = tm.filter(function (x) { return x.t === t; }); var best = { w: 0, u: 0, l: 0, nw: 0 }, cur = { w: 0, u: 0, l: 0, nw: 0 };
    r.forEach(function (x) { cur.w = x.res === "W" ? cur.w + 1 : 0; cur.u = x.res !== "L" ? cur.u + 1 : 0; cur.l = x.res === "L" ? cur.l + 1 : 0; cur.nw = x.res !== "W" ? cur.nw + 1 : 0; Object.keys(best).forEach(function (k) { if (cur[k] > best[k]) best[k] = cur[k]; }); });
    return { t: t, best: best, cur: cur }; }
  var st = TEAMS.map(streaks), bw = st.length ? winners(st, function (x) { return x.best.w; }) : [], bu = st.length ? winners(st, function (x) { return x.best.u; }) : [];
  add("streak", "teams", "📈", "Winning and unbeaten streaks",
    bw.length ? "Longest win run: " + bw[0].best.w : "–", bu.length ? "Longest unbeaten run: " + bu[0].best.u + " – " + names(bu, function (x) { return esc(T(x.t)); }) : "",
    "<h4>Streaks by team</h4>" + rows(st.map(function (x) { return [c.tl(x.t, T(x.t)), x.best.w, x.cur.w, x.best.u, x.cur.u, x.best.nw, x.best.l]; }), ["Team", "Best win run", "Now", "Best unbeaten", "Now", "Longest without a win", "Longest losing run"]));

  // s2. fair play
  var fp = TEAMS.map(function (t) { var es = ev.filter(function (e) { return e.team_id === t; }); var y = es.filter(function (e) { return e.event_type === "yellow_card"; }).length, r = es.filter(function (e) { return e.event_type === "red_card"; }).length, f = es.filter(function (e) { return e.event_type === "foul"; }).length; return { t: t, y: y, r: r, f: f }; });
  var fair = fp.length ? fp.slice().sort(function (a, b) { return (a.y * 2 + a.r * 5 + a.f) - (b.y * 2 + b.r * 5 + b.f); }) : [];
  add("fair", "teams", "🤝", "Fair play",
    fair.length ? "Cleanest: " + esc(T(fair[0].t)) : "–", fair.length ? "Most cards and fouls: " + esc(T(fair[fair.length - 1].t)) : "",
    "<h4>Discipline table (fewest first)</h4>" + rows(fair.map(function (x, i) { return [(i + 1) + ". " + c.tl(x.t, T(x.t)), x.y, x.r, x.f, x.y * 2 + x.r * 5 + x.f]; }), ["Team", "Yellow", "Red", "Fouls", "Score (Y×2 + R×5 + F)"]));

  // =============== MORE TRIVIA ===============
  // L. League at a glance
  var totG = done.reduce(function (s, m) { return s + m.home_score + m.away_score; }, 0);
  var draws = done.filter(function (m) { return m.home_score === m.away_score; }), oneG = done.filter(function (m) { return Math.abs(m.home_score - m.away_score) === 1; }), bigW = done.filter(function (m) { return Math.abs(m.home_score - m.away_score) >= 3; });
  add("glance", "goals", "📊", "The league at a glance",
    plural(totG, "goal") + " · " + (n ? (totG / n).toFixed(2) : "0") + " per match",
    plural(n, "match", "matches") + " played · " + plural(draws.length, "draw") + " · " + plural(oneG.length, "one-goal game"),
    "<h4>Totals</h4>" + rows([["Matches played", n], ["Goals", totG], ["Goals per match", n ? (totG / n).toFixed(2) : "–"], ["Draws", draws.length + " (" + pct(draws.length, n) + ")"], ["Won by exactly 1 goal", oneG.length + " (" + pct(oneG.length, n) + ")"], ["Won by 3+ goals", bigW.length + " (" + pct(bigW.length, n) + ")"], ["Own goals", ogsAll()], ["1st-half goals / 2nd-half goals", h1 + " / " + h2]], ["", "Count"]) +
    "<h4>Goals per match day</h4>" + rows(dayList.map(function (d) { return ["Day " + d.day, d.g, (d.g / d.ms.length).toFixed(2)]; }), ["Day", "Goals", "Per match"]) + note(timeNote));
  function ogsAll() { return ev.filter(function (e) { return e.event_type === "own_goal"; }).length; }

  // T. Wins / draws / losses by team
  var rec = TEAMS.map(function (t) { var o = tally(tm.filter(function (r) { return r.t === t; })); o.t = t; o.pts = o.w * 2 + o.d; return o; });
  var mw = winners(rec, function (x) { return x.w; }), md = winners(rec, function (x) { return x.d; }), ml2 = winners(rec, function (x) { return x.l; });
  add("wdl", "teams", "📋", "Most wins, draws and losses",
    "Wins: " + names(mw, function (x) { return esc(T(x.t)); }) + " (" + mw[0].w + ")",
    "Draws: " + names(md, function (x) { return esc(T(x.t)); }) + " (" + md[0].d + ") · Losses: " + names(ml2, function (x) { return esc(T(x.t)); }) + " (" + ml2[0].l + ")",
    "<h4>Full record</h4>" + rows(rec.slice().sort(function (a, b) { return b.pts - a.pts || b.w - a.w; }).map(function (x) { return [c.tl(x.t, T(x.t)), x.p, x.w, x.d, x.l, x.pts]; }), ["Team", "Played", "Won", "Drawn", "Lost", "Points (win 2, draw 1)"]) +
    "<h4>Every result</h4>" + rows(done.map(function (m) { return [mlink(m), line(m)]; }), ["Match", "Result"]));

  // T2. Defence
  var def = teamGoals.slice().sort(function (a, b) { return a.ga - b.ga; });
  add("defence", "teams", "🧱", "Best and leakiest defence",
    def.length ? "Best: " + esc(T(def[0].t)) + " · " + def[0].ga + " against" : "–", def.length ? "Leakiest: " + esc(T(def[def.length - 1].t)) + " · " + def[def.length - 1].ga + " against" : "",
    "<h4>Goals against</h4>" + rows(def.map(function (x) { return [c.tl(x.t, T(x.t)), x.ga, x.p, (x.ga / x.p).toFixed(2), x.g - x.ga > 0 ? "+" + (x.g - x.ga) : (x.g - x.ga)]; }), ["Team", "Conceded", "Played", "Per match", "Goal difference"]));

  // T3. Fastest / latest goal per team
  var byT = TEAMS.map(function (t) { var a = all.filter(function (g) { return g.team === t; }); return { t: t, a: a, f: a.length ? a.slice().sort(function (x, y) { return inHalf(x) - inHalf(y); })[0] : null, l: a.length ? a.slice().sort(function (x, y) { return inHalf(y) - inHalf(x); })[0] : null }; });
  var bf = byT.filter(function (x) { return x.f; }).sort(function (a, b) { return inHalf(a.f) - inHalf(b.f); }), bl = byT.filter(function (x) { return x.l; }).sort(function (a, b) { return inHalf(b.l) - inHalf(a.l); });
  add("teamfast", "drama", "⏲️", "Fastest and latest goal by each team",
    bf.length ? "Fastest: " + esc(T(bf[0].t)) + " · " + clock(inHalf(bf[0].f)) : "–", bl.length ? "Latest: " + esc(T(bl[0].t)) + " · " + clock(inHalf(bl[0].l)) + " of the " + (bl[0].l.half === 1 ? "1st" : "2nd") + " half" : "",
    "<h4>Each team's quickest and latest goal in a half</h4>" + rows(byT.map(function (x) { return [c.tl(x.t, T(x.t)), x.f ? clock(inHalf(x.f)) + " · " + c.pl(x.f.pid, P(x.f.pid)) + " (" + mlink(x.f.m) + ")" : "–", x.l ? clock(inHalf(x.l)) + " · " + c.pl(x.l.pid, P(x.l.pid)) + " (" + mlink(x.l.m) + ")" : "–"]; }), ["Team", "Fastest (into a half)", "Latest (into a half)"]) + note("Clock = time into the half, out of 10:00. " + timeNote));

  // T4. Scored first yet lost
  var sfl = [], sfd = [];
  ordered.forEach(function (m) { var g = goalsBy[m.id] || []; if (!g.length) return; var first = g[0].team, f = gf(m, first), a = gf(m, other(m, first)); if (f < a) sfl.push({ m: m, t: first }); else if (f === a) sfd.push({ m: m, t: first }); });
  add("sflost", "drama", "💔", "Scored first, still lost",
    sfl.length ? plural(sfl.length, "time") : "Never so far", sfd.length ? plural(sfd.length, "more match", "more matches") + " where the first scorer only drew" : "",
    "<h4>Scored first and lost</h4>" + (sfl.length ? rows(sfl.map(function (x) { return [mlink(x.m), esc(T(x.t)), line(x.m)]; }), ["Match", "Team that scored first", "Result"]) : '<p class="muted">None yet.</p>') +
    "<h4>Scored first and drew</h4>" + (sfd.length ? rows(sfd.map(function (x) { return [mlink(x.m), esc(T(x.t)), line(x.m)]; }), ["Match", "Team that scored first", "Result"]) : '<p class="muted">None yet.</p>') +
    "<h4>By team (scored first, not won)</h4>" + rows(TEAMS.map(function (t) { return [c.tl(t, T(t)), sfl.filter(function (x) { return x.t === t; }).length, sfd.filter(function (x) { return x.t === t; }).length]; }), ["Team", "Lost", "Drew"]) + note(timeNote));

  // T5. Toss winners who chose Side
  var sideR = tr.filter(function (r) { return r.choice === "side"; }), startR = tr.filter(function (r) { return r.choice === "kickoff"; }), st2 = tally(sideR), st1 = tally(startR);
  var lostToss = tm.filter(function (r) { return r.tossWon === false; });
  add("tossside", "toss", "↔️", "Won the toss and chose Side",
    tr.length ? sideR.length + " of " + tr.length + " (" + pct(sideR.length, tr.length) + ")" : "–", tr.length ? "Then won " + st2.w + ", drew " + st2.d + ", lost " + st2.l + " · Chose Start and went " + wdl(st1) : "No toss recorded yet",
    "<h4>Win rate after each choice</h4>" + rows([["Chose Side", st2.p, st2.w, st2.d, st2.l, pct(st2.w, st2.p)], ["Chose Start (kick-off)", st1.p, st1.w, st1.d, st1.l, pct(st1.w, st1.p)], ["Lost the toss", lostToss.length, tally(lostToss).w, tally(lostToss).d, tally(lostToss).l, pct(tally(lostToss).w, lostToss.length)]], ["", "Matches", "Won", "Drew", "Lost", "Win %"]) +
    "<h4>By team</h4>" + rows(TEAMS.map(function (t) { var a = tr.filter(function (r) { return r.t === t; }), sd = a.filter(function (r) { return r.choice === "side"; }), lt = lostToss.filter(function (r) { return r.t === t; }); return [c.tl(t, T(t)), a.length, sd.length, a.length - sd.length, lt.length]; }), ["Team", "Tosses won", "Chose Side", "Chose Start", "Tosses lost"]) + note(tossNote));

  // P. Assists and unassisted goals
  var as = {}; ev.forEach(function (e) { if (e.event_type === "assist") { as[e.player_id] = as[e.player_id] || { pid: e.player_id, n: 0, ms: {} }; as[e.player_id].n++; as[e.player_id].ms[e.match_id] = 1; } });
  var asl = Object.keys(as).map(function (k) { return as[k]; }).sort(function (a, b) { return b.n - a.n; });
  var un = {}; ev.forEach(function (e) { if (e.event_type === "goal" && !e.related_player_id) { un[e.player_id] = un[e.player_id] || { pid: e.player_id, n: 0 }; un[e.player_id].n++; } });
  var unl = Object.keys(un).map(function (k) { return un[k]; }).sort(function (a, b) { return b.n - a.n; });
  var goalsTotal = ev.filter(function (e) { return e.event_type === "goal"; }).length, goalsAssisted = ev.filter(function (e) { return e.event_type === "goal" && e.related_player_id; }).length;
  add("assist", "players", "🅰️", "Most assists",
    asl.length ? names(winners(asl, function (x) { return x.n; }), function (x) { return esc(P(x.pid)); }) + " · " + asl[0].n : "–", goalsTotal ? goalsAssisted + " of " + goalsTotal + " scorecard goals had an assist (" + pct(goalsAssisted, goalsTotal) + ")" : "",
    "<h4>Assist leaders</h4>" + rows(asl.slice(0, 10).map(function (x, i) { return [(i + 1) + ". " + c.pl(x.pid, P(x.pid)), x.n, Object.keys(x.ms).length]; }), ["Player", "Assists", "Matches with an assist"]) + note("Only goals recorded goal-by-goal on a scorecard are counted."));
  add("unassisted", "players", "🦸", "Most goals scored without an assist",
    unl.length ? names(winners(unl, function (x) { return x.n; }), function (x) { return esc(P(x.pid)); }) + " · " + unl[0].n : "–", goalsTotal ? plural(goalsTotal - goalsAssisted, "unassisted goal") + " of " + goalsTotal + " (" + pct(goalsTotal - goalsAssisted, goalsTotal) + ")" : "",
    "<h4>Solo goals (no assist recorded)</h4>" + rows(unl.slice(0, 10).map(function (x, i) { var g = pg[x.pid] ? pg[x.pid].g : x.n; return [(i + 1) + ". " + c.pl(x.pid, P(x.pid)), x.n, g, pct(x.n, g)]; }), ["Player", "Unassisted goals", "All goals", "Share unassisted"]) + note("An unassisted goal has no assist recorded on the scorecard."));

  // P2. Captains
  var capMap = {}; c.apps.forEach(function (a) { if (!isDone[a.match_id] || !a.is_captain || a.status !== "played") return; var m = M[a.match_id], r = tm.filter(function (x) { return x.m.id === m.id && x.t === a.team_id; })[0]; if (!r) return; var k = a.player_id; capMap[k] = capMap[k] || { pid: k, w: 0, d: 0, l: 0, p: 0, rows: [] }; capMap[k].p++; capMap[k][r.res.toLowerCase()]++; capMap[k].rows.push(r); });
  var caps = Object.keys(capMap).map(function (k) { return capMap[k]; });
  var capOk = caps.filter(function (x) { return x.p >= 3; }).sort(function (a, b) { return (b.w / b.p) - (a.w / a.p) || b.p - a.p; });
  var capBest = capOk.length ? winners(capOk, function (x) { return Math.round(1000 * x.w / x.p); }) : [];
  add("capwin", "players", "©️", "Captain with the best win %",
    capBest.length ? names(capBest, function (x) { return esc(P(x.pid)); }) + " · " + pct(capBest[0].w, capBest[0].p) : "No captain has led 3 matches yet",
    capBest.length ? capBest[0].w + " wins in " + capBest[0].p + " matches as captain (min 3 matches)" : caps.length + " captains so far, none with 3 matches",
    "<h4>Captains with 3+ matches</h4>" + (capOk.length ? rows(capOk.map(function (x) { return [c.pl(x.pid, P(x.pid)), x.p, x.w, x.d, x.l, pct(x.w, x.p)]; }), ["Captain", "Matches", "Won", "Drawn", "Lost", "Win %"]) : '<p class="muted">Nobody yet.</p>') +
    "<h4>All captains</h4>" + rows(caps.slice().sort(function (a, b) { return b.p - a.p || b.w - a.w; }).map(function (x) { return [c.pl(x.pid, P(x.pid)), x.p, x.w, x.d, x.l, pct(x.w, x.p)]; }), ["Captain", "Matches", "Won", "Drawn", "Lost", "Win %"]) + note("Only matches where the lineup marks a captain are counted, so the numbers grow as lineups are entered."));

  // P3. Cards and fouls by player
  var dc = {}; ev.forEach(function (e) { if (e.event_type === "yellow_card" || e.event_type === "red_card" || e.event_type === "foul") { dc[e.player_id] = dc[e.player_id] || { pid: e.player_id, y: 0, r: 0, f: 0 }; dc[e.player_id][e.event_type === "yellow_card" ? "y" : e.event_type === "red_card" ? "r" : "f"]++; } });
  var dcl = Object.keys(dc).map(function (k) { return dc[k]; }).sort(function (a, b) { return (b.y * 2 + b.r * 5 + b.f) - (a.y * 2 + a.r * 5 + a.f); });
  add("badboy", "players", "🟨", "Most cards and fouls",
    dcl.length ? names(winners(dcl, function (x) { return x.y * 2 + x.r * 5 + x.f; }), function (x) { return esc(P(x.pid)); }) : "–", dcl.length ? dcl[0].y + " yellow · " + dcl[0].r + " red · " + dcl[0].f + " fouls" : "",
    "<h4>Discipline table</h4>" + rows(dcl.slice(0, 10).map(function (x, i) { return [(i + 1) + ". " + c.pl(x.pid, P(x.pid)), x.y, x.r, x.f]; }), ["Player", "Yellow", "Red", "Fouls"]));

  // T6. Scorer spread
  var spread = TEAMS.map(function (t) { var by = {}; ev.forEach(function (e) { if (e.event_type === "goal" && e.team_id === t) by[e.player_id] = (by[e.player_id] || 0) + 1; }); var ks = Object.keys(by).sort(function (a, b) { return by[b] - by[a]; }), tot = ks.reduce(function (s, k) { return s + by[k]; }, 0); return { t: t, n: ks.length, top: ks[0], topG: ks.length ? by[ks[0]] : 0, tot: tot }; });
  var spr = spread.filter(function (x) { return x.n; }).sort(function (a, b) { return b.n - a.n; });
  add("spread", "teams", "🎲", "Who shares the scoring?",
    spr.length ? "Most scorers: " + esc(T(spr[0].t)) + " · " + spr[0].n : "–", spr.length ? "Most reliant on one player: " + (function () { var r = spread.filter(function (x) { return x.tot > 0; }).sort(function (a, b) { return b.topG / b.tot - a.topG / a.tot; })[0]; return esc(T(r.t)) + " (" + esc(P(r.top)) + ", " + pct(r.topG, r.tot) + " of their goals)"; })() : "",
    "<h4>Different goalscorers per team</h4>" + rows(spread.map(function (x) { return [c.tl(x.t, T(x.t)), x.n, x.tot, x.top ? c.pl(x.top, P(x.top)) + " (" + x.topG + ")" : "–", pct(x.topG, x.tot)]; }), ["Team", "Different scorers", "Goals by players", "Top scorer", "Share of goals"]) + note("Own goals are not counted."));

  // D. Thrillers
  var thr = done.filter(function (m) { return m.home_score + m.away_score >= 2 && Math.abs(m.home_score - m.away_score) <= 1; });
  add("thrill", "drama", "😮", "Nail-biters",
    plural(oneG.length, "match", "matches") + " decided by one goal", plural(draws.length - nil.length, "scoring draw") + " · " + plural(bigW.length, "thrashing") + " (3+ goals)",
    "<h4>One-goal wins</h4>" + (oneG.length ? rows(oneG.map(function (m) { return [mlink(m), line(m)]; }), ["Match", "Result"]) : '<p class="muted">None.</p>') +
    "<h4>Scoring draws</h4>" + (draws.length - nil.length ? rows(draws.filter(function (m) { return m.home_score > 0; }).map(function (m) { return [mlink(m), line(m)]; }), ["Match", "Result"]) : '<p class="muted">None.</p>') +
    "<h4>Big wins (3+ goals)</h4>" + (bigW.length ? rows(bigW.map(function (m) { return [mlink(m), line(m)]; }), ["Match", "Result"]) : '<p class="muted">None.</p>'));

  // ---- Goal records: every card shows the PLAYER, TEAM and WHOLE-LEAGUE record side by side ----
  function trio(pv, tv, lv) { return '<span class="triv-line"><em>Player</em>' + pv + '</span><span class="triv-line"><em>Team</em>' + tv + '</span><span class="triv-line"><em>League</em>' + lv + "</span>"; }
  function setHead(id, html, sub) { items.forEach(function (it) { if (it.id === id) { it.headline = html; it.sub = sub || ""; } }); }
  function nmv(list, f, v) { return list.length ? names(list, f) + " · " + v : "–"; }
  var mTeam = []; done.forEach(function (m) { mTeam.push({ t: m.home_team_id, g: m.home_score, m: m }); mTeam.push({ t: m.away_team_id, g: m.away_score, m: m }); });
  var mTeamBest = mTeam.length ? winners(mTeam, function (x) { return x.g; }) : [];
  var bhl = bh;
  setHead("lg", trio(pw.length ? nmv(pw, function (x) { return esc(P(x.pid)); }, pw[0].g) : "–", tw.length ? nmv(tw, function (x) { return esc(T(x.t)); }, tw[0].g) : "–", plural(totG, "goal") + " in " + plural(n, "match", "matches")), "Season total. Tap for the full tables.");
  setHead("day", trio(pdl.length ? nmv(winners(pdl, function (x) { return x.g; }), function (x) { return esc(P(x.pid)) + " (Day " + x.day + ")"; }, Math.max.apply(null, pdl.map(function (x) { return x.g; }))) : "–", btd.length ? nmv(btd, function (x) { return esc(T(x.t)) + " (Day " + x.day + ")"; }, btd[0].g) : "–", bd.length ? "Day " + bd.map(function (d) { return d.day; }).join(" & Day ") + " · " + bd[0].g : "–"), "Most goals on one match day (2 matches per team per day).");
  setHead("match", trio(pml.length ? nmv(winners(pml, function (x) { return x.g; }), function (x) { return esc(P(x.pid)); }, pml[0].g) : "–", mTeamBest.length ? nmv(mTeamBest, function (x) { return esc(T(x.t)) + " (D" + x.m.match_day + " M" + x.m.match_number + ")"; }, mTeamBest[0].g) : "–", recMatches.length ? recMatches.length + (recMatches.length > 1 ? " matches" : " match") + " · " + recTot : "–"), "League = most goals by both teams in one match.");
  var hpl = halfPl.length ? winners(halfPl, function (x) { return x.g; }) : [];
  setHead("half", trio(hpl.length ? nmv(hpl, function (x) { return esc(P(x.pid)) + " (" + (x.h === 1 ? "1st" : "2nd") + " half, D" + x.m.match_day + " M" + x.m.match_number + ")"; }, hpl[0].g) : "–", bth.length ? nmv(bth, function (x) { return esc(T(x.t)) + " (" + (x.h === 1 ? "1st" : "2nd") + " half, D" + x.m.match_day + " M" + x.m.match_number + ")"; }, bth[0].g) : "–", bhl.length ? nmv(bhl, function (x) { return (x.h === 1 ? "1st" : "2nd") + " half, D" + x.m.match_day + " M" + x.m.match_number; }, bhl[0].tot) : "–"), "Counts matches where the order of goals is known (" + ordered.length + " of " + n + ").");

  // ---- Kick-off: every way a team ended up starting ----
  var kickAll = TEAMS.map(function (t) { var r = tm.filter(function (x) { return x.t === t && x.kicked === true; }); var viaStart = r.filter(function (x) { return x.choice === "kickoff"; }), viaOpp = r.filter(function (x) { return x.choice !== "kickoff"; }); var tv = tally(viaStart), to = tally(viaOpp); return [c.tl(t, T(t)), r.length, viaStart.length, wdl(tv), viaOpp.length, wdl(to), wdl(tally(r))]; });
  items.forEach(function (it) { if (it.id === "kickwins") it.detail += "<h4>How each team came to kick off</h4>" + rows(kickAll, ["Team", "Times they kicked off", "…by choosing Start", "Record (W-D-L)", "…because the toss winner chose Side", "Record (W-D-L)", "All kick-offs (W-D-L)"]); });

  // ---- Data check: what the trivia cannot see yet ----
  var capSet = {}; c.apps.forEach(function (a) { if (isDone[a.match_id] && a.is_captain) capSet[a.match_id + "|" + a.team_id] = 1; });
  var noToss = done.filter(function (m) { return !(m.toss_winner_team_id && m.toss_choice); }), noCap = done.filter(function (m) { return !capSet[m.id + "|" + m.home_team_id] || !capSet[m.id + "|" + m.away_team_id]; });
  var noPotm = done.filter(function (m) { return !ev.some(function (e) { return e.match_id === m.id && e.event_type === "player_of_match"; }); });
  var noGoals = done.filter(function (m) { return (m.home_score + m.away_score) > 0 && (goalsBy[m.id] || []).length !== m.home_score + m.away_score; });
  var noOrder = done.filter(function (m) { return !isOrdered[m.id] && (m.home_score + m.away_score) > 0 && (goalsBy[m.id] || []).length === m.home_score + m.away_score; });
  function mlist(a) { return a.length ? a.map(mlink).join(" · ") : "None. All good."; }
  add("dq", "check", "🔍", "What the trivia can and cannot see",
    (noToss.length + noGoals.length + noOrder.length + noCap.length) ? "Some scorecard details are missing" : "Every scorecard is complete",
    "Cards only use what is recorded. This lists the gaps so you can compare with the real matches.",
    "<h4>Toss not recorded (" + noToss.length + ")</h4><p>" + mlist(noToss) + "</p>" +
    "<h4>Score has goals that are not on the scorecard (" + noGoals.length + ")</h4><p>" + mlist(noGoals) + "</p>" +
    "<h4>Goals recorded but order unclear (" + noOrder.length + ")</h4><p>" + mlist(noOrder) + "</p>" +
    "<h4>Captain missing for one or both teams (" + noCap.length + ")</h4><p>" + mlist(noCap) + "</p>" +
    "<h4>No Player of the Match (" + noPotm.length + ")</h4><p>" + mlist(noPotm) + "</p>" +
    note("Comebacks, score-first, halves and fastest/latest goals need goal-by-goal scorecards. Toss cards need a recorded toss. Captain cards need a recorded captain."));

  return items;
}

// ---------- page ----------
function renderTrivia() {
  var box = document.getElementById("triv-body");
  if (!box) return;
  var chips = document.getElementById("triv-chips");
  chips.innerHTML = TRIV_CATS.map(function (c) { var k = c[0] === "all" ? TRIV.items.length : TRIV.items.filter(function (i) { return i.cat === c[0]; }).length; return '<button type="button" data-cat="' + c[0] + '" class="' + (TRIV.cat === c[0] ? "on" : "") + '">' + c[1] + " (" + k + ")</button>"; }).join("");
  var list = TRIV.items.filter(function (it) { return TRIV.cat === "all" || it.cat === TRIV.cat; });
  var cnt = document.getElementById("triv-count"); if (cnt) cnt.textContent = list.length + " trivia";
  if (!list.length) { box.innerHTML = '<p class="muted">No trivia in this group yet.</p>'; return; }
  box.innerHTML = list.map(function (it) {
    var open = TRIV.open === it.id;
    return '<div class="triv-card' + (open ? " open" : "") + '" data-id="' + it.id + '"><button type="button" class="triv-head" aria-expanded="' + open + '"><span class="triv-ico">' + it.icon + '</span><span class="triv-txt"><span class="triv-title">' + it.title + '</span><span class="triv-big">' + it.headline + '</span><span class="triv-sub">' + (it.sub || "") + '</span></span><span class="triv-chev">' + (open ? "▾" : "▸") + "</span></button>" +
      (open ? '<div class="triv-detail">' + it.detail + "</div>" : "") + "</div>";
  }).join("");
}
function trivWire() {
  document.getElementById("triv-chips").addEventListener("click", function (e) { var b = e.target.closest("button[data-cat]"); if (!b) return; TRIV.cat = b.getAttribute("data-cat"); renderTrivia(); });
  document.getElementById("triv-body").addEventListener("click", function (e) { var h = e.target.closest(".triv-head"); if (!h) return; var id = h.parentNode.getAttribute("data-id"); TRIV.open = TRIV.open === id ? null : id; renderTrivia(); });
}
async function loadTrivia() {
  var box = document.getElementById("triv-body");
  box.innerHTML = '<p class="muted">Loading…</p>';
  var sid = document.getElementById("triv-season").value, all = sid === "all";
  var mq = window.sb.from("matches").select("*");
  if (!all) mq = mq.eq("season_id", sid);
  var matches = (await mq).data || [];
  var ids = matches.map(function (m) { return m.id; });
  var events = ids.length ? await recFetchAll("match_events", ids) : [];
  var apps = ids.length ? await recFetchAll("match_appearances", ids) : [];
  TRIV.items = trivBuild({ matches: matches, events: events, apps: apps, esc: escapeHtml,
    tname: function (id) { return (TEAMS[id] && TEAMS[id].name) || "?"; }, pname: function (id) { return (PLAYERS[id] && PLAYERS[id].full_name) || (typeof pname === "function" ? pname(id) : "?"); },
    ml: function (m, label) { return matchLink(m, label); }, pl: function (id, name) { return playerLink(id, name); }, tl: function (id, name) { return teamLink(id, name); } });
  TRIV.loaded = true;
  renderTrivia();
}
function initTrivia(seasonOpts) {
  var sel = document.getElementById("triv-season");
  sel.innerHTML = seasonOpts;
  sel.addEventListener("change", loadTrivia);
  trivWire();
}
