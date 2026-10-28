-- One-week transfers ("loans"): a player whose lineup row (match_appearances.team_id) names a team other than his roster team plays FOR THAT TEAM that match.
--  * he gets a second stats row (his roster team + the team he played for), so profiles show both teams and totals add up
--  * his roster team's matches on that match day do not count for him at all (not played, not absent)
-- Run after migration_live_scoring.sql / migration_details_pending.sql. Safe to re-run. The database still allows one roster team per season.
create or replace view player_season_stats as
WITH stints AS (
  SELECT tsr.player_id, tsr.season_id, tsr.team_id, false AS loan FROM team_season_rosters tsr
  UNION
  SELECT ma.player_id, m.season_id, ma.team_id, true AS loan
  FROM match_appearances ma
    JOIN matches m ON m.id = ma.match_id
    JOIN team_season_rosters t ON t.player_id = ma.player_id AND t.season_id = m.season_id
  WHERE ma.team_id <> t.team_id
)
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
     JOIN stints tsr ON tsr.player_id = p.id
     LEFT JOIN matches m ON m.season_id = tsr.season_id AND (m.home_team_id = tsr.team_id OR m.away_team_id = tsr.team_id)
       AND (tsr.loan
            OR NOT EXISTS (SELECT 1 FROM match_appearances x JOIN matches xm ON xm.id = x.match_id
                           WHERE x.player_id = tsr.player_id AND xm.season_id = m.season_id AND xm.match_day = m.match_day AND x.team_id <> tsr.team_id))
       AND (NOT tsr.loan
            OR EXISTS (SELECT 1 FROM match_appearances x WHERE x.player_id = tsr.player_id AND x.match_id = m.id AND x.team_id = tsr.team_id))
     LEFT JOIN match_appearances ma ON ma.player_id = p.id AND ma.match_id = m.id
     LEFT JOIN match_events me ON me.player_id = p.id AND me.match_id = m.id AND m.status = 'completed'
  GROUP BY p.id, p.full_name, tsr.season_id, tsr.team_id;
