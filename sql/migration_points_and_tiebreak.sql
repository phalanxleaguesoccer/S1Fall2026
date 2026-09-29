-- Points: Win 2, Draw 1, Loss 0 (standings recalculate automatically from
-- completed matches, so nothing else is needed after a result is saved).
alter table seasons alter column points_win set default 2;
alter table seasons alter column points_draw set default 1;
alter table seasons alter column points_loss set default 0;
update seasons set points_win = 2, points_draw = 1, points_loss = 0;

-- (Penalty shoot-out tie-break lives in migration_tiebreak_shootouts.sql)

-- Safety: a match marked "completed" with blank scores must not hand both
-- teams a draw. Only count completed matches that actually have scores.
create or replace view league_standings as
with raw_team_matches as (
  select
    s.id as season_id,
    t.id as team_id,
    m.id as match_id,
    m.status,
    m.forfeited_by_team_id,
    case when m.home_team_id = t.id then m.home_score else m.away_score end as goals_for,
    case when m.home_team_id = t.id then m.away_score else m.home_score end as goals_against
  from seasons s
  join teams t on true
  join matches m on m.season_id = s.id and (m.home_team_id = t.id or m.away_team_id = t.id)
  where m.status = 'forfeited'
     or (m.status = 'completed' and m.home_score is not null and m.away_score is not null)
),
team_matches as (
  select
    season_id, team_id, match_id, status, goals_for, goals_against,
    case
      when status = 'forfeited' and forfeited_by_team_id = team_id then 'loss'
      when status = 'forfeited' and forfeited_by_team_id != team_id then 'win'
      when status = 'completed' and goals_for > goals_against then 'win'
      when status = 'completed' and goals_for < goals_against then 'loss'
      when status = 'completed' then 'draw'
      else null
    end as result
  from raw_team_matches
)
select
  tm.season_id,
  tm.team_id,
  count(*) as played,
  count(*) filter (where result = 'win') as wins,
  count(*) filter (where result = 'draw') as draws,
  count(*) filter (where result = 'loss') as losses,
  coalesce(sum(goals_for), 0) as goals_for,
  coalesce(sum(goals_against), 0) as goals_against,
  coalesce(sum(goals_for), 0) - coalesce(sum(goals_against), 0) as goal_difference,
  (count(*) filter (where result = 'win')) * (select points_win from seasons where id = tm.season_id)
  + (count(*) filter (where result = 'draw')) * (select points_draw from seasons where id = tm.season_id)
  + (count(*) filter (where result = 'loss')) * (select points_loss from seasons where id = tm.season_id)
  as points
from team_matches tm
group by tm.season_id, tm.team_id;
