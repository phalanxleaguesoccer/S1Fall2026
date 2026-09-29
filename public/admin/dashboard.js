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
  initShootoutForm();
  document.getElementById("event-form").addEventListener("submit", onLogEvent);
  document.getElementById("e-match").addEventListener("change", loadEventsForSelectedMatch);

  // Records tab: season selects that don't need "All Seasons"
  ["rating-season", "susp-season", "award-season"].forEach(function (id) {
    var sel = document.getElementById(id);
    sel.innerHTML = ALL_SEASONS.map(function (s) { return '<option value="' + s.id + '">' + escapeHtml(s.name) + "</option>"; }).join("");
    sel.value = CURRENT_SEASON.id;
  });
  populateAppearanceMatchDropdown();
  document.getElementById("appearance-form").addEventListener("submit", onLogAppearance);
  document.getElementById("note-form").addEventListener("submit", onLogNote);
  document.getElementById("rating-form").addEventListener("submit", onLogRating);
  document.getElementById("suspension-form").addEventListener("submit", onLogSuspension);
  document.getElementById("award-form").addEventListener("submit", onLogAward);
}

// ---------- TEAMS ----------
async function refreshTeams() {
  var res = await window.sb.from("teams").select("*").order("name");
  TEAMS_CACHE = res.data || [];
  document.getElementById("teams-list").innerHTML = TEAMS_CACHE.length
    ? TEAMS_CACHE.map(function (t) {
        return '<div class="list-row"><span>' + escapeHtml(t.name) + (t.is_active === false ? ' <span class="pill">Archived</span>' : "") + "</span>" +
          '<button class="btn secondary" data-team-id="' + t.id + '" data-active="' + (t.is_active !== false) + '" onclick="toggleTeamActive(this)">' +
          (t.is_active === false ? "Reactivate" : "Archive") + "</button></div>";
      }).join("")
    : '<p class="muted">No teams yet.</p>';

  var awardTeamSel = document.getElementById("award-team");
  if (awardTeamSel) {
    var prevAwardTeam = awardTeamSel.value;
    awardTeamSel.innerHTML = '<option value="">—</option>' + TEAMS_CACHE.map(function (t) {
      return '<option value="' + t.id + '">' + escapeHtml(t.name) + "</option>";
    }).join("");
    awardTeamSel.value = prevAwardTeam;
  }

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

  // Match Appearance form's Team select mirrors m-home/m-away (every team,
  // since appearances are logged against the actual scheduled match).
  var apTeamSel = document.getElementById("ap-team");
  if (apTeamSel) {
    var apTeamPrev = apTeamSel.value;
    apTeamSel.innerHTML = '<option value="">— select —</option>' + TEAMS_CACHE.map(function (t) {
      return '<option value="' + t.id + '">' + escapeHtml(t.name) + "</option>";
    }).join("");
    apTeamSel.value = apTeamPrev;
  }
}

async function toggleTeamActive(btn) {
  var teamId = btn.dataset.teamId;
  var isActive = btn.dataset.active === "true";
  var res = await window.sb.from("teams").update({ is_active: !isActive }).eq("id", teamId);
  if (res.error) { alert(res.error.message); return; }
  await refreshTeams();
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
    ? PLAYERS_CACHE.map(function (p) {
        return '<div class="list-row"><span>' + escapeHtml(p.full_name) + (p.is_active === false ? ' <span class="pill">Archived</span>' : "") +
          '</span><span class="muted">' + escapeHtml(p.preferred_position || "") + "</span>" +
          '<button class="btn secondary" data-player-id="' + p.id + '" data-active="' + (p.is_active !== false) + '" onclick="togglePlayerActive(this)">' +
          (p.is_active === false ? "Reactivate" : "Archive") + "</button></div>";
      }).join("")
    : '<p class="muted">No players yet.</p>';

  ["r-player", "e-player", "ap-player", "note-player", "rating-player", "susp-player"].forEach(function (id) {
    var sel = document.getElementById(id);
    if (!sel) return;
    var prev = sel.value;
    sel.innerHTML = '<option value="">— select —</option>' + PLAYERS_CACHE.map(function (p) {
      return '<option value="' + p.id + '">' + escapeHtml(p.full_name) + "</option>";
    }).join("");
    sel.value = prev;
  });

  var awardPlayerSel = document.getElementById("award-player");
  if (awardPlayerSel) {
    var prevAwardPlayer = awardPlayerSel.value;
    awardPlayerSel.innerHTML = '<option value="">—</option>' + PLAYERS_CACHE.map(function (p) {
      return '<option value="' + p.id + '">' + escapeHtml(p.full_name) + "</option>";
    }).join("");
    awardPlayerSel.value = prevAwardPlayer;
  }
}

async function togglePlayerActive(btn) {
  var playerId = btn.dataset.playerId;
  var isActive = btn.dataset.active === "true";
  var res = await window.sb.from("players").update({ is_active: !isActive }).eq("id", playerId);
  if (res.error) { alert(res.error.message); return; }
  await refreshPlayers();
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
        if (payload.home_score === null || payload.away_score === null || isNaN(payload.home_score) || isNaN(payload.away_score)) {
          alert("Enter both scores before marking a match completed (otherwise both teams would be given a draw).");
          return;
        }
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

// ---------- RECORDS: appearances, notes/ratings, suspensions, awards ----------
async function populateAppearanceMatchDropdown() {
  var res = await window.sb.from("matches").select("*").eq("season_id", CURRENT_SEASON.id).order("match_day").order("match_number");
  var teamsById = {};
  TEAMS_CACHE.forEach(function (t) { teamsById[t.id] = t; });
  var sel = document.getElementById("ap-match");
  sel.innerHTML = '<option value="">— select match —</option>' + (res.data || []).map(function (m) {
    var home = teamsById[m.home_team_id] ? teamsById[m.home_team_id].name : "?";
    var away = teamsById[m.away_team_id] ? teamsById[m.away_team_id].name : "?";
    return '<option value="' + m.id + '">Day ' + m.match_day + " M" + m.match_number + ": " + home + " vs " + away + "</option>";
  }).join("");
}

async function onLogAppearance(e) {
  e.preventDefault();
  var msg = document.getElementById("appearance-msg");
  var payload = {
    match_id: document.getElementById("ap-match").value,
    player_id: document.getElementById("ap-player").value,
    team_id: document.getElementById("ap-team").value,
    started: document.getElementById("ap-started").checked,
    is_captain: document.getElementById("ap-captain").checked,
    position_played: document.getElementById("ap-position").value.trim() || null,
    minutes_played: document.getElementById("ap-minutes").value || null
  };
  if (!payload.match_id || !payload.player_id || !payload.team_id) { showError(msg, "Match, player, and team are all required."); return; }
  var res = await window.sb.from("match_appearances").upsert(payload, { onConflict: "match_id,player_id" });
  if (res.error) { showError(msg, res.error.message); return; }
  showSuccess(msg, "Appearance logged.");
  document.getElementById("appearance-form").reset();
  document.getElementById("ap-started").checked = true;
}

async function onLogNote(e) {
  e.preventDefault();
  var msg = document.getElementById("note-msg");
  var playerId = document.getElementById("note-player").value;
  var noteType = document.getElementById("note-type").value;
  var noteText = document.getElementById("note-text").value.trim();
  if (!playerId || !noteText) { showError(msg, "Player and note text are required."); return; }

  var logRes = await window.sb.from("player_notes_log").insert({ player_id: playerId, note_type: noteType, note: noteText });
  if (logRes.error) { showError(msg, logRes.error.message); return; }

  // Keep the player's current-snapshot field (shown on their profile) in sync.
  var column = noteType === "fitness" ? "fitness_notes" : "leave_plan";
  var updatePayload = {};
  updatePayload[column] = noteText;
  await window.sb.from("players").update(updatePayload).eq("id", playerId);

  showSuccess(msg, "Note logged and profile updated.");
  document.getElementById("note-form").reset();
}

async function onLogRating(e) {
  e.preventDefault();
  var msg = document.getElementById("rating-msg");
  var playerId = document.getElementById("rating-player").value;
  var seasonId = document.getElementById("rating-season").value;
  var ratingValue = document.getElementById("rating-value").value || null;
  var levelValue = document.getElementById("rating-level").value || null;
  if (!playerId || !seasonId) { showError(msg, "Player and season are required."); return; }
  if (!ratingValue && !levelValue) { showError(msg, "Enter a rating and/or a skill level."); return; }

  var logRes = await window.sb.from("player_rating_log").insert({
    player_id: playerId, season_id: seasonId,
    skill_rating: ratingValue, skill_level: levelValue,
    notes: document.getElementById("rating-notes").value.trim() || null
  });
  if (logRes.error) { showError(msg, logRes.error.message); return; }

  var updatePayload = {};
  if (ratingValue) updatePayload.skill_rating = ratingValue;
  if (levelValue) updatePayload.skill_level = levelValue;
  await window.sb.from("players").update(updatePayload).eq("id", playerId);

  showSuccess(msg, "Rating logged and profile updated.");
  document.getElementById("rating-form").reset();
  document.getElementById("rating-season").value = seasonId;
}

async function onLogSuspension(e) {
  e.preventDefault();
  var msg = document.getElementById("suspension-msg");
  var payload = {
    player_id: document.getElementById("susp-player").value,
    season_id: document.getElementById("susp-season").value,
    reason: document.getElementById("susp-reason").value.trim(),
    matches_banned: parseInt(document.getElementById("susp-matches").value, 10) || 1
  };
  if (!payload.player_id || !payload.season_id || !payload.reason) { showError(msg, "Player, season, and reason are all required."); return; }
  var res = await window.sb.from("suspensions").insert(payload);
  if (res.error) { showError(msg, res.error.message); return; }
  showSuccess(msg, "Suspension logged.");
  document.getElementById("suspension-form").reset();
}

async function onLogAward(e) {
  e.preventDefault();
  var msg = document.getElementById("award-msg");
  var payload = {
    season_id: document.getElementById("award-season").value,
    award_type: document.getElementById("award-type").value,
    player_id: document.getElementById("award-player").value || null,
    team_id: document.getElementById("award-team").value || null,
    notes: document.getElementById("award-notes").value.trim() || null
  };
  if (!payload.season_id || !payload.award_type) { showError(msg, "Season and award type are required."); return; }
  if (!payload.player_id && !payload.team_id) { showError(msg, "Pick a player or a team for this award."); return; }
  var res = await window.sb.from("season_awards").insert(payload);
  if (res.error) { showError(msg, res.error.message); return; }
  showSuccess(msg, "Award logged.");
  document.getElementById("award-form").reset();
}

// ---------- TIE-BREAK SHOOT-OUT ORDER (last-resort standings tie-break) ----------
async function initShootoutForm() {
  var real = TEAMS_CACHE.filter(function (t) { return !/^Team [A-Z]$/.test(t.name) && t.is_active !== false; });
  var box = document.getElementById("shootout-teams");
  var res = await window.sb.from("tiebreak_shootout_order").select("*").eq("season_id", CURRENT_SEASON.id);
  var existing = {};
  (res.data || []).forEach(function (r) { existing[r.team_id] = r.position; });
  if (res.error) { box.innerHTML = '<p class="muted">Run sql/migration_tiebreak_shootouts.sql to enable this.</p>'; return; }
  box.innerHTML = real.map(function (t) {
    return '<div style="display:flex; align-items:center; gap:10px; margin:6px 0;">' +
      '<input type="number" min="1" max="' + real.length + '" data-team-id="' + t.id + '" value="' + (existing[t.id] || "") + '" style="width:80px;">' +
      "<span>" + escapeHtml(t.name) + "</span></div>";
  }).join("");
  var form = document.getElementById("shootout-form");
  if (form.dataset.bound) return;
  form.dataset.bound = "1";
  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    var msg = document.getElementById("shootout-msg");
    var open = await window.sb.from("matches").select("id", { count: "exact", head: true })
      .eq("season_id", CURRENT_SEASON.id).in("status", ["scheduled", "postponed"]);
    if (open.count > 0) {
      msg.textContent = "Not allowed yet: " + open.count + " match(es) are still scheduled/postponed. A tie-break shoot-out is only allowed once the tournament is complete.";
      return;
    }
    var entries = [];
    document.querySelectorAll("#shootout-teams input").forEach(function (inp) {
      if (inp.value !== "") entries.push({ season_id: CURRENT_SEASON.id, team_id: inp.dataset.teamId, position: parseInt(inp.value, 10) });
    });
    var seen = {};
    for (var i = 0; i < entries.length; i++) {
      if (!(entries[i].position >= 1) || seen[entries[i].position]) { msg.textContent = "Each shoot-out position must be a unique number (1, 2, 3 …)."; return; }
      seen[entries[i].position] = true;
    }
    var del = await window.sb.from("tiebreak_shootout_order").delete().eq("season_id", CURRENT_SEASON.id);
    if (del.error) { msg.textContent = "Error: " + del.error.message; return; }
    if (entries.length) {
      var ins = await window.sb.from("tiebreak_shootout_order").insert(entries);
      if (ins.error) { msg.textContent = "Error: " + ins.error.message; return; }
    }
    msg.textContent = "Saved.";
  });
}
