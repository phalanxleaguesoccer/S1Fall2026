// Live scoring: shared helpers for the admin Live desk and the public pages.
// A match is "live" while matches.live_phase is set: h1 (first half) | ht (half-time) | h2 (second half) | ft (full time, not yet confirmed).
// The admin always enters TIME REMAINING in the half; visitors always see TIME PLAYED:
//   1st half  7:20 left  ->  2:40 played
//   2nd half  4:50 left  ->  15:10 played (10:00 + 5:10)
// The database computes events.minute / events.second the same way (sql/migration_live_scoring.sql).
window.LIVE = (function () {
  var HALF = 600;          // seconds in one half. Keep equal to live_half_seconds() in the SQL.
  var MIN_PLAYERS = 4;     // players a team needs before kick-off
  var cfg = window.PHALANX_CONFIG || {};
  var enabled = cfg.LIVE_DESK_ENABLED !== false;   // set LIVE_DESK_ENABLED: false in config.js to hide everything live
  var offset = 0;          // server time minus this device's time, ms

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function mmss(sec) { sec = Math.max(0, Math.round(sec)); return pad(Math.floor(sec / 60)) + ":" + pad(sec % 60); }
  function played(sec) { sec = Math.max(0, Math.round(sec)); return Math.floor(sec / 60) + ":" + pad(sec % 60); }   // 2:40, 15:10
  function elapsed(half, rem) { return (half === 1 ? 0 : HALF) + (HALF - rem); }
  function parseRem(text) {   // "7:20" or "07:20" -> seconds, or null when it is not a valid time inside a half
    var m = /^(\d{1,2}):([0-5]\d)$/.exec(String(text || "").trim());
    if (!m) return null;
    var s = +m[1] * 60 + +m[2];
    return s > HALF ? null : s;
  }
  function isLive(m) { return enabled && !!(m && m.live_phase); }
  function now() { return Date.now() + offset; }
  function remaining(m) {   // seconds left on the clock right now
    if (m.clock_rem == null) return HALF;
    if (!m.clock_running || !m.clock_at) return m.clock_rem;
    return Math.max(0, m.clock_rem - (now() - Date.parse(m.clock_at)) / 1000);
  }
  function playedNow(m) {   // seconds of match time played (both halves)
    var half = m.live_phase === "h2" || m.live_phase === "ft" ? 2 : 1;
    if (m.live_phase === "ht") return HALF;
    if (m.live_phase === "ft") return 2 * HALF - (m.clock_rem == null ? 0 : m.clock_rem);
    return elapsed(half, remaining(m));
  }
  function phaseText(m) {
    return { h1: "1st half", ht: "Half-time", h2: "2nd half", ft: "Full time" }[m.live_phase] || "";
  }
  function goalFor(e, teamId) { return (e.event_type === "goal" && e.team_id === teamId) || false; }
  function score(m, events) {   // live score: goals for each side plus the other side's own goals
    var h = 0, a = 0;
    (events || []).forEach(function (e) {
      if (e.match_id && e.match_id !== m.id) return;
      if (e.event_type === "goal") { if (e.team_id === m.home_team_id) h++; else if (e.team_id === m.away_team_id) a++; }
      else if (e.event_type === "own_goal") { if (e.team_id === m.home_team_id) a++; else if (e.team_id === m.away_team_id) h++; }
    });
    return { h: h, a: a };
  }
  async function syncClock(sb) {   // learn the server clock so every device agrees on the countdown
    try {
      var t0 = Date.now(), r = await sb.rpc("server_now");
      if (r && r.data) { var t1 = Date.now(); offset = Date.parse(r.data) - (t0 + t1) / 2; }
    } catch (e) {}
  }
  // Subscribe to realtime changes if the browser client supports it; polling is the safety net.
  function subscribe(sb, matchId, onChange) {
    try {
      if (!sb.channel) return null;
      var ch = sb.channel("live-" + (matchId || "all"));
      var f = matchId ? { filter: "match_id=eq." + matchId } : {};
      ch.on("postgres_changes", Object.assign({ event: "*", schema: "public", table: "match_events" }, f), onChange)
        .on("postgres_changes", Object.assign({ event: "*", schema: "public", table: "matches" }, matchId ? { filter: "id=eq." + matchId } : {}), onChange)
        .on("postgres_changes", Object.assign({ event: "*", schema: "public", table: "match_appearances" }, f), onChange)
        .subscribe();
      return ch;
    } catch (e) { return null; }
  }
  return { HALF: HALF, MIN_PLAYERS: MIN_PLAYERS, enabled: enabled, mmss: mmss, played: played, elapsed: elapsed, parseRem: parseRem,
    isLive: isLive, remaining: remaining, playedNow: playedNow, phaseText: phaseText, score: score, syncClock: syncClock, subscribe: subscribe, now: now };
})();
