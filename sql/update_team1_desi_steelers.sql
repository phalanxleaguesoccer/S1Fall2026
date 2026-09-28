-- Renames "Team A" to "Desi Steelers FC" with a new crest, and sets Nasiq as
-- the team owner for the current season. Only the teams.name/crest_url and a
-- team_season_rosters row change here — match_day fixtures in `matches`
-- reference teams by team_id (a stable UUID), not by name, so the existing
-- schedule (seed_schedule.sql) is untouched by this rename.

update teams
set name = 'Desi Steelers FC',
    crest_url = 'assets/teams/desi-steelers-fc.png'
where name = 'Team A';

-- Assigns Nasiq to Desi Steelers FC as owner for the current season.
-- (No jersey_number/auction_price yet since owners are pre-auction.)
insert into team_season_rosters (season_id, team_id, player_id, is_owner)
select s.id, t.id, p.id, true
from seasons s, teams t, players p
where s.is_current = true
  and t.name = 'Desi Steelers FC'
  and p.full_name = 'Nasiq'
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = true;
