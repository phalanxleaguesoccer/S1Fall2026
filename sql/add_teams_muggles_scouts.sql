-- Adds 2 new teams: Muggles FC (owner: Amritpal Singh) and Scouts FC
-- (owner: Bhagyesh Rane — run seed_players_batch7.sql first, since this
-- depends on his player row existing).
--
-- Note: the original 24-match schedule (seed_schedule.sql) only fixtures
-- Team A/B/C/D (now including the renamed Desi Steelers FC) — these 2 new
-- teams get no matches automatically; add fixtures for them separately if
-- they're meant to play this season.

insert into teams (name, crest_url) values
  ('Muggles FC', 'assets/teams/muggles-fc.png'),
  ('Scouts FC', 'assets/teams/scouts-fc.png');

insert into team_season_rosters (season_id, team_id, player_id, is_owner)
select s.id, t.id, p.id, true
from seasons s, teams t, players p
where s.is_current = true
  and t.name = 'Muggles FC'
  and p.full_name = 'Amritpal Singh'
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = true;

insert into team_season_rosters (season_id, team_id, player_id, is_owner)
select s.id, t.id, p.id, true
from seasons s, teams t, players p
where s.is_current = true
  and t.name = 'Scouts FC'
  and p.full_name = 'Bhagyesh Rane'
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = true;
