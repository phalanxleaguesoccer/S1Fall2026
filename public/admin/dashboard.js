window.IN_ADMIN_DIR = true;
var CURRENT_SEASON = null;
var ALL_SEASONS = [];
var TEAMS_CACHE = [];
var PLAYERS_CACHE = [];

// ---------- Auth guard ----------
(async function guard() {
  var sessionRes = await window.sb.auth.getSession();
  if (!sessionRes.data.session) { window.location.href = "login.html"; return; }
  var adminRes = await window.sb.from("admins").select("*").eq("user_id", sessionRes.data.session.user.id).maybeSingle();
  if (!adminRes.data) { await window.sb.auth.signOut(); window.location.href = "login.html"; return; }
  document.getElementById("whoami").textContent = "Logged in as " + (adminRes.data.display_name || sessionRes.data.session.user.email);
  init();
})();

document.getElementById("logout-btn").addEventListener("click", async function () {
  await window.sb.auth.signOut();
  window.location.href = "login.html";
});

// ---------- Tabs ----------
document.querySelectorAll(".tabs button").forEach(function (btn) {
  btn.addEventListener("click", function () {
    document.querySelectorAll(".tabs button").forEach(function (b) { b.classList.remove("active"); });
    document.querySelectorAll(".tab-panel").forEach(function (p) { p.classList.remove("active"); });
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

async function init() {
  CURRENT_SEASON = await getCurrentSeason();
  if (!CURRENT_SEASON) {
    alert("No current season found. Run the schema.sql seed, or add one in Supabase directly.");
    return;
  }
  var seasonsRes = await window.sb.from("seasons").select("*").order("created_at", { ascending: true });
  ALL_SEASONS = seasonsRes.data || [];
  var rSeasonSel = document.getElementById("r-season");
  rSeasonSel.innerHTML = ALL_SEASONS.map(function (s) { return '<option value="' + s.id + '">' + escapeHtml(s.name) + "</option>"; }).join("");
  rSeasonSel.value = CURRENT_SEASON.id;
  rSeasonSel.addEventListener("change", refreshRosters);

  await refreshTeams();
  await refreshPlayers();
  await refreshRosters();
  await refreshMatches();
  populateEventMatchDropdown();

  document.getElementById("team-form").addEventListener("submit", onAddTeam);
  document.getElementById("player-form").addEventListener("submit", onAddPlayer);
  document.getElementById("roster-form").addEventListener("submit", onAssignRoster);
  document.getElementById("match-form").addEventListener("submit", onAddMatch);
  document.getElementById("event-form").addEventListener("submit", onLogEvent);
  document.getElementById("e-match").addEventListener("change", loadEventsForSelectedMatch);
}

// ---------- TEAMS ----------
async function refreshTeams() {
  var res = await window.sb.from("teams").select("*").order("name");
  TEAMS_CACHE = res.data || [];
  document.getElementById("teams-list").innerHTML = TEAMS_CACHE.length
    ? TEAMS_CACHE.map(function (t) { return '<div class="list-row"><span>' + escapeHtml(t.name) + "</span></div>"; }).join("")
    : '<p class="muted">No teams yet.</p>';

  // m-home/m-away/e-team are tied to actual scheduled matches, which still
  // reference the generic Team A/B/C/D slots until the draw happens — those
  // dropdowns need every team, placeholders included.
  ["m-home", "m-away", "e-team"].forEach(function (id) {
    var sel = document.getElementById(id);
    var prev = sel.value;
    sel.innerHTML = '<option value="">— select —</option>' + TEAMS_CACHE.map(function (t) {
      return '<option value="' + t.id + '">' + escapeHtml(t.name) + "</option>";
    }).join("");
    sel.value = prev;
  });

  // r-team (roster/squad assignment) is about building squads for the real,
  // finalized teams — so it only lists those (not the generic Team A/B/C/D
  // schedule placeholders), plus "Unassigned" to take a player off a roster.
  var finalizedTeams = TEAMS_CACHE.filter(function (t) { return !/^Team [A-Z]$/.test(t.name); });
  var rTeamSel = document.getElementById("r-team");
  var rTeamPrev = rTeamSel.value;
  rTeamSel.innerHTML = '<option value="">— select —</option>' +
    '<option value="unassigned">Unassigned (remove from roster)</option>' +
    finalizedTeams.map(function (t) { return '<option value="' + t.id + '">' + escapeHtml(t.name) + "</option>"; }).join("");
  rTeamSel.value = rTeamPrev;
}

async function onAddTeam(e) {
  e.preventDefault();
  var name = document.getElementById("team-name-input").value.trim();
  var crest = document.getElementById("team-crest-input").value.trim();
  var msg = document.getElementById("team-msg");
  var res = await window.sb.from("teams").insert({ name: name, crest_url: crest || null });
  if (res.error) { showError(msg, res.error.message); return; }
  showSuccess(msg, "Team added.");
  document.getElementById("team-form").reset();
  await refreshTeams();
}

// ---------- PLAYERS ----------
async function refreshPlayers() {
  var res = await window.sb.from("players").select("*").order("full_name");
  PLAYERS_CACHE = res.data || [];
  document.getElementById("players-list").innerHTML = PLAYERS_CACHE.length
    ? PLAYERS_CACHE.map(function (p) { return '<div class="list-row"><span>' + escapeHtml(p.full_name) + '</span><span class="muted">' + escapeHtml(p.preferred_position || "") + "</span></div>"; }).join("")
    : '<p class="muted">No players yet.</p>';

  ["r-player", "e-player"].forEach(function (id) {
    var sel = document.getElementById(id);
    var prev = sel.value;
    sel.innerHTML = '<option value="">— select —</option>' + PLAYERS_CACHE.map(function (p) {
      return '<option value="' + p.id + '">' + escapeHtml(p.full_name) + "</option>";
    }).join("");
    sel.value = prev;
  });
}

async function onAddPlayer(e) {
  e.preventDefault();
  var msg = document.getElementById("player-msg");
  var payload = {
    full_name: document.getElementById("p-name").value.trim(),
    age: document.getElementById("p-age").value || null,
    preferred_position: document.getElementById("p-position").value.trim() || null,
    preferred_foot: document.getElementById("p-foot").value || null,
    position_category: document.getElementById("p-position-category").value || null,
    jersey_size: document.getElementById("p-jersey-size").value.trim() || null,
    photo_url: document.getElementById("p-photo").value.trim() || null,
    fun_fact: document.getElementById("p-fact").value.trim() || null,
    stamina_level: document.getElementById("p-stamina").value || null,
    skill_rating: document.getElementById("p-skill-rating").value || null,
    skill_level: document.getElementById("p-skill-level").value || null,
    playing_experience: document.getElementById("p-experience").value.trim() || null,
    fitness_notes: document.getElementById("p-fitness").value.trim() || null,
    leave_plan: document.getElementById("p-leave").value.trim() || null
  };
  var res = await window.sb.from("players").insert(payload);
  if (res.error) { showError(msg, res.error.message); return; }
  showSuccess(msg, "Player added.");
  document.getElementById("player-form").reset();
  await refreshPlayers();
}

// ---------- ROSTERS ----------
async function refreshRosters() {
  var seasonId = document.getElementById("r-season").value || CURRENT_SEASON.id;
  var res = await window.sb.from("team_season_rosters").select("*, players(*), teams(*)").eq("season_id", seasonId);
  var list = document.getElementById("rosters-list");
  if (!res.data || res.data.length === 0) { list.innerHTML = '<p class="muted">No rosters set yet.</p>'; return; }
  list.innerHTML = res.data.map(function (r) {
    return '<div class="list-row"><span>' + escapeHtml(r.players.full_name) + " &rarr; " + escapeHtml(r.teams.name) +
      (r.jersey_number ? " (#" + r.jersey_number + ")" : "") + (r.is_owner ? ' <span class="pill completed">Owner</span>' : "") + "</span></div>";
  }).join("");
}

async function onAssignRoster(e) {
  e.preventDefault();
  var msg = document.getElementById("roster-msg");
  var seasonId = document.getElementById("r-season").value;
  var playerId = document.getElementById("r-player").value;
  var teamChoice = document.getElementById("r-team").value;
  if (!seasonId || !playerId || !teamChoice) { showError(msg, "Pick a season, player, and team."); return; }

  if (teamChoice === "unassigned") {
    var delRes = await window.sb.from("team_season_rosters").delete().eq("season_id", seasonId).eq("player_id", playerId);
    if (delRes.error) { showError(msg, delRes.error.message); return; }
    showSuccess(msg, "Removed from roster for that season.");
    document.getElementById("roster-form").reset();
    document.getElementById("r-season").value = seasonId;
    await refreshRosters();
    return;
  }

  var payload = {
    season_id: seasonId,
    player_id: playerId,
    team_id: teamChoice,
    jersey_number: document.getElementById("r-jersey").value || null,
    auction_price: document.getElementById("r-price").value || null,
    is_owner: document.getElementById("r-owner").checked
  };
  var res = await window.sb.from("team_season_rosters").upsert(payload, { onConflict: "season_id,player_id" });
  if (res.error) { showError(msg, res.error.message); return; }
  showSuccess(msg, "Roster updated.");
  document.getElementById("roster-form").reset();
  document.getElementById("r-season").value = seasonId;
  await refreshRosters();
}

// ---------- MATCHES ----------
async function refreshMatches() {
  var res = await window.sb.from("matches").select("*").eq("season_id", CURRENT_SEASON.id).order("match_day").order("match_number");
  var teamsById = {};
  TEAMS_CACHE.forEach(function (t) { teamsById[t.id] = t; });
  var list = document.getElementById("matches-list");
  if (!res.data || res.data.length === 0) { list.innerHTML = '<p class="muted">No matches yet.</p>'; return; }

  list.innerHTML = res.data.map(function (m) {
    var home = teamsById[m.home_team_id] ? teamsById[m.home_team_id].name : "?";
    var away = teamsById[m.away_team_id] ? teamsById[m.away_team_id].name : "?";
    return '<div class="card" style="margin-bottom:10px;">' +
      "<strong>Day " + m.match_day + " Match " + m.match_number + "</strong> — " + escapeHtml(home) + " vs " + escapeHtml(away) +
      ' <span class="pill ' + m.status + '">' + m.status + "</span>" +
      '<form class="mt-16 result-form" data-match-id="' + m.id + '">' +
      '<div class="row">' +
      '<div><label>Status</label><select name="status">' +
        ["scheduled", "completed", "forfeited", "postponed"].map(function (s) {
          return '<option value="' + s + '"' + (m.status === s ? " selected" : "") + ">" + s + "</option>";
        }).join("") +
      "</select></div>" +
      '<div><label>' + escapeHtml(home) + ' score</label><input type="number" name="home_score" value="' + (m.home_score ?? "") + '" min="0"></div>' +
      '<div><label>' + escapeHtml(away) + ' score</label><input type="number" name="away_score" value="' + (m.away_score ?? "") + '" min="0"></div>' +
      "</div>" +
      '<button class="btn secondary mt-16" type="submit">Save Result</button>' +
      "</form></div>";
  }).join("");

  document.querySelectorAll(".result-form").forEach(function (f) {
    f.addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var matchId = f.dataset.matchId;
      var status = f.status.value;
      var payload = { status: status };
      if (status === "completed") {
        payload.home_score = f.home_score.value === "" ? null : parseInt(f.home_score.value, 10);
        payload.away_score = f.away_score.value === "" ? null : parseInt(f.away_score.value, 10);
      } else if (status === "forfeited") {
        payload.home_score = null;
        payload.away_score = null;
      }
      var res = await window.sb.from("matches").update(payload).eq("id", matchId);
      if (res.error) { alert(res.error.message); return; }
      await refreshMatches();
      populateEventMatchDropdown();
    });
  });
}

async function onAddMatch(e) {
  e.preventDefault();
  var msg = document.getElementById("match-msg");
  var kickoff = document.getElementById("m-kickoff").value;
  var payload = {
    season_id: CURRENT_SEASON.id,
    match_day: parseInt(document.getElementById("m-day").value, 10),
    match_number: parseInt(document.getElementById("m-number").value, 10),
    home_team_id: document.getElementById("m-home").value,
    away_team_id: document.getElementById("m-away").value,
    kickoff_at: kickoff ? new Date(kickoff).toISOString() : null
  };
  if (!payload.home_team_id || !payload.away_team_id) { showError(msg, "Pick both teams."); return; }
  if (payload.home_team_id === payload.away_team_id) { showError(msg, "Home and away team must differ."); return; }
  var res = await window.sb.from("matches").insert(payload);
  if (res.error) { showError(msg, res.error.message); return; }
  showSuccess(msg, "Match added.");
  document.getElementById("match-form").reset();
  await refreshMatches();
  populateEventMatchDropdown();
}

// ---------- EVENTS ----------
async function populateEventMatchDropdown() {
  var res = await window.sb.from("matches").select("*").eq("season_id", CURRENT_SEASON.id).order("match_day").order("match_number");
  var teamsById = {};
  TEAMS_CACHE.forEach(function (t) { teamsById[t.id] = t; });
  var sel = document.getElementById("e-match");
  sel.innerHTML = '<option value="">— select match —</option>' + (res.data || []).map(function (m) {
    var home = teamsById[m.home_team_id] ? teamsById[m.home_team_id].name : "?";
    var away = teamsById[m.away_team_id] ? teamsById[m.away_team_id].name : "?";
    return '<option value="' + m.id + '">Day ' + m.match_day + " M" + m.match_number + ": " + home + " vs " + away + "</option>";
  }).join("");
}

async function onLogEvent(e) {
  e.preventDefault();
  var msg = document.getElementById("event-msg");
  var payload = {
    match_id: document.getElementById("e-match").value,
    team_id: document.getElementById("e-team").value,
    player_id: document.getElementById("e-player").value,
    event_type: document.getElementById("e-type").value,
    half: parseInt(document.getElementById("e-half").value, 10),
    minute: document.getElementById("e-minute").value ? parseInt(document.getElementById("e-minute").value, 10) : null
  };
  if (!payload.match_id || !payload.team_id || !payload.player_id) { showError(msg, "Match, team, and player are all required."); return; }
  var res = await window.sb.from("match_events").insert(payload);
  if (res.error) { showError(msg, res.error.message); return; }
  showSuccess(msg, "Event logged.");
  loadEventsForSelectedMatch();
}

async function loadEventsForSelectedMatch() {
  var matchId = document.getElementById("e-match").value;
  var list = document.getElementById("events-list");
  if (!matchId) { list.innerHTML = '<p class="muted">Pick a match to see its events.</p>'; return; }
  var res = await window.sb.from("match_events").select("*, players(*)").eq("match_id", matchId).order("minute");
  if (!res.data || res.data.length === 0) { list.innerHTML = '<p class="muted">No events logged for this match yet.</p>'; return; }
  var typeLabel = { goal: "Goal", assist: "Assist", yellow_card: "Yellow", red_card: "Red", substitution_in: "Sub on", substitution_out: "Sub off", player_of_match: "Player of the Match", save: "Goal Saved", player_of_tournament: "Player of the Tournament" };
  list.innerHTML = res.data.map(function (ev) {
    return '<div class="list-row"><span>' + (typeLabel[ev.event_type] || ev.event_type) + " — " + escapeHtml(ev.players.full_name) +
      (ev.minute ? " (" + ev.minute + "')" : "") + "</span>" +
      '<button class="btn danger" data-event-id="' + ev.id + '" onclick="deleteEvent(this)">Delete</button></div>';
  }).join("");
}

async function deleteEvent(btn) {
  if (!confirm("Delete this event?")) return;
  await window.sb.from("match_events").delete().eq("id", btn.dataset.eventId);
  loadEventsForSelectedMatch();
}
