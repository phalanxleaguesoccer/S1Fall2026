-- Vamshi (Desi Steelers FC) missed every match through injury: Absent (injury) in all completed matches
-- except the one where he was Rested (that stays Rested).
-- Run sql/migration_injuries.sql FIRST. Safe to re-run. Re-run it after re-running any dayN_results.sql
-- (those rebuild the lineups and clear this flag).
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  pid uuid := (select id from players where full_name = 'Vamshi');
  tid uuid;
  n int;
begin
  if pid is null then raise exception 'Player Vamshi not found'; end if;
  select team_id into tid from team_season_rosters where season_id = s and player_id = pid;
  if tid is null then raise exception 'Vamshi is not in a squad this season'; end if;
  -- make sure he has a lineup row for every completed match of his team
  insert into match_appearances (match_id, player_id, team_id, status, started)
  select m.id, pid, tid, 'absent', false from matches m
  where m.season_id = s and m.status = 'completed' and tid in (m.home_team_id, m.away_team_id)
  on conflict (match_id, player_id) do nothing;
  update match_appearances set status = 'absent', started = false, absent_reason = 'injury'
  where player_id = pid and status <> 'rested'
    and match_id in (select id from matches where season_id = s and status = 'completed' and tid in (home_team_id, away_team_id));
  get diagnostics n = row_count;
  raise notice 'Vamshi marked absent (injury) in % match(es)', n;
end $$;

select m.match_day, m.match_number, ma.status, ma.absent_reason
from match_appearances ma join matches m on m.id = ma.match_id join players p on p.id = ma.player_id
where p.full_name = 'Vamshi' order by m.match_day, m.match_number;
