-- Own goals.
-- An own goal is recorded as a match event with event_type = 'own_goal':
--   * player_id = the player who put the ball into his own net
--   * team_id   = that player's OWN team (the goal counts for the opposing team)
-- It is NOT counted in the player's goals. This adds an own_goals column to player_season_stats
-- (appended as the last column; everything else is unchanged from migration_attendance.sql).
create or replace view player_season_stats as
select
  p.id as player_id,
  p.full_name,
  tsr.season_id,
  tsr.team_id,
  count(distinct m.id) filter (
    where m.status = 'completed'
      and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
      and (ma.status = 'played'
           or (ma.id is null and not exists (select 1 from match_appearances x where x.match_id = m.id and x.team_id = tsr.team_id)))
  ) as games_played,
  count(distinct me.id) filter (where me.event_type = 'goal') as goals,
  count(distinct me.id) filter (where me.event_type = 'assist') as assists,
  count(distinct me.id) filter (where me.event_type = 'yellow_card') as yellow_cards,
  count(distinct me.id) filter (where me.event_type = 'red_card') as red_cards,
  count(distinct me.id) filter (where me.event_type = 'player_of_match') as potm_awards,
  count(distinct me.id) filter (where me.event_type = 'save') as saves,
  count(distinct me.id) filter (where me.event_type = 'player_of_tournament') as tournament_awards,
  count(distinct ma.match_id) filter (
    where ma.status = 'played' and m.status = 'completed'
      and ((m.home_team_id = tsr.team_id and m.away_score = 0)
        or (m.away_team_id = tsr.team_id and m.home_score = 0))
  ) as clean_sheets,
  count(distinct ma.match_id) filter (where ma.status = 'rested' and m.status = 'completed') as rested,
  count(distinct ma.match_id) filter (where ma.status = 'absent' and m.status = 'completed') as absent,
  count(distinct me.id) filter (where me.event_type = 'own_goal') as own_goals
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_appearances ma on ma.player_id = p.id and ma.match_id = m.id
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;
