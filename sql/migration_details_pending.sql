-- Score-only matches ("details pending"): a completed match with no lineup yet no longer counts as played by everybody.
-- Standings use the score straight away; players get Played/W/D/L when the lineup is entered. Goals etc. count as soon as events exist.
-- Run on PREPROD, then live. Safe to re-run. Already included in migration_live_scoring.sql (section 8); run this alone only if that was run earlier.
create or replace view player_season_stats as
SELECT p.id AS player_id,
    p.full_name,
    tsr.season_id,
    tsr.team_id,
    count(DISTINCT m.id) FILTER (WHERE m.status = 'completed'::text AND (m.home_team_id = tsr.team_id OR m.away_team_id = tsr.team_id) AND ma.status = 'played'::text) AS games_played,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'goal'::text) AS goals,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'assist'::text) AS assists,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'yellow_card'::text) AS yellow_cards,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'red_card'::text) AS red_cards,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'player_of_match'::text) AS potm_awards,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'save'::text) AS saves,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'player_of_tournament'::text) AS tournament_awards,
    count(DISTINCT ma.match_id) FILTER (WHERE ma.status = 'played'::text AND m.status = 'completed'::text AND (m.home_team_id = tsr.team_id AND m.away_score = 0 OR m.away_team_id = tsr.team_id AND m.home_score = 0)) AS clean_sheets,
    count(DISTINCT ma.match_id) FILTER (WHERE ma.status = 'rested'::text AND m.status = 'completed'::text) AS rested,
    count(DISTINCT ma.match_id) FILTER (WHERE ma.status = 'absent'::text AND m.status = 'completed'::text) AS absent,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'own_goal'::text) AS own_goals,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'foul'::text) AS fouls
   FROM players p
     JOIN team_season_rosters tsr ON tsr.player_id = p.id
     LEFT JOIN matches m ON m.season_id = tsr.season_id AND (m.home_team_id = tsr.team_id OR m.away_team_id = tsr.team_id)
     LEFT JOIN match_appearances ma ON ma.player_id = p.id AND ma.match_id = m.id
     LEFT JOIN match_events me ON me.player_id = p.id AND me.match_id = m.id AND m.status = 'completed'
  GROUP BY p.id, p.full_name, tsr.season_id, tsr.team_id;
