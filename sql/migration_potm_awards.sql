-- Migration: adds "Player of the Match" awards to a player's stats.
--
-- Design: reuses the existing match_events table (event_type is free text,
-- no schema change needed there) with a new event_type value
-- 'player_of_match', logged once per match for the awarded player via the
-- admin dashboard's Event Log form (Team/Player/Half/Minute can be left at
-- defaults since only the award matters). player_season_stats is updated to
-- surface a potm_awards count alongside goals/assists/cards.

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
  count(*) filter (where me.event_type = 'player_of_match') as potm_awards
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;
