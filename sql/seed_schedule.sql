-- Adds 4 placeholder teams (A/B/C/D) and the full 24-match schedule.
-- Safe to run once on a fresh project with no teams yet.
-- Kickoff dates/times are left NULL (TBD) — update them later via the admin dashboard
-- or by re-running an UPDATE once dates are locked.

insert into teams (name) values ('Team A'), ('Team B'), ('Team C'), ('Team D');

with s as (
  select id as season_id from seasons where is_current = true limit 1
),
t as (
  select name, id from teams where name in ('Team A','Team B','Team C','Team D')
)
insert into matches (season_id, match_day, match_number, home_team_id, away_team_id, status)
select s.season_id, v.match_day, v.match_number, home.id, away.id, 'scheduled'
from s,
(values
  (1, 1, 'Team B', 'Team D'),
  (1, 2, 'Team A', 'Team C'),
  (1, 3, 'Team A', 'Team D'),
  (1, 4, 'Team B', 'Team C'),
  (2, 1, 'Team C', 'Team D'),
  (2, 2, 'Team A', 'Team B'),
  (2, 3, 'Team B', 'Team C'),
  (2, 4, 'Team A', 'Team D'),
  (3, 1, 'Team B', 'Team D'),
  (3, 2, 'Team A', 'Team C'),
  (3, 3, 'Team C', 'Team D'),
  (3, 4, 'Team A', 'Team B'),
  (4, 1, 'Team A', 'Team C'),
  (4, 2, 'Team B', 'Team D'),
  (4, 3, 'Team A', 'Team D'),
  (4, 4, 'Team B', 'Team C'),
  (5, 1, 'Team C', 'Team D'),
  (5, 2, 'Team A', 'Team B'),
  (5, 3, 'Team A', 'Team D'),
  (5, 4, 'Team B', 'Team C'),
  (6, 1, 'Team C', 'Team D'),
  (6, 2, 'Team A', 'Team B'),
  (6, 3, 'Team B', 'Team D'),
  (6, 4, 'Team A', 'Team C')
) as v(match_day, match_number, home_name, away_name)
join teams home on home.name = v.home_name
join teams away on away.name = v.away_name;
