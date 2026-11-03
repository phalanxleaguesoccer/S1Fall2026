-- READ-ONLY consistency audit. Paste into Supabase SQL editor and run. It changes nothing.
-- Base of truth = the MATCH SCORECARDS (matches + match_events + match_appearances).
-- Everything else (team standings, season stats, player profiles) is derived from them, so any row returned is a discrepancy.
-- Result: one row per problem (check, match/player, detail). ZERO ROWS = everything matches.
with s as (select id from seasons where is_current limit 1),
mm as (select m.*, h.name hn, a.name an from matches m join s on s.id = m.season_id join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id),
lbl as (select id, 'Day '||match_day||' M'||match_number||' '||hn||' v '||an as l from mm),
ev as (select e.*, p.full_name pname from match_events e join players p on p.id = e.player_id where e.match_id in (select id from mm)),
-- goals credited to each side from the scorecard events (goal for the scorer's team; own goal for the OTHER team)
ev_goals as (
  select m.id match_id,
    count(*) filter (where (e.event_type = 'goal' and e.team_id = m.home_team_id) or (e.event_type = 'own_goal' and e.team_id = m.away_team_id)) hg,
    count(*) filter (where (e.event_type = 'goal' and e.team_id = m.away_team_id) or (e.event_type = 'own_goal' and e.team_id = m.home_team_id)) ag,
    count(*) n
  from mm m left join ev e on e.match_id = m.id group by m.id),
t_score as (
  select 'score vs events' chk, l.l what,
    'match says '||m.home_score||'-'||m.away_score||' but scorecard events give '||g.hg||'-'||g.ag as detail
  from mm m join ev_goals g on g.match_id = m.id join lbl l on l.id = m.id
  where m.status = 'completed' and (coalesce(m.home_score,-1) <> g.hg or coalesce(m.away_score,-1) <> g.ag)),
t_noscore as (
  select 'completed without score' chk, l.l, 'status completed but a score is blank' from mm m join lbl l on l.id = m.id
  where m.status = 'completed' and (m.home_score is null or m.away_score is null)),
t_evteam as (
  select 'event team not in match' chk, l.l, e.pname||' '||e.event_type||' recorded for a team that is not playing' from ev e join mm m on m.id = e.match_id join lbl l on l.id = m.id
  where e.team_id not in (m.home_team_id, m.away_team_id)),
t_lineup as (
  select 'event vs lineup' chk, l.l,
    e.pname||' has a '||e.event_type||' but '||
    case when a.id is null then 'is not in the lineup' when a.status <> 'played' then 'is marked '||a.status||' in the lineup' else 'plays for another team in the lineup' end as detail
  from ev e join mm m on m.id = e.match_id join lbl l on l.id = m.id
  left join match_appearances a on a.match_id = e.match_id and a.player_id = e.player_id
  where e.event_type in ('goal','own_goal','assist','yellow_card','red_card','foul','save','player_of_match')
    and m.status = 'completed'
    and exists (select 1 from match_appearances x where x.match_id = m.id)   -- only matches that have a lineup
    and (a.id is null or a.status <> 'played' or a.team_id <> e.team_id)),
t_nolineup as (
  select 'no lineup (details pending)' chk, l.l, 'completed, but nobody is recorded as played, so no one gets a game played' from mm m join lbl l on l.id = m.id
  where m.status = 'completed' and not exists (select 1 from match_appearances x where x.match_id = m.id and x.status = 'played')),
t_potm as (
  select 'player of the match' chk, l.l, case when c = 0 then 'no Player of the Match recorded' else c||' Players of the Match recorded' end
  from (select m.id, count(e.id) c from mm m left join ev e on e.match_id = m.id and e.event_type = 'player_of_match' where m.status = 'completed' group by m.id) x
  join lbl l on l.id = x.id where c <> 1),
t_assist as (
  select 'assist without goal' chk, l.l, e.pname||' has an assist but the related scorer has no goal in this match' from ev e join lbl l on l.id = e.match_id
  where e.event_type = 'assist' and (e.related_player_id is null or not exists (select 1 from ev g where g.match_id = e.match_id and g.event_type = 'goal' and g.player_id = e.related_player_id))
  union all
  select 'goal assist mismatch', l.l, e.pname||' goal lists an assist by someone who has no assist event' from ev e join lbl l on l.id = e.match_id
  where e.event_type = 'goal' and e.related_player_id is not null and not exists (select 1 from ev a where a.match_id = e.match_id and a.event_type = 'assist' and a.player_id = e.related_player_id)),
t_dup as (
  select 'possible duplicate event' chk, l.l, e.pname||' '||e.event_type||' entered '||count(*)||' times at the same moment'
  from ev e join lbl l on l.id = e.match_id group by l.l, e.pname, e.event_type, e.half, e.minute, e.second having count(*) > 1 and e.event_type not in ('foul')),
-- standings recomputed from the matches themselves
st_calc as (
  select t.id team_id, t.name,
    count(*) played,
    count(*) filter (where gf > ga) w, count(*) filter (where gf = ga) d, count(*) filter (where gf < ga) l,
    sum(gf) gf, sum(ga) ga
  from teams t join (
    select home_team_id tid, home_score gf, away_score ga from mm where status = 'completed' and home_score is not null and away_score is not null
    union all select away_team_id, away_score, home_score from mm where status = 'completed' and home_score is not null and away_score is not null) x on x.tid = t.id
  group by t.id, t.name),
t_stand as (
  select 'standings vs matches' chk, c.name what,
    'table shows P'||ls.played||' W'||ls.wins||' D'||ls.draws||' L'||ls.losses||' GF'||ls.goals_for||' GA'||ls.goals_against||' Pts'||ls.points||' / matches give P'||c.played||' W'||c.w||' D'||c.d||' L'||c.l||' GF'||c.gf||' GA'||c.ga||' Pts'||(c.w*2+c.d) as detail
  from st_calc c join league_standings ls on ls.team_id = c.team_id and ls.season_id = (select id from s)
  where (ls.played, ls.wins, ls.draws, ls.losses, ls.goals_for, ls.goals_against, ls.points) is distinct from (c.played, c.w, c.d, c.l, c.gf, c.ga, c.w*2+c.d)),
-- team goals from scorecards vs players' goals (+ opponents' own goals)
t_players as (
  select 'player goals vs team goals' chk, c.name,
    'team scored '||c.gf||' in matches but player goals plus opponent own goals add up to '||coalesce(pg.n,0)
  from st_calc c left join (
    select (case when e.event_type = 'goal' then e.team_id else case when m.home_team_id = e.team_id then m.away_team_id else m.home_team_id end end) team_id, count(*) n
    from ev e join mm m on m.id = e.match_id where m.status = 'completed' and e.event_type in ('goal','own_goal') group by 1) pg on pg.team_id = c.team_id
  where c.gf <> coalesce(pg.n,0)),
-- player season stats view vs the scorecards (per player, all teams combined)
raw_p as (
  select p.id pid, p.full_name,
    (select count(*) from ev e join mm m on m.id = e.match_id where m.status = 'completed' and e.player_id = p.id and e.event_type = 'goal') goals,
    (select count(*) from ev e join mm m on m.id = e.match_id where m.status = 'completed' and e.player_id = p.id and e.event_type = 'assist') assists,
    (select count(*) from ev e join mm m on m.id = e.match_id where m.status = 'completed' and e.player_id = p.id and e.event_type = 'yellow_card') yc,
    (select count(*) from ev e join mm m on m.id = e.match_id where m.status = 'completed' and e.player_id = p.id and e.event_type = 'red_card') rc,
    (select count(*) from ev e join mm m on m.id = e.match_id where m.status = 'completed' and e.player_id = p.id and e.event_type = 'player_of_match') potm,
    (select count(*) from ev e join mm m on m.id = e.match_id where m.status = 'completed' and e.player_id = p.id and e.event_type = 'own_goal') og,
    (select count(*) from match_appearances a join mm m on m.id = a.match_id where m.status = 'completed' and a.player_id = p.id and a.status = 'played') gp,
    (select count(*) from match_appearances a join mm m on m.id = a.match_id where m.status = 'completed' and a.player_id = p.id and a.status = 'rested') rested,
    (select count(*) from match_appearances a join mm m on m.id = a.match_id where m.status = 'completed' and a.player_id = p.id and a.status = 'absent') absent
  from players p),
v_p as (
  select player_id, sum(goals) goals, sum(assists) assists, sum(yellow_cards) yc, sum(red_cards) rc, sum(potm_awards) potm, sum(own_goals) og, sum(games_played) gp, sum(rested) rested, sum(absent) absent
  from player_season_stats where season_id = (select id from s) group by player_id),
t_pstats as (
  select 'player stats vs scorecards' chk, r.full_name,
    'stats show GP'||coalesce(v.gp,0)||' G'||coalesce(v.goals,0)||' A'||coalesce(v.assists,0)||' YC'||coalesce(v.yc,0)||' RC'||coalesce(v.rc,0)||' POTM'||coalesce(v.potm,0)||' OG'||coalesce(v.og,0)||' Rest'||coalesce(v.rested,0)||' Abs'||coalesce(v.absent,0)
    ||' / scorecards give GP'||r.gp||' G'||r.goals||' A'||r.assists||' YC'||r.yc||' RC'||r.rc||' POTM'||r.potm||' OG'||r.og||' Rest'||r.rested||' Abs'||r.absent
  from raw_p r left join v_p v on v.player_id = r.pid
  where (coalesce(v.gp,0), coalesce(v.goals,0), coalesce(v.assists,0), coalesce(v.yc,0), coalesce(v.rc,0), coalesce(v.potm,0), coalesce(v.og,0), coalesce(v.rested,0), coalesce(v.absent,0))
        is distinct from (r.gp, r.goals, r.assists, r.yc, r.rc, r.potm, r.og, r.rested, r.absent)
    and (r.gp + r.goals + r.assists + r.yc + r.rc + r.potm + r.og + r.rested + r.absent > 0 or v.gp is not null))
select * from t_score union all select * from t_noscore union all select * from t_evteam union all select * from t_lineup
union all select * from t_nolineup union all select * from t_potm union all select * from t_assist union all select * from t_dup
union all select * from t_stand union all select * from t_players union all select * from t_pstats
order by 1, 2;
