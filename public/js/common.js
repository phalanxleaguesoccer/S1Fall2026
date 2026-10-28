// Shared header/footer injection + small helpers used across all pages.

function renderHeader(activePage) {
  var links = [
    ["index.html", "Standings"],
    ["matches.html", "Matches"],
    ["stats.html", "Stats"],
    ["teams.html", "Teams"],
    ["players.html", "Players"],
    ["auction.html", "Auction"],
    ["sponsors.html", "Sponsors"],
    ["admin/login.html", "Admin"]
  ];
  var nav = links.map(function (l) {
    var active = activePage === l[0] ? " active" : "";
    return '<a class="' + active.trim() + '" href="' + l[0] + '">' + l[1] + "</a>";
  }).join("");

  document.body.insertAdjacentHTML(
    "afterbegin",
    '<header class="site-header"><div class="container">' +
      '<a class="brand" href="index.html"><img class="logo" src="' + (window.IN_ADMIN_DIR ? "../" : "") + 'assets/brand/logo-icon.png" alt="Phalanx League Soccer logo"> Phalanx League Soccer</a>' +
      '<nav class="main-nav">' + nav + "</nav>" +
      "</div></header>"
  );
  renderEnvBanner();
}

// Preprod copy only (config.js sets ENV: "preprod"): a fixed red strip so a test
// site can never be mistaken for the live league. The live config has no ENV.
function renderEnvBanner() {
  var cfg = window.PHALANX_CONFIG || {};
  if (cfg.ENV !== "preprod" || document.getElementById("env-banner")) return;
  document.title = "[PREPROD] " + document.title;
  document.body.style.paddingBottom = "40px";
  document.body.insertAdjacentHTML(
    "beforeend",
    '<div id="env-banner" style="position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#b3261e;color:#fff;' +
      'font:600 13px/1.3 system-ui,sans-serif;padding:7px 12px;text-align:center;letter-spacing:.02em">' +
      "PREPROD · test copy, not the live league</div>"
  );
}

function renderFooter() {
  document.body.insertAdjacentHTML(
    "beforeend",
    '<footer class="site-footer">Phalanx League Soccer | <span id="footer-season">…</span> | 6-A-side | <span id="footer-views">…</span></footer>'
  );

  // Fill in the current season's name once Supabase is ready.
  if (window.sb) {
    getCurrentSeason().then(function (season) {
      var el = document.getElementById("footer-season");
      if (el) el.textContent = season ? season.name : "—";
    });
    trackPageView("site").then(function (count) {
      var el = document.getElementById("footer-views");
      if (el) el.textContent = formatViewCount(count) + " site-wide";
    });
  }
}

// Renders a breadcrumb trail right under the header so people can jump back
// to any ancestor page without relying on the browser's back button.
// `crumbs` is an array of { label, href } — href is omitted (or null) on the
// last entry, which renders as plain (non-link) text for the current page.
function renderBreadcrumbs(crumbs) {
  var html = crumbs.map(function (c, i) {
    var isLast = i === crumbs.length - 1;
    var piece = (!isLast && c.href)
      ? '<a href="' + escapeHtml(c.href) + '">' + escapeHtml(c.label) + "</a>"
      : '<span class="current"' + (isLast ? ' id="crumb-current"' : '') + '>' + escapeHtml(c.label) + "</span>";
    return i === 0 ? piece : '<span class="sep">/</span>' + piece;
  }).join("");

  document.body.insertAdjacentHTML(
    "afterbegin",
    '<nav class="breadcrumbs">' + html + "</nav>"
  );

  // Header is inserted afterbegin too (see renderHeader), and is always
  // called before renderBreadcrumbs on every page, so the breadcrumb nav
  // (inserted after the header exists) ends up directly below it.
  var header = document.querySelector(".site-header");
  var nav = document.querySelector(".breadcrumbs");
  if (header && nav && header.nextSibling !== nav) {
    header.insertAdjacentElement("afterend", nav);
  }
}

function formatViewCount(count) {
  if (count === null || count === undefined) return "—";
  return count.toLocaleString() + (count === 1 ? " view" : " views");
}

// Counts every page load as a view (people revisit the same player/team page
// multiple times a day for different research, and each of those should
// count), then returns the current total.
async function trackPageView(pageKey) {
  try {
    var incRes = await window.sb.rpc("increment_page_view", { p_key: pageKey });
    if (!incRes.error && typeof incRes.data === "number") return incRes.data;
  } catch (err) {
    // RPC can fail (offline, etc.) — fall through to a plain read so the
    // count still displays even if this particular visit didn't increment.
  }
  try {
    var res = await window.sb.from("page_views").select("view_count").eq("page_key", pageKey).maybeSingle();
    return res.data ? res.data.view_count : null;
  } catch (err) {
    return null;
  }
}

function fixHref(activePage) {
  // Pages under /admin/ need "../" prefixes for nav links; patched here so
  // renderHeader() can stay simple for top-level pages.
  if (window.IN_ADMIN_DIR) {
    document.querySelectorAll("nav.main-nav a").forEach(function (a) {
      var href = a.getAttribute("href");
      if (href.indexOf("admin/") !== 0 && href !== "admin/login.html") {
        a.setAttribute("href", "../" + href);
      }
    });
    document.querySelector(".brand").setAttribute("href", "../index.html");
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function qs(name) {
  var params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function showError(el, message) {
  el.textContent = message;
  el.className = "error-msg";
}
function showSuccess(el, message) {
  el.textContent = message;
  el.className = "success-msg";
}

// Returns { data: currentSeason } for the season flagged is_current = true.
async function getCurrentSeason() {
  var res = await window.sb.from("seasons").select("*").eq("is_current", true).limit(1).single();
  return res.data;
}

// Kickoff times are always shown in Eastern time (EST/EDT as applicable),
// no matter where the viewer's browser is, so "9:00 PM" means the same thing
// for everyone and a late-evening match never shows up on the wrong date.
function formatKickoff(iso) {
  return new Date(iso).toLocaleString("en-US", {
    timeZone: "America/New_York", weekday: "short", month: "short", day: "numeric",
    year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short"
  });
}
function formatKickoffDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    timeZone: "America/New_York", month: "short", day: "numeric", year: "numeric"
  });
}

// ---------- Captains ----------
// capApps: match_appearances rows with is_captain = true (any teams / seasons).
// matchOf(matchId) -> match row.  opts.seasonRank: { seasonId: n } (older seasons first).
// Returns { teams: { teamId: [entry...] }, all: [entry...], changes: [entry...] } in match order.
// entry = { app, match, team_id, player_id, changeFrom (previous captain of that team, when it changed),
//           leagueFirst (set on changes[0]: the first change in the whole league) }
// Every captain is a captain: there is no stand-in distinction, any switch of captain is a change.
function captainTimeline(capApps, matchOf, opts) {
  var rank = (opts && opts.seasonRank) || {};
  var keyOf = function (a) { var m = matchOf(a.match_id) || {}; return [rank[m.season_id] || 0, m.match_day || 0, m.match_number || 0]; };
  var cmp = function (a, b) { var x = keyOf(a), y = keyOf(b); return x[0] - y[0] || x[1] - y[1] || x[2] - y[2]; };
  var rows = capApps.filter(function (a) { return matchOf(a.match_id); }).slice().sort(cmp);
  var teams = {};
  rows.forEach(function (a) { (teams[a.team_id] = teams[a.team_id] || []).push(a); });
  var out = { teams: {}, all: [], changes: [] };
  Object.keys(teams).forEach(function (tid) {
    var prev = null, entries = [];
    teams[tid].forEach(function (a) {
      var e = { app: a, match: matchOf(a.match_id), team_id: tid, player_id: a.player_id };
      if (prev && prev !== a.player_id) e.changeFrom = prev;
      prev = a.player_id;
      entries.push(e);
    });
    out.teams[tid] = entries;
    entries.forEach(function (e) { out.all.push(e); if (e.changeFrom) out.changes.push(e); });
  });
  var ecmp = function (a, b) { return cmp(a.app, b.app); };
  out.all.sort(ecmp); out.changes.sort(ecmp);
  if (out.changes.length) out.changes[0].leagueFirst = true;
  return out;
}
// Links used wherever a team / match / player name is shown, so every name opens its page.
function teamLink(id, name) { return id ? '<a href="team.html?id=' + id + '">' + escapeHtml(name || "?") + "</a>" : escapeHtml(name || "TBD"); }
function matchLink(m, label) { return '<a href="match.html?id=' + m.id + '">' + (label || matchLabelShort(m)) + "</a>"; }
function playerLink(id, name) { return '<a href="player.html?id=' + id + '">' + escapeHtml(name || "?") + "</a>"; }
function matchLabelShort(m) { return "Day " + m.match_day + " · M" + m.match_number; }


// ---------- Standings tie-breaks (shared by the Standings page and Stats > Records) ----------
// Rows tied on pts, gd, gf and ga are ordered by head-to-head (points, then
// goal difference, in the matches played between just those teams). If they
// are STILL level, the admin-recorded penalty shoot-out order decides (only
// available once the tournament is complete). Anything nothing can separate
// is flagged r.unresolved so the page can ask for a shoot-out.
// shootoutPos: { teamId: position } (1 = best), or null when not allowed yet.
function resolveTies(rows, matches, shootoutPos) {
  function key(r) { return [r.pts, r.gd, r.gf, r.ga].join("|"); }
  var out = [];
  var i = 0;
  while (i < rows.length) {
    var j = i + 1;
    while (j < rows.length && key(rows[j]) === key(rows[i])) j++;
    var group = rows.slice(i, j);
    if (group.length > 1) {
      var ids = group.map(function (r) { return r.team.id; });
      var h = {};
      ids.forEach(function (id) { h[id] = { pts: 0, gd: 0 }; });
      matches.forEach(function (m) {
        if (!h[m.home_team_id] || !h[m.away_team_id]) return;
        if (m.status === "forfeited") {
          // Forfeit: the other team gets the win (2 pts); no goals recorded.
          if (m.forfeited_by_team_id === m.home_team_id) h[m.away_team_id].pts += 2;
          else if (m.forfeited_by_team_id === m.away_team_id) h[m.home_team_id].pts += 2;
          return;
        }
        if (m.home_score == null || m.away_score == null) return;
        var hs = m.home_score, as = m.away_score;
        h[m.home_team_id].gd += hs - as;
        h[m.away_team_id].gd += as - hs;
        if (hs > as) h[m.home_team_id].pts += 2;
        else if (as > hs) h[m.away_team_id].pts += 2;
        else { h[m.home_team_id].pts += 1; h[m.away_team_id].pts += 1; }
      });
      function pos(r) {
        var v = shootoutPos && shootoutPos[r.team.id];
        return v == null ? Infinity : v;
      }
      function cmp(a, b) {
        var x = h[a.team.id], y = h[b.team.id];
        if (y.pts !== x.pts) return y.pts - x.pts;
        if (y.gd !== x.gd) return y.gd - x.gd;
        var pa = pos(a), pb = pos(b);
        if (pa === pb) return 0;
        return pa < pb ? -1 : 1;
      }
      group.sort(cmp);
      var runId = 0;
      for (var k = 0; k < group.length; k++) {
        if (k > 0 && cmp(group[k - 1], group[k]) !== 0) runId++;
        group[k].tieKey = i + ":" + runId;
        var same = (k > 0 && cmp(group[k - 1], group[k]) === 0) ||
                   (k < group.length - 1 && cmp(group[k], group[k + 1]) === 0);
        if (same) group[k].unresolved = true;
      }
    }
    out = out.concat(group);
    i = j;
  }
  return out;
}

// ---------- Win / draw / loss estimate for a match (Poisson goals model) ----------
// matches: completed matches of one season (or all). Attack and defence come from the goals so far, shrunk toward the
// league average with K "prior" games, so a few matches cannot swing it far. Returns {w, d, l, games} for team a vs team b, or null.
function winModel(matches, a, b) {
  var done = matches.filter(function (m) { return m.status === "completed" && m.home_score != null && m.away_score != null; });
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

// Keeps an open page current: every 12 s (only while the tab is visible) it looks at a cheap fingerprint of the results
// (match status / scores / live phase plus how many events and lineup rows exist). When it changes, onChange() is called,
// so tables, records and stats refresh by themselves when a match ends or details are added later.
function watchResults(onChange, everyMs) {
  var last = null, busy = false;
  async function fingerprint() {
    var r = await Promise.all([
      window.sb.from("matches").select("id, status, home_score, away_score, live_phase"),
      window.sb.from("match_events").select("id", { count: "exact", head: true }),
      window.sb.from("match_appearances").select("id", { count: "exact", head: true })
    ]);
    if (r[0].error) return null;
    return JSON.stringify([(r[0].data || []).map(function (m) { return [m.id, m.status, m.home_score, m.away_score, m.live_phase]; }).sort(), r[1].count, r[2].count]);
  }
  async function tick() {
    if (busy || document.hidden) return;
    busy = true;
    try {
      var f = await fingerprint();
      if (f !== null) { if (last !== null && f !== last) await onChange(); last = f; }
    } catch (e) {} finally { busy = false; }
  }
  tick();
  return setInterval(tick, everyMs || 12000);
}

// One-week transfers ("loans"): a player whose lineup row names a team other than his roster team that match day
// plays for that team that day. withLoans() adds a virtual roster row for the other team (only its loan matches count)
// and makes his home-team matches on those match days not count at all (neither played nor absent).
// rosterSkip(r, m) tells the stats loops which (roster row, match) pairs to ignore.
function withLoans(roster, apps, matches) {
  var Mx = {}; (matches || []).forEach(function (m) { Mx[m.id] = m; });
  var home = {}; roster.forEach(function (r) { if (!r.loan) home[r.season_id + "|" + r.player_id] = r; });
  var skip = {}, loans = {};
  (apps || []).forEach(function (a) {
    var m = Mx[a.match_id]; if (!m) return;
    var h = home[m.season_id + "|" + a.player_id];
    if (!h || h.team_id === a.team_id) return;
    var k = m.season_id + "|" + a.player_id;
    (skip[k] = skip[k] || {})[m.match_day] = true;
    var lk = k + "|" + a.team_id;
    loans[lk] = loans[lk] || { id: "loan-" + lk, season_id: m.season_id, player_id: a.player_id, team_id: a.team_id, is_owner: false, auction_price: null, jersey_number: null, loan: true, loanMatches: {} };
    loans[lk].loanMatches[m.id] = true;
  });
  var out = roster.map(function (r) { var s = skip[r.season_id + "|" + r.player_id]; return s && !r.loan ? Object.assign({}, r, { skipDays: s }) : r; });
  Object.keys(loans).forEach(function (k) { out.push(loans[k]); });
  return out;
}
function rosterSkip(r, m) { return r.loan ? !r.loanMatches[m.id] : !!(r.skipDays && r.skipDays[m.match_day]); }
