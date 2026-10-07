-- Attendance: every squad member is Played, Rested or Absent in each match.
-- Run this BEFORE sql/day1_lineups.sql.
--  * match_appearances.status  = 'played' | 'rested' | 'absent'
--  * player_season_stats: games_played now counts only matches the player actually PLAYED
--    (for completed matches where a team has no lineup entered at all, everyone still counts as played,
--    exactly like before), plus new columns rested and absent.
alter table match_appearances add column if not exists status text not null default 'played';
alter table match_appearances drop constraint if exists match_appearances_status_check;
alter table match_appearances add constraint match_appearances_status_check check (status in ('played','rested','absent'));

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
  count(distinct ma.match_id) filter (where ma.status = 'absent' and m.status = 'completed') as absent
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_appearances ma on ma.player_id = p.id and ma.match_id = m.id
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;
