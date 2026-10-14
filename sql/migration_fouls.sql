-- Fouls (tracked whether or not a card is shown).
-- A foul is a match event with event_type = 'foul' (player_id = the player who committed it).
-- Adds a fouls column to player_season_stats (appended as the last column).
-- A foul is a foul: a yellow or red card is NOT counted as a foul; record the card and the foul separately.

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
  count(distinct me.id) filter (where me.event_type = 'own_goal') as own_goals,
  count(distinct me.id) filter (where me.event_type = 'foul') as fouls
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_appearances ma on ma.player_id = p.id and ma.match_id = m.id
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;
