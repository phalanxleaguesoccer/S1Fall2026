// Live Desk: admin + approved co-admin run a match live.
// Rules of the road:
//  * The admin only types TIME REMAINING in the half; time played is computed (LIVE.elapsed) and the database re-computes it.
//  * Scores are never typed: they come from the goal events. At confirm time the database recomputes the final score again.
//  * Every change is recorded by the database in audit_log (who, what, when). Removing something needs a typed reason.
window.IN_ADMIN_DIR = true;
var $ = function (s) { return document.querySelector(s); };
var U = null, ROLE = null, LABEL = "", SEASON = null, MATCHES = [], M = null, TEAMS = {}, ROST = { H: [], A: [] }, PLAYER = {}, APP = {}, EV = [], LOCK = null, AUD = [];
var DRAFT = null, BUSY = false, TAB = "desk", HEART = null, POLL = null, TICK = null, TOASTT = null, CHAN = null;
var TYPE = { goal: "Goal", own_goal: "Own goal", yellow_card: "Yellow card", red_card: "Red card", foul: "Foul", save: "Save", assist: "Assist", player_of_match: "Player of the match" };
var COLOR = { goal: "var(--ev-goal)", own_goal: "var(--ev-goal)", yellow_card: "var(--ev-yellow)", red_card: "var(--ev-red)", foul: "var(--ev-foul)", save: "var(--ev-save)" };
var LOCK_STALE = 45;   // seconds without a heartbeat before someone else may score without "Take over"

function esc(s) { return escapeHtml(s == null ? "" : String(s)); }
function toast(msg, bad) {
  var t = document.getElementById("ld-toast");
  if (!t) { t = document.createElement("div"); t.id = "ld-toast"; t.style.cssText = "position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:99;max-width:92vw;padding:10px 16px;border-radius:10px;font-weight:600;box-shadow:0 6px 24px rgba(0,0,0,.6);"; document.body.appendChild(t); }
  t.textContent = msg; t.style.background = bad ? "var(--coral-2)" : "#1f6b45"; t.style.color = "#fff"; t.style.display = "block";
  clearTimeout(TOASTT); TOASTT = setTimeout(function () { t.style.display = "none"; }, bad ? 7000 : 2200);
}
function etStr(ts) {
  return new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true, timeZoneName: "short" }).format(new Date(ts));
}
function tname(id) { return TEAMS[id] ? TEAMS[id].name : "?"; }
function pname(id) { return PLAYER[id] ? PLAYER[id].full_name : "?"; }
function sideId(k) { return k === "H" ? M.home_team_id : M.away_team_id; }
function otherTeam(id) { return id === M.home_team_id ? M.away_team_id : M.home_team_id; }
function phase() { return M.status !== "scheduled" ? "final" : (M.live_phase || "pre"); }

// ---------------------------------------------------------------- sign in / access
function show(id, on) { var e = document.getElementById(id); if (e) e.classList.toggle("hide", !on); }
function showOnly(id) { ["gate", "pending", "nodb", "desk"].forEach(function (x) { show(x, x === id); }); show("logout-btn", id !== "gate"); }
function gateTab(up) { show("g-signin", !up); show("g-signup", up); $("#g-in").className = up ? "" : "on"; $("#g-up").className = up ? "on" : ""; }
$("#g-in").onclick = function () { gateTab(false); }; $("#g-up").onclick = function () { gateTab(true); };
$("#signin-form").addEventListener("submit", async function (e) {
  e.preventDefault(); var m = $("#si-msg"); m.textContent = "Signing in…"; m.className = "muted";
  var r = await window.sb.auth.signInWithPassword({ email: $("#si-email").value.trim(), password: $("#si-pass").value });
  if (r.error) { showError(m, r.error.message); return; }
  U = r.data.user; m.textContent = ""; afterLogin();
});
$("#signup-form").addEventListener("submit", async function (e) {
  e.preventDefault(); var m = $("#su-msg"); m.textContent = "Creating your account…"; m.className = "muted";
  var name = $("#su-name").value.trim(), email = $("#su-email").value.trim();
  var r = await window.sb.auth.signUp({ email: email, password: $("#su-pass").value, options: { data: { display_name: name } } });
  if (r.error) { showError(m, r.error.message); return; }
  if (r.data && r.data.session) { U = r.data.user; afterLogin(); return; }
  showSuccess(m, "Almost done: check your email and click the confirmation link, then come back here and sign in. A league admin then has to approve you.");
});
$("#logout-btn").onclick = async function () { await window.sb.auth.signOut(); location.reload(); };
$("#pending-out").onclick = $("#logout-btn").onclick;
$("#pending-refresh").onclick = function () { afterLogin(); };

async function boot() {
  var s = await window.sb.auth.getSession();
  if (!s.data || !s.data.session) { showOnly("gate"); return; }
  U = s.data.session.user; afterLogin();
}
async function afterLogin() {
  var a = await window.sb.from("admins").select("*").eq("user_id", U.id).maybeSingle();
  if (a.data) { ROLE = "admin"; LABEL = a.data.display_name || U.email; return enter(); }
  var c = await window.sb.from("coadmins").select("*").eq("user_id", U.id).maybeSingle();
  if (c.error) { showOnly("nodb"); return; }
  if (!c.data) {   // first sign-in after sign-up: file the request now
    var nm = (U.user_metadata && U.user_metadata.display_name) || (U.email || "").split("@")[0];
    var ins = await window.sb.from("coadmins").insert({ user_id: U.id, display_name: nm, email: U.email, status: "pending" });
    if (ins.error) { showOnly("nodb"); return; }
    c = { data: { status: "pending", display_name: nm } };
  }
  if (c.data.status === "approved") { ROLE = "coadmin"; LABEL = c.data.display_name; return enter(); }
  $("#pending-text").textContent = c.data.status === "revoked" ? "Your co-admin access has been turned off. Please contact a league admin." : "Your request is with the league admins. You will be able to run live matches as soon as one approves you.";
  $("#whoami").textContent = "Signed in as " + (c.data.display_name || U.email);
  showOnly("pending");
}

// ---------------------------------------------------------------- desk
async function enter() {
  var chk = await window.sb.rpc("server_now");
  if (chk.error) { showOnly("nodb"); return; }
  showOnly("desk");
  $("#whoami").textContent = "Signed in as " + LABEL + " (" + (ROLE === "admin" ? "Admin" : "Co-admin") + ")";
  await LIVE.syncClock(window.sb);
  SEASON = await getCurrentSeason();
  if (!SEASON) { toast("No current season", true); return; }
  var tr = await window.sb.from("teams").select("*"); (tr.data || []).forEach(function (t) { TEAMS[t.id] = t; });
  var mr = await window.sb.from("matches").select("*").eq("season_id", SEASON.id).eq("status", "scheduled").order("match_day", { ascending: true }).order("match_number", { ascending: true });
  MATCHES = (mr.data || []).filter(function (m) { return TEAMS[m.home_team_id] && TEAMS[m.away_team_id]; });
  if (!MATCHES.length) { $("#match-pick").innerHTML = "<option>No upcoming matches</option>"; $("#match-meta").textContent = "Every match is already confirmed."; return; }
  $("#match-pick").innerHTML = MATCHES.map(function (m) {
    return '<option value="' + m.id + '">Day ' + m.match_day + " · M" + m.match_number + " · " + esc(tname(m.home_team_id)) + " vs " + esc(tname(m.away_team_id)) + (m.live_phase ? " · LIVE" : (m.kickoff_at ? " · " + esc(formatKickoff(m.kickoff_at)) : "")) + "</option>";
  }).join("");
  var want = qs("match"), pick = MATCHES.filter(function (m) { return m.id === want; })[0] || MATCHES.filter(function (m) { return m.live_phase; })[0] ||
    MATCHES.slice().sort(function (a, b) { return Math.abs(Date.parse(a.kickoff_at || "2100-01-01") - Date.now()) - Math.abs(Date.parse(b.kickoff_at || "2100-01-01") - Date.now()); })[0];
  $("#match-pick").value = pick.id;
  await openMatch(pick.id);
  clearInterval(TICK); TICK = setInterval(tick, 250);
  clearInterval(POLL); POLL = setInterval(function () { if (!BUSY) refresh(); }, 4000);
  clearInterval(HEART); HEART = setInterval(heartbeat, 15000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
}
$("#match-pick").addEventListener("change", function () { openMatch(this.value); });

async function openMatch(id) {
  M = MATCHES.filter(function (m) { return m.id === id; })[0];
  DRAFT = null; closeSheet(); ROST = { H: [], A: [] }; PLAYER = {};
  var rr = await window.sb.from("team_season_rosters").select("*, players(*)").eq("season_id", M.season_id).in("team_id", [M.home_team_id, M.away_team_id]);
  (rr.data || []).forEach(function (r) {
    if (!r.players) return; PLAYER[r.player_id] = r.players;
    (r.team_id === M.home_team_id ? ROST.H : ROST.A).push(r.players);
  });
  ["H", "A"].forEach(function (k) { ROST[k].sort(function (a, b) { return a.full_name.localeCompare(b.full_name); }); });
  if (CHAN && window.sb.removeChannel) { try { window.sb.removeChannel(CHAN); } catch (e) {} }
  CHAN = LIVE.subscribe(window.sb, id, function () { if (!BUSY) refresh(); });
  await loadAll(); render();
}
async function loadAll() {
  var id = M.id;
  var r = await Promise.all([
    window.sb.from("matches").select("*").eq("id", id).single(),
    window.sb.from("match_appearances").select("*").eq("match_id", id),
    window.sb.from("match_events").select("*").eq("match_id", id).order("created_at", { ascending: true }),
    window.sb.from("live_locks").select("*").eq("match_id", id).maybeSingle()
  ]);
  if (r[0].data) { Object.assign(M, r[0].data); }
  APP = {}; (r[1].data || []).forEach(function (a) { APP[a.player_id] = a; });
  EV = r[2].data || []; LOCK = r[3].data || null;
  if (TAB === "audit") await loadAudit();
}
function sig() {
  var li = lockInfo();
  return JSON.stringify([M.live_phase, M.clock_rem, M.clock_running, M.clock_at, M.toss_winner_team_id, M.toss_choice, M.status, M.home_score, M.away_score, APP, EV, li.other ? li.other.label : li.mine ? "me" : "free", TAB]);
}
async function refresh() {   // poll/realtime: only redraw when something actually changed (keeps open dropdowns open)
  try { var before = sig(); await loadAll(); if (sig() !== before) render(); } catch (e) {}
}

// ---------------------------------------------------------------- edit lock (one scorer at a time)
function lockInfo() {
  if (!LOCK) return { free: true };
  if (LOCK.user_id === U.id) return { mine: true };
  var age = (LIVE.now() - Date.parse(LOCK.beat_at)) / 1000;
  return age < LOCK_STALE ? { other: LOCK, age: Math.round(age) } : { free: true };
}
async function claimLock() {
  var r = await window.sb.from("live_locks").upsert({ match_id: M.id, user_id: U.id, label: LABEL, beat_at: new Date(LIVE.now()).toISOString() }, { onConflict: "match_id" });
  if (r.error) { toast("Could not take the edit lock: " + r.error.message, true); return false; }
  LOCK = { match_id: M.id, user_id: U.id, label: LABEL, beat_at: new Date(LIVE.now()).toISOString() }; return true;
}
async function ensureLock() {
  if (M.status !== "scheduled") return false;
  var li = lockInfo();
  if (li.other) { toast(li.other.label + " is running this match. Tap “Take over” first.", true); render(); return false; }
  if (li.mine) return true;
  return claimLock();
}
async function heartbeat() { if (M && lockInfo().mine && M.status === "scheduled" && !document.hidden) { claimLock(); } }

// ---------------------------------------------------------------- data helpers
function appOf(pid) { return APP[pid] || null; }
function stOf(pid) { var a = appOf(pid); return a && a.status ? a.status : "played"; }
function squad(k) { return ROST[k]; }
function lineup(k) { return squad(k).filter(function (p) { return stOf(p.id) === "played"; }); }
function redOut(pid, exceptId) { return EV.some(function (e) { return e.event_type === "red_card" && e.player_id === pid && e.id !== exceptId; }); }
function onPitch(k, exceptEv) { return lineup(k).filter(function (p) { return !redOut(p.id, exceptEv); }); }
function items() {   // goals carry their assist; assists/POTM are not listed on their own
  var assists = EV.filter(function (e) { return e.event_type === "assist"; }), used = {}, out = [];
  EV.forEach(function (e) {
    if (e.event_type === "assist" || e.event_type === "player_of_match" || e.event_type === "player_of_tournament") return;
    var it = { e: e, assist: null };
    if (e.event_type === "goal") {
      var a = assists.filter(function (x) { return !used[x.id] && x.team_id === e.team_id && x.related_player_id === e.player_id && x.half === e.half && x.time_remaining === e.time_remaining; })[0];
      if (a) { used[a.id] = 1; it.assist = a; }
    }
    out.push(it);
  });
  return out;
}
function elOf(e) { return LIVE.elapsed(e.half, e.time_remaining == null ? LIVE.HALF : e.time_remaining); }
function sortedItems() { return items().sort(function (a, b) { return elOf(a.e) - elOf(b.e) || (a.e.created_at < b.e.created_at ? -1 : 1); }); }
function sc() { return LIVE.score(M, EV); }
function halfScore(h) { return LIVE.score(M, EV.filter(function (e) { return e.half === h; })); }

// ---------------------------------------------------------------- render
function teamNames() {
  var h = tname(M.home_team_id), a = tname(M.away_team_id);
  ["hn", "an"].forEach(function (id, i) { var e = document.getElementById(id); if (e) e.textContent = i ? a : h; });
  document.querySelectorAll(".hn").forEach(function (e) { e.textContent = h; }); document.querySelectorAll(".an").forEach(function (e) { e.textContent = a; });
  ["add-gH", "ht-gH"].forEach(function (id) { var e = document.getElementById(id); if (e) e.innerHTML = "⚽ Goal<br><small>" + esc(h) + "</small>"; });
  ["add-gA", "ht-gA"].forEach(function (id) { var e = document.getElementById(id); if (e) e.innerHTML = "⚽ Goal<br><small>" + esc(a) + "</small>"; });
}
function render() {
  if (!M) return;
  var ph = phase();
  $("#match-meta").textContent = "Kickoff " + (M.kickoff_at ? formatKickoff(M.kickoff_at) : "to be confirmed") + " · 2 × 10:00 halves";
  var idx = { pre: 0, h1: 1, ht: 2, h2: 3, ft: 4, final: 4 }[ph];
  ["s1", "s2", "s3", "s4", "s5"].forEach(function (s, i) { $("#" + s).className = i === idx ? "on" : (i < idx || ph === "final" ? "done" : ""); });
  var map = { pre: "p-pre", h1: "p-live", h2: "p-live", ht: "p-ht", ft: "p-ft", final: "p-final" };
  ["p-pre", "p-live", "p-ht", "p-ft", "p-final"].forEach(function (id) { show(id, id === map[ph]); });
  teamNames();
  renderLock();
  var s = sc();
  ["hs", "hth", "fh", "xh"].forEach(function (id) { var e = document.getElementById(id); if (e) e.textContent = id === "hth" ? halfScore(1).h : s.h; });
  ["as", "hta", "fa", "xa"].forEach(function (id) { var e = document.getElementById(id); if (e) e.textContent = id === "hta" ? halfScore(1).a : s.a; });
  if (ph === "pre") renderPre();
  if (ph === "h1" || ph === "h2") {
    $("#half-txt").textContent = LIVE.phaseText(M); $("#btn-pause").textContent = M.clock_running ? "⏸ Pause" : "▶ Resume"; show("lv", !!M.clock_running);
    $("#tl-live").innerHTML = timeline(true);
  }
  if (ph === "ht") $("#tl-ht").innerHTML = timeline(true);
  if (ph === "ft") { $("#tl-ft").innerHTML = timeline(true); renderFt(); }
  if (ph === "final") $("#tl-final").innerHTML = timeline(false);
  if (TAB === "audit") renderAudit();
  tick();
}
function tick() {
  if (!M) return; var ph = phase();
  if (ph === "h1" || ph === "h2") {
    var r = LIVE.remaining(M); var c = $("#clk"); c.textContent = LIVE.mmss(r); c.style.color = r <= 0 ? "var(--coral)" : "";
    $("#btn-endhalf").className = "lb" + (r <= 0 ? " pri" : "");
  }
}
function renderLock() {
  var li = lockInfo(), bar = $("#lockbar");
  if (M.status !== "scheduled") { bar.innerHTML = ""; return; }
  if (li.other) bar.innerHTML = '<div class="lock"><b>' + esc(li.other.label) + '</b> is running this match (active ' + li.age + 's ago). You can watch, but not edit. <button class="lb" style="margin-top:8px;width:100%;" data-act="takeover">Take over</button></div>';
  else if (li.mine && LOCK) bar.innerHTML = '<div class="muted" style="margin-bottom:8px;">✔ You are the active scorer for this match.</div>';
  else bar.innerHTML = "";
}
function timeline(editable) {
  var all = sortedItems(), run = {}, h = 0, a = 0;
  all.forEach(function (it) {
    var e = it.e;
    if (e.event_type === "goal" || e.event_type === "own_goal") {
      var home = (e.event_type === "goal") === (e.team_id === M.home_team_id);
      if (home) h++; else a++; run[e.id] = h + "–" + a;
    }
  });
  var ro = !!lockInfo().other;
  function row(it) {
    var e = it.e;
    var tm = LIVE.played(elOf(e));
    return '<div class="ev"><span class="m">' + tm + '<br><span class="pill h' + e.half + '">' + (e.half === 1 ? "1H" : "2H") + '</span></span><span class="dot" style="background:' + COLOR[e.event_type] + '"></span><div class="body">' + TYPE[e.event_type] +
      " · <b>" + esc(pname(e.player_id)) + "</b>" + (run[e.id] ? '<span class="sc">' + run[e.id] + "</span>" : "") + (e.is_penalty ? ' <span class="muted">(pen)</span>' : "") +
      (it.assist ? ' <span class="muted">(assist ' + esc(pname(it.assist.player_id)) + ")</span>" : "") + ' <span class="muted">· ' + esc(tname(e.team_id)) + " · " + LIVE.mmss(e.time_remaining == null ? LIVE.HALF : e.time_remaining) + " left</span></div>" +
      (editable && !ro ? '<button class="x" data-act="edit" data-id="' + e.id + '" title="Edit">✎</button><button class="x" data-act="rm" data-id="' + e.id + '" title="Remove">✕</button>' : "") + "</div>";
  }
  var out = "", curH = M.live_phase === "h2" || M.live_phase === "ft" || M.status !== "scheduled" ? 2 : 1;
  [2, 1].forEach(function (half) {
    var l = all.filter(function (it) { return it.e.half === half; }).reverse();
    if (!l.length && half > curH) return;
    var hs = halfScore(half);
    out += '<div class="hb h' + half + '">' + (half === 1 ? "FIRST HALF · 0:00 – 10:00" : "SECOND HALF · 10:00 – 20:00") + "<span>goals " + hs.h + "–" + hs.a + "</span></div>" +
      (l.length ? l.map(row).join("") : '<div class="muted" style="padding:6px 2px;">No events in this half yet.</div>');
    if (half === 2 && (curH === 2)) out += '<div class="htdiv">HALF-TIME ' + halfScore(1).h + "–" + halfScore(1).a + "</div>";
  });
  return out;
}

// ---- pre-match
function renderPre() {
  $("#toss-teams").innerHTML = ["H", "A"].map(function (k) { return '<button class="lb' + (M.toss_winner_team_id === sideId(k) ? " sel" : "") + '" data-act="toss" data-t="' + sideId(k) + '">' + esc(tname(sideId(k))) + "</button>"; }).join("");
  $("#toss-choice").innerHTML = [["side", "Side"], ["kickoff", "Kick-off"]].map(function (c) { return '<button class="lb' + (M.toss_choice === c[0] ? " sel" : "") + '" data-act="choice" data-c="' + c[0] + '">' + c[1] + "</button>"; }).join("");
  ["H", "A"].forEach(function (k) {
    var sq = squad(k), n = lineup(k).length, r = sq.filter(function (p) { return stOf(p.id) === "rested"; }).length, ab = sq.filter(function (p) { return stOf(p.id) === "absent"; }).length;
    var capId = (sq.filter(function (p) { return appOf(p.id) && appOf(p.id).is_captain; })[0] || {}).id || "";
    $("#ros-" + k).innerHTML = '<div class="t" style="margin-bottom:4px;">' + esc(tname(sideId(k))) + ' <span class="' + (n >= LIVE.MIN_PLAYERS ? "ok" : "bad") + '">· ' + n + " playing · " + r + " rested · " + ab + " absent</span></div>" +
      '<label>Captain</label><select data-act="cap" data-k="' + k + '"><option value="">— not recorded —</option>' + sq.filter(function (p) { return stOf(p.id) === "played"; }).map(function (p) { return '<option value="' + p.id + '"' + (capId === p.id ? " selected" : "") + ">" + esc(p.full_name) + "</option>"; }).join("") + "</select>" +
      (sq.length ? sq.map(function (p) {
        var st = stOf(p.id);
        return '<div class="pr ' + st + '"><span class="n">' + esc(p.full_name) + '</span><span class="seg">' +
          [["played", "Playing"], ["rested", "Rested"], ["absent", "Absent"]].map(function (s) { return '<button class="' + s[0] + (st === s[0] ? " on" : "") + '" data-act="st" data-p="' + p.id + '" data-k="' + k + '" data-s="' + s[0] + '">' + s[1] + "</button>"; }).join("") + "</span></div>" +
          (st !== "played" ? '<label style="display:flex;gap:6px;align-items:center;margin:0 0 4px;"><input type="checkbox" data-act="inj" data-p="' + p.id + '"' + (appOf(p.id) && appOf(p.id).absent_reason === "injury" ? " checked" : "") + ' style="width:auto;"> injury</label>' : "");
      }).join("") : '<p class="muted">No squad members for this team yet.</p>');
  });
  var c = checks();
  $("#pre-chk").innerHTML = c.map(function (x) { return '<li class="' + (x[0] ? "ok" : "warn") + '">' + (x[0] ? "✔" : "○") + " " + x[1] + "</li>"; }).join("");
  $("#btn-start").disabled = !c.every(function (x) { return x[0]; }) || !!lockInfo().other;
}
function checks() {
  var h = lineup("H").length, a = lineup("A").length;
  return [[!!M.toss_winner_team_id, "Toss winner recorded"], [!!M.toss_choice, "Toss choice recorded (side / kick-off)"],
    [h >= LIVE.MIN_PLAYERS, esc(tname(M.home_team_id)) + " has at least " + LIVE.MIN_PLAYERS + " players (" + h + ")"], [a >= LIVE.MIN_PLAYERS, esc(tname(M.away_team_id)) + " has at least " + LIVE.MIN_PLAYERS + " players (" + a + ")"]];
}
// ---- full time
function renderFt() {
  var list = [].concat(lineup("H"), lineup("A")), cur = (EV.filter(function (e) { return e.event_type === "player_of_match"; })[0] || {}).player_id || "";
  var keep = $("#potm").value || cur;
  $("#potm").innerHTML = '<option value="">— none —</option>' + list.map(function (p) { return '<option value="' + p.id + '"' + (keep === p.id ? " selected" : "") + ">" + esc(p.full_name) + "</option>"; }).join("");
  $("#ft-chk").innerHTML = '<li class="ok">✔ Scorers, assists, fouls, cards, rested and absent players are already saved from your timeline. Nothing to re-enter.</li>' +
    '<li class="ok">✔ The final score is worked out from the goals: ' + sc().h + "–" + sc().a + ".</li>";
}

// ---------------------------------------------------------------- write actions
async function run(fn) {
  if (BUSY) return false; BUSY = true;
  try {
    if (!(await ensureLock())) return false;
    var r = await fn();
    if (r && r.error) { toast(r.error.message || "Could not save", true); await loadAll(); render(); return false; }
    await loadAll(); render(); flash(); return true;
  } catch (e) { toast("Something went wrong: " + (e.message || e), true); return false; }
  finally { BUSY = false; }
}
function flash() { var s = $("#sync"); if (s) { s.innerHTML = '<span class="ok">● Saved · visitors see it now</span>'; } }
async function note(text) {
  return window.sb.from("audit_log").insert({ table_name: "live_note", record_id: M.id, action: "NOTE", new_data: { match_id: M.id, note: text } });
}
function setMatch(patch) { return window.sb.from("matches").update(patch).eq("id", M.id); }

async function doStatus(pid, k, st) {
  if (phase() !== "pre") return;
  return run(function () {
    var cur = appOf(pid);
    if (!cur && st === "played") return null;
    return window.sb.from("match_appearances").upsert({ match_id: M.id, player_id: pid, team_id: sideId(k), status: st, started: st === "played", absent_reason: st === "played" ? null : (cur && cur.absent_reason) || null, is_captain: st === "played" && cur ? !!cur.is_captain : false }, { onConflict: "match_id,player_id" });
  });
}
async function doCaptain(k, pid) {
  return run(async function () {
    var c = await window.sb.from("match_appearances").update({ is_captain: false }).eq("match_id", M.id).eq("team_id", sideId(k));
    if (c.error) return c;
    if (!pid) return null;
    var cur = appOf(pid);
    return window.sb.from("match_appearances").upsert({ match_id: M.id, player_id: pid, team_id: sideId(k), status: "played", started: true, is_captain: true }, { onConflict: "match_id,player_id" });
  });
}
async function doInjury(pid, on) {
  var cur = appOf(pid); if (!cur) return;
  return run(function () { return window.sb.from("match_appearances").update({ absent_reason: on ? "injury" : null }).eq("match_id", M.id).eq("player_id", pid); });
}
async function doStart() {
  var c = checks(); if (!c.every(function (x) { return x[0]; })) { toast("Finish the checklist first", true); return; }
  if (!confirm("Start the first half now? The lineup, toss and rested/absent players lock at kick-off.")) return;
  return run(function () { return setMatch({ live_phase: "h1", clock_rem: LIVE.HALF, clock_running: true }); });
}
async function doPause() {
  return run(function () { return M.clock_running ? setMatch({ clock_rem: Math.round(LIVE.remaining(M)), clock_running: false }) : setMatch({ clock_running: true }); });
}
async function doEndHalf() {
  var r = Math.round(LIVE.remaining(M)), h1 = M.live_phase === "h1";
  if (r > 5 && !confirm("The clock still shows " + LIVE.mmss(r) + ". End the " + (h1 ? "first" : "second") + " half anyway?")) return;
  return run(async function () {
    if (r > 0) { var n = await note((h1 ? "First" : "Second") + " half ended early with " + LIVE.mmss(r) + " left"); if (n.error) return n; }
    return setMatch({ live_phase: h1 ? "ht" : "ft", clock_rem: 0, clock_running: false });
  });
}
async function doStart2() { return run(function () { return setMatch({ live_phase: "h2", clock_rem: LIVE.HALF, clock_running: true }); }); }
async function doConfirm() {
  var msg = $("#ft-msg"); msg.textContent = "";
  var s = sc();
  if (!confirm("Confirm the final result " + tname(M.home_team_id) + " " + s.h + " – " + s.a + " " + tname(M.away_team_id) + "?\n\nStandings, Records and Form update immediately. Only an admin can change it afterwards.")) return;
  var pm = $("#potm").value;
  return run(async function () {
    var old = EV.filter(function (e) { return e.event_type === "player_of_match"; });
    for (var i = 0; i < old.length; i++) { var d = await window.sb.from("match_events").delete().eq("id", old[i].id); if (d.error) return d; }
    if (pm) {
      var team = ROST.H.some(function (p) { return p.id === pm; }) ? M.home_team_id : M.away_team_id;
      var ins = await window.sb.from("match_events").insert({ match_id: M.id, team_id: team, player_id: pm, event_type: "player_of_match", half: 2, minute: null });
      if (ins.error) return ins;
    }
    var fin = await setMatch({ status: "completed", live_phase: null, clock_running: false, home_score: s.h, away_score: s.a });
    if (fin.error) return fin;
    await window.sb.from("live_locks").delete().eq("match_id", M.id);
    return null;
  });
}

// ---------------------------------------------------------------- event sheet
function closeSheet() { DRAFT = null; show("sheet", false); $("#sheet").innerHTML = ""; }
function openAdd(type, side) {
  if (lockInfo().other) { toast("Someone else is running this match. Tap “Take over” first.", true); return; }
  var ph = phase(), half = ph === "h2" || ph === "ft" ? 2 : 1, live = ph === "h1" || ph === "h2";
  DRAFT = { id: null, type: type, team: side === "?" ? null : sideId(side), og: false, player: null, assist: null, pen: false, half: half, rem: live ? LIVE.mmss(Math.round(LIVE.remaining(M))) : "" };
  sheet();
}
function openEdit(id) {
  var it = items().filter(function (x) { return x.e.id === id; })[0]; if (!it) return;
  var e = it.e, og = e.event_type === "own_goal";
  DRAFT = { id: id, type: og ? "goal" : e.event_type, og: og, team: og ? otherTeam(e.team_id) : e.team_id, player: e.player_id, assist: it.assist ? it.assist.player_id : "", pen: !!e.is_penalty, half: e.half, rem: LIVE.mmss(e.time_remaining == null ? 0 : e.time_remaining), orig: it };
  sheet();
}
function allowedHalves() { var ph = phase(); return ph === "h1" || ph === "ht" ? [1] : [1, 2]; }
function kType(d) { return d.type === "goal" && d.og ? "own_goal" : d.type; }
function sheet() {
  var d = DRAFT, sh = $("#sheet"); show("sheet", true);
  var title = (d.id ? "Edit · " : "") + (TYPE[d.type] || d.type);
  if (!d.team) {
    sh.innerHTML = '<div class="t">' + title + ' · which team?</div><div class="lrow">' + ["H", "A"].map(function (k) { return '<button class="lb" data-s-team="' + sideId(k) + '">' + esc(tname(sideId(k))) + "</button>"; }).join("") + '</div><button class="lb ghost" style="width:100%;margin-top:8px;" data-s-cancel>Cancel</button>';
    return;
  }
  var tid = d.type === "goal" && d.og ? otherTeam(d.team) : d.team, k = tid === M.home_team_id ? "H" : "A";
  var exceptEv = d.orig ? d.orig.e.id : null;
  var pls = onPitch(k, exceptEv); if (d.player && !pls.some(function (p) { return p.id === d.player; }) && PLAYER[d.player] && (k === "H" ? ROST.H : ROST.A).some(function (p) { return p.id === d.player; })) pls = pls.concat([PLAYER[d.player]]);
  var assists = onPitch(d.team === M.home_team_id ? "H" : "A", null).filter(function (p) { return p.id !== d.player; });
  var halves = allowedHalves();
  sh.innerHTML = '<div class="t">' + title + " · " + esc(tname(d.team)) + (d.half ? " · " + (d.half === 1 ? "1st" : "2nd") + " half" : "") + "</div>" +
    (d.type === "goal" ? '<label style="display:flex;gap:8px;align-items:center;margin:0 0 6px;"><input type="checkbox" data-s-og style="width:auto;"' + (d.og ? " checked" : "") + "> Own goal (a " + esc(tname(otherTeam(d.team))) + " player put it in his own net, counts for " + esc(tname(d.team)) + ")</label>" +
      (d.og ? "" : '<label style="display:flex;gap:8px;align-items:center;margin:0 0 6px;"><input type="checkbox" data-s-pen style="width:auto;"' + (d.pen ? " checked" : "") + "> Penalty</label>") : "") +
    "<label>" + (d.og ? "Player who scored the own goal" : d.type === "goal" ? "Scorer" : "Player") + '</label><div class="pl">' + pls.map(function (p) { return '<button class="lb' + (d.player === p.id ? " sel" : "") + '" data-s-player="' + p.id + '">' + esc(p.full_name) + "</button>"; }).join("") + "</div>" +
    (d.type === "goal" && !d.og && d.player ? '<label>Assist (same team)</label><div class="pl">' + assists.map(function (p) { return '<button class="lb' + (d.assist === p.id ? " sel" : "") + '" data-s-assist="' + p.id + '">' + esc(p.full_name) + "</button>"; }).join("") + '<button class="lb ghost' + (d.assist === "" ? " sel" : "") + '" data-s-assist="">No assist</button></div>' : "") +
    (halves.length > 1 ? '<label>Half</label><div class="lrow">' + halves.map(function (h) { return '<button class="lb' + (d.half === h ? " sel" : "") + '" data-s-half="' + h + '">' + (h === 1 ? "1st half" : "2nd half") + "</button>"; }).join("") + "</div>" : "") +
    "<label>Time remaining in that half (mm:ss), filled in from the clock. Change it if you are entering late.</label>" +
    '<div class="lrow"><button class="lb" data-s-nudge="-10">−10s</button><input type="text" id="s-rt" inputmode="numeric" value="' + esc(d.rem) + '" style="text-align:center;font-size:20px;" placeholder="mm:ss"><button class="lb" data-s-nudge="10">+10s</button></div>' +
    '<div class="muted" id="s-conv" style="margin-top:4px;"></div>' +
    '<div class="lrow" style="margin-top:10px;"><button class="lb ghost" data-s-cancel>Cancel</button><button class="lb pri" data-s-save id="s-save">' + (d.id ? "Save change" : "Save event") + '</button></div><div id="s-err" class="bad" style="margin-top:6px;"></div>';
  convPreview();
}
function convPreview() {
  var d = DRAFT, c = $("#s-conv"); if (!c) return;
  var r = LIVE.parseRem($("#s-rt").value);
  if (r == null) { c.innerHTML = '<span class="bad">Enter the time left as mm:ss, between 00:00 and 10:00 (each half is 10 minutes).</span>'; return; }
  var e = LIVE.elapsed(d.half, r);
  c.innerHTML = "Visitors will see <b>" + (d.half === 1 ? "1st half" : "2nd half") + " · " + LIVE.played(e) + "</b> played" + (d.half === 2 ? " (10:00 + " + LIVE.played(LIVE.HALF - r) + ")" : "");
}
async function saveDraft() {
  var d = DRAFT, err = $("#s-err"); err.textContent = "";
  var r = LIVE.parseRem($("#s-rt").value);
  if (r == null) { err.textContent = "Fix the time first. Nothing was saved."; return; }
  d.rem = $("#s-rt").value;
  if (!d.player) { err.textContent = "Pick the player first."; return; }
  if (d.type === "goal" && !d.og && d.assist == null) { err.textContent = "Pick an assist, or “No assist”."; return; }
  var ph = phase(), curHalf = ph === "h1" ? 1 : ph === "h2" ? 2 : 0;
  if (curHalf && d.half === curHalf && (ph === "h1" || ph === "h2") && r < LIVE.remaining(M) - 3) { err.textContent = "That time has not happened yet: the clock shows " + LIVE.mmss(LIVE.remaining(M)) + " left."; return; }
  if (d.half === 2 && (ph === "h1" || ph === "ht")) { err.textContent = "The second half has not started."; return; }
  var type = kType(d), teamId = type === "own_goal" ? otherTeam(d.team) : d.team, el = LIVE.elapsed(d.half, r);
  var dup = items().some(function (it) { return (!d.orig || it.e.id !== d.orig.e.id) && it.e.event_type === type && it.e.team_id === teamId && it.e.player_id === d.player && it.e.half === d.half && it.e.time_remaining === r; });
  if (dup && !confirm("An identical event is already in the timeline. Add it again?")) return;
  var base = { match_id: M.id, half: d.half, time_remaining: r, minute: Math.floor(el / 60), second: el % 60 };
  var late = curHalf && d.half < curHalf || ph === "ft" && d.half === 1;
  var btn = $("#s-save"); btn.disabled = true;
  var ok = await run(async function () {
    var assistId = type === "goal" && d.assist ? d.assist : null;
    if (!d.id) {
      var rows = [Object.assign({}, base, { event_type: type, team_id: teamId, player_id: d.player, related_player_id: assistId, is_penalty: type === "goal" && !!d.pen })];
      if (assistId) rows.push(Object.assign({}, base, { event_type: "assist", team_id: teamId, player_id: assistId, related_player_id: d.player }));
      // a second yellow card to the same player in this match also gives him a red card automatically
      var autoRed = type === "yellow_card" && items().some(function (it) { return it.e.event_type === "yellow_card" && it.e.player_id === d.player; }) &&
        !items().some(function (it) { return it.e.event_type === "red_card" && it.e.player_id === d.player; });
      if (autoRed) rows.push(Object.assign({}, base, { event_type: "red_card", team_id: teamId, player_id: d.player, related_player_id: null }));
      var ins = await window.sb.from("match_events").insert(rows); if (ins.error) return ins;
      if (autoRed) { var nr = await note("Automatic red card: second yellow card for " + pname(d.player)); if (nr.error) return nr; }
      if (late) { var n = await note("Late entry: " + TYPE[type] + " · " + pname(d.player) + " added to the " + (d.half === 1 ? "first" : "second") + " half after it ended"); if (n.error) return n; }
      return null;
    }
    var o = d.orig, upd = await window.sb.from("match_events").update(Object.assign({}, base, { event_type: type, team_id: teamId, player_id: d.player, related_player_id: assistId, is_penalty: type === "goal" && !!d.pen })).eq("id", o.e.id);
    if (upd.error) return upd;
    if (o.assist) {
      if (assistId) { var u2 = await window.sb.from("match_events").update(Object.assign({}, base, { team_id: teamId, player_id: assistId, related_player_id: d.player })).eq("id", o.assist.id); if (u2.error) return u2; }
      else { var d2 = await window.sb.from("match_events").delete().eq("id", o.assist.id); if (d2.error) return d2; }
    } else if (assistId) {
      var i2 = await window.sb.from("match_events").insert(Object.assign({}, base, { event_type: "assist", team_id: teamId, player_id: assistId, related_player_id: d.player })); if (i2.error) return i2;
    }
    return null;
  });
  if (ok) closeSheet(); else if (btn) btn.disabled = false;
}
async function removeEvent(id) {
  if (lockInfo().other) { toast("Someone else is running this match.", true); return; }
  var it = items().filter(function (x) { return x.e.id === id; })[0]; if (!it) return;
  var why = prompt("Why are you removing this " + TYPE[it.e.event_type] + " (" + pname(it.e.player_id) + ")?\nA reason is required and is kept in the audit trail.");
  if (!why || !why.trim()) { toast("Nothing was removed: a reason is required.", true); return; }
  return run(async function () {
    var n = await note("REMOVED " + TYPE[it.e.event_type] + " · " + pname(it.e.player_id) + " (" + tname(it.e.team_id) + ") " + (it.e.half === 1 ? "1st" : "2nd") + " half, " + LIVE.mmss(it.e.time_remaining || 0) + " left. Reason: " + why.trim());
    if (n.error) return n;
    if (it.assist) { var a = await window.sb.from("match_events").delete().eq("id", it.assist.id); if (a.error) return a; }
    return window.sb.from("match_events").delete().eq("id", id);
  });
}

// ---------------------------------------------------------------- audit trail
async function loadAudit() {
  var since = new Date(Date.parse(M.kickoff_at || new Date()) - 36 * 3600 * 1000).toISOString();
  var r = await window.sb.from("audit_log").select("*").in("table_name", ["matches", "match_events", "match_appearances", "live_note"]).gte("changed_at", since).order("changed_at", { ascending: false }).limit(1000);
  AUD = (r.data || []).filter(function (a) {
    var d = a.new_data || a.old_data || {};
    return a.table_name === "matches" || a.table_name === "live_note" ? (a.record_id === M.id) : d.match_id === M.id;
  });
}
function auditText(a) {
  var n = a.new_data || {}, o = a.old_data || {}, d = a.new_data || a.old_data || {};
  if (a.table_name === "live_note") return "NOTE: " + esc(n.note || "");
  if (a.table_name === "match_events") {
    var who = pname(d.player_id) + " (" + tname(d.team_id) + ")", t = TYPE[d.event_type] || d.event_type;
    var tm = (d.half === 1 ? "1st" : d.half === 2 ? "2nd" : "?") + " half, " + (d.time_remaining == null ? "?" : LIVE.mmss(d.time_remaining)) + " left";
    if (a.action === "INSERT") return "ADDED " + esc(t) + " · " + esc(who) + " · " + tm;
    if (a.action === "DELETE") return "REMOVED " + esc(t) + " · " + esc(who) + " · " + tm;
    var ob = (TYPE[o.event_type] || o.event_type) + " " + pname(o.player_id) + " " + (o.time_remaining == null ? "?" : LIVE.mmss(o.time_remaining)) + " left";
    return "EDITED " + esc(ob) + " → " + esc(t + " " + pname(d.player_id) + " " + (d.time_remaining == null ? "?" : LIVE.mmss(d.time_remaining)) + " left");
  }
  if (a.table_name === "match_appearances") {
    var p = pname(d.player_id) + " (" + tname(d.team_id) + ")";
    if (a.action === "DELETE") return esc(p) + " lineup entry removed";
    var bits = []; if (!o.status || o.status !== n.status) bits.push("set to " + (n.status === "played" ? "playing" : n.status));
    if (!!o.is_captain !== !!n.is_captain) bits.push(n.is_captain ? "made captain" : "no longer captain");
    if ((o.absent_reason || null) !== (n.absent_reason || null)) bits.push(n.absent_reason ? "marked injury" : "injury cleared");
    return esc(p) + " " + (bits.join(", ") || "updated");
  }
  if (a.table_name === "matches") {
    var m = [];
    if (o.toss_winner_team_id !== n.toss_winner_team_id) m.push("Toss won by " + esc(tname(n.toss_winner_team_id)));
    if (o.toss_choice !== n.toss_choice) m.push("Toss winner chose " + (n.toss_choice === "kickoff" ? "kick-off" : "side"));
    if (o.live_phase !== n.live_phase) m.push(n.live_phase === "h1" ? "FIRST HALF started" : n.live_phase === "ht" ? "HALF-TIME" : n.live_phase === "h2" ? "SECOND HALF started" : n.live_phase === "ft" ? "FULL TIME" : "");
    else if (o.clock_running !== n.clock_running) m.push(n.clock_running ? "Clock resumed at " + LIVE.mmss(n.clock_rem) : "Clock paused at " + LIVE.mmss(n.clock_rem));
    if (o.status !== n.status && n.status === "completed") m.push("RESULT CONFIRMED " + n.home_score + "–" + n.away_score + " (match marked completed)");
    return m.filter(Boolean).join(" · ") || "Match updated";
  }
  return esc(a.table_name + " " + a.action);
}
function renderAudit() {
  $("#audit-body").innerHTML = AUD.length ? AUD.map(function (a) { return "<tr><td>" + esc(etStr(a.changed_at)) + "</td><td>" + esc(a.changed_by_label || "Admin") + "</td><td>" + auditText(a) + "</td></tr>"; }).join("") : '<tr><td colspan="3" class="muted">Nothing recorded for this match yet.</td></tr>';
}
function setTab(t) { TAB = t; show("pane-desk", t === "desk"); show("pane-audit", t === "audit"); $("#t-desk").className = t === "desk" ? "on" : ""; $("#t-audit").className = t === "audit" ? "on" : ""; if (t === "audit") loadAudit().then(renderAudit); }
$("#t-desk").onclick = function () { setTab("desk"); }; $("#t-audit").onclick = function () { setTab("audit"); };

// ---------------------------------------------------------------- clicks
document.addEventListener("click", function (ev) {
  var el = ev.target.closest("[data-act],[data-add],[data-s-team],[data-s-cancel],[data-s-player],[data-s-assist],[data-s-half],[data-s-nudge],[data-s-save]"); if (!el) return;
  var ds = el.dataset;
  if (ds.add !== undefined) { var p = ds.add.split("|"); openAdd(p[0], p[1]); return; }
  if (ds.sTeam) { DRAFT.team = ds.sTeam; sheet(); return; }
  if (ds.sCancel !== undefined) { closeSheet(); return; }
  if (ds.sPlayer) { DRAFT.rem = $("#s-rt").value; DRAFT.player = ds.sPlayer; if (DRAFT.assist === ds.sPlayer) DRAFT.assist = null; sheet(); return; }
  if (ds.sAssist !== undefined) { DRAFT.rem = $("#s-rt").value; DRAFT.assist = ds.sAssist; sheet(); return; }
  if (ds.sHalf) { DRAFT.rem = $("#s-rt").value; DRAFT.half = +ds.sHalf; sheet(); return; }
  if (ds.sNudge) { var inp = $("#s-rt"), cur = LIVE.parseRem(inp.value); cur = cur == null ? Math.round(LIVE.remaining(M)) : cur; inp.value = LIVE.mmss(Math.max(0, Math.min(LIVE.HALF, cur + +ds.sNudge))); convPreview(); return; }
  if (ds.sSave !== undefined) { saveDraft(); return; }
  switch (ds.act) {
    case "takeover": claimLock().then(function (ok) { if (ok) { toast("You are now the active scorer"); render(); } }); break;
    case "toss": run(function () { return setMatch({ toss_winner_team_id: ds.t }); }); break;
    case "choice": run(function () { return setMatch({ toss_choice: ds.c }); }); break;
    case "st": doStatus(ds.p, ds.k, ds.s); break;
    case "edit": openEdit(ds.id); break;
    case "rm": removeEvent(ds.id); break;
  }
});
document.addEventListener("change", function (ev) {
  var t = ev.target;
  if (t.dataset && t.dataset.act === "cap") doCaptain(t.dataset.k, t.value);
  else if (t.dataset && t.dataset.act === "inj") doInjury(t.dataset.p, t.checked);
  else if (t.dataset && t.dataset.sOg !== undefined) { DRAFT.rem = $("#s-rt").value; DRAFT.og = t.checked; DRAFT.player = null; DRAFT.assist = null; sheet(); }
  else if (t.dataset && t.dataset.sPen !== undefined) { DRAFT.pen = t.checked; }
});
document.addEventListener("input", function (ev) { if (ev.target.id === "s-rt") convPreview(); });
$("#btn-start").onclick = doStart; $("#btn-pause").onclick = doPause; $("#btn-endhalf").onclick = doEndHalf; $("#btn-start2").onclick = doStart2; $("#btn-confirm").onclick = doConfirm;

boot();
