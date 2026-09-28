-- Migration: adds "Goals Saved" (goalkeeper saves) and "Player of the
-- Tournament" to player stats.
--
-- Both reuse the existing match_events table (event_type is free text, no
-- schema change needed there):
--   - 'save'                 — log once per save via the admin dashboard,
--                              same as a goal/assist/card.
--   - 'player_of_tournament' — a season-wide award, not really tied to one
--                              match, but match_events requires a match_id,
--                              so log it once against any match played in
--                              that season (e.g. the final match day) for
--                              the awarded player — it's counted per
--                              season/team via the match's season_id, not
--                              tied to that specific match's outcome.

create or replace view player_season_stats as
select
  p.id as player_id,
  p.full_name,
  tsr.season_id,
  tsr.team_id,
  count(distinct m.id) filter (
    where m.status = 'completed'
    and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
  ) as games_played,
  count(*) filter (where me.event_type = 'goal') as goals,
  count(*) filter (where me.event_type = 'assist') as assists,
  count(*) filter (where me.event_type = 'yellow_card') as yellow_cards,
  count(*) filter (where me.event_type = 'red_card') as red_cards,
  count(*) filter (where me.event_type = 'player_of_match') as potm_awards,
  count(*) filter (where me.event_type = 'save') as saves,
  count(*) filter (where me.event_type = 'player_of_tournament') as tournament_awards
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;
