-- Adds Renegades as a 4th standalone identity team (owner: Varun, "Zack" on
-- his jersey), not tied to any scheduled match — same as Desi Steelers FC,
-- Muggles FC, and Scouts FC. The actual Team A/B/C/D schedule slots are
-- untouched; those get assigned to real teams once the draw happens.

insert into teams (name, crest_url) values
  ('Renegades', 'assets/teams/renegades.png');

insert into team_season_rosters (season_id, team_id, player_id, is_owner)
select s.id, t.id, p.id, true
from seasons s, teams t, players p
where s.is_current = true
  and t.name = 'Renegades'
  and p.full_name = 'Varun'
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = true;
