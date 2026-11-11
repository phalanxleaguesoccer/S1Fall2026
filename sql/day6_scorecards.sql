-- MATCH DAY 6 (all four matches), from the owner's scorecards. Replaces the earlier day6_m1_m2 script.
--   M1 Scouts FC 2-0 Desi Steelers FC   M2 Renegades 0-0 Muggles FC   M3 Muggles FC 1-0 Desi Steelers FC   M4 Renegades 1-1 Scouts FC
-- Vivek is a Renegades player who played for DESI STEELERS in Match 1 and Match 3 (one-day transfer). He has no row in Renegades' matches (M2, M4).
-- M1 times are ELAPSED match time (given as 6:22 and 19:04); M3 and M4 times were given as TIME REMAINING and are converted (600 s halves).
-- Own goal (M1): Vignesh's goal is stored on Desi Steelers FC (his own team) and counts for Scouts FC.
-- Absent Vija, Rishabh, Vamshi and Ashu are flagged as injury, as in every earlier match; other absences have no reason recorded.
-- M4: Kartik and Chirag were both captains and played; Dhananjay (Renegades) was the only one rested.
-- Safe to re-run. Replaces the lineups and events of these four matches. Stops and changes nothing if a name or team does not fit or the goals do not add up to the scores.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  desi uuid := (select id from teams where name = 'Desi Steelers FC');
  vivek uuid := (select id from players where full_name = 'Vivek');
  r record; mid uuid; tid uuid; pid uuid; n_ok int; m uuid[]; bad text;
begin
  if vivek is null or desi is null then raise exception 'Vivek or Desi Steelers FC not found'; end if;
  for i in 1..4 loop
    select id into mid from matches where season_id = s and match_day = 6 and match_number = i;
    if mid is null then raise exception 'Day 6 Match % not found', i; end if;
    m := array_append(m, mid);
  end loop;
  for r in select * from (values (1,'Scouts FC','Desi Steelers FC'),(2,'Renegades','Muggles FC'),(3,'Muggles FC','Desi Steelers FC'),(4,'Renegades','Scouts FC')) v(n,t1,t2) loop
    perform 1 from matches x join teams h on h.id = x.home_team_id join teams a on a.id = x.away_team_id
     where x.id = m[r.n] and ((h.name = r.t1 and a.name = r.t2) or (h.name = r.t2 and a.name = r.t1));
    if not found then raise exception 'Day 6 Match % is not % vs % in the schedule; nothing changed', r.n, r.t1, r.t2; end if;
  end loop;

  delete from match_events where match_id = any(m);
  delete from match_appearances where match_id = any(m);

  -- toss
  for r in select * from (values (1,'Desi Steelers FC','kickoff'),(2,'Renegades','kickoff'),(3,'Muggles FC','kickoff'),(4,'Scouts FC','kickoff')) v(n, who, choice) loop
    update matches set toss_winner_team_id = (select id from teams where name = r.who), toss_choice = r.choice where id = m[r.n];
  end loop;

  -- lineups: everyone in both squads played unless rested / absent. Vivek is left out here and added to Desi Steelers below.
  insert into match_appearances (match_id, player_id, team_id, status, started)
  select x.id, tsr.player_id, tsr.team_id, 'played', true
  from matches x join team_season_rosters tsr on tsr.season_id = x.season_id and tsr.team_id in (x.home_team_id, x.away_team_id)
  where x.id = any(m) and tsr.player_id <> vivek;
  insert into match_appearances (match_id, player_id, team_id, status, started) values (m[1], vivek, desi, 'played', true), (m[3], vivek, desi, 'played', true);

  for r in select * from (values
      (1,'rested','Ajinkya P'),(1,'rested','Bhagyesh Rane'),
      (1,'absent','Vija'),(1,'absent','Rishabh Devgon'),(1,'absent','Vamshi'),
      (2,'rested','Rohith'),
      (2,'absent','Ashu'),(2,'absent','Ayush'),(2,'absent','Shailesh'),(2,'absent','Nuhu Okikiri'),
      (3,'rested','Dhruv'),
      (3,'absent','Vija'),(3,'absent','Rishabh Devgon'),(3,'absent','Vamshi'),(3,'absent','Ajinkya P'),(3,'absent','Ashu'),(3,'absent','Ayush'),
      (4,'rested','Dhananjay'),
      (4,'absent','Jitendra'),(4,'absent','Shailesh'),(4,'absent','Nuhu Okikiri')) v(n, status, who)
  loop
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Player "%" not found', r.who; end if;
    update match_appearances set status = r.status, started = false,
      absent_reason = case when r.status = 'absent' and r.who in ('Vija','Rishabh Devgon','Vamshi','Ashu') then 'injury' else null end
     where match_id = m[r.n] and player_id = pid;
    get diagnostics n_ok = row_count;
    if n_ok <> 1 then raise exception 'Day 6 Match %: "%" is not in either squad of this match', r.n, r.who; end if;
  end loop;

  -- captains (all must have played)
  for r in select * from (values
      (1,'Desi Steelers FC','Kaushik Apte'),(1,'Scouts FC','Kartik'),
      (2,'Muggles FC','Amritpal Singh'),(2,'Renegades','Dhananjay'),
      (3,'Muggles FC','Amritpal Singh'),(3,'Desi Steelers FC','Kaushik Apte'),
      (4,'Scouts FC','Kartik'),(4,'Renegades','Chirag')) v(n, team, who) loop
    select id into pid from players where full_name = r.who;
    select id into tid from teams where name = r.team;
    update match_appearances set is_captain = true, captain_stand_in = false
     where match_id = m[r.n] and player_id = pid and team_id = tid and status = 'played';
    get diagnostics n_ok = row_count;
    if n_ok <> 1 then raise exception 'Day 6 Match %: captain "%" did not play for %', r.n, r.who, r.team; end if;
  end loop;

  -- events: match, player, type, half, ELAPSED seconds from kick-off, related player
  for r in select * from (values
      (1,'Vignesh','own_goal',1, 6*60+22, null::text),
      (1,'Kartik','goal',2, 19*60+4,'Pradnyal Gandhi'),
      (1,'Pradnyal Gandhi','assist',2, 19*60+4,'Kartik'),
      (1,'Ketan Shilimkar','player_of_match',null,null,null),
      (2,'Minti','player_of_match',null,null,null),
      -- Match 3 (times given as remaining: 9:50 and 2:10 left in the 2nd half)
      (3,'Vishnu Mohan','goal',2, 600+(600-(9*60+50)),null),
      (3,'Dheeraj R Vatti','yellow_card',2, 600+(600-(2*60+10)),null),
      (3,'Vishnu Mohan','player_of_match',null,null,null),
      -- Match 4 (remaining: Prajna 0:12 left in the 2nd half, Bilal 6:22 left in the 1st, Bilal's card 6:34 left in the 2nd)
      (4,'Bilal Yaser','goal',1, 600-(6*60+22),'Bhagyesh Rane'),
      (4,'Bhagyesh Rane','assist',1, 600-(6*60+22),'Bilal Yaser'),
      (4,'Bilal Yaser','yellow_card',2, 600+(600-(6*60+34)),null),
      (4,'Prajna','goal',2, 600+(600-12),'Minti'),
      (4,'Minti','assist',2, 600+(600-12),'Prajna'),
      (4,'Prajna','player_of_match',null,null,null)) v(n, who, typ, half, elapsed, rel)
  loop
    mid := m[r.n];
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Match %: player "%" not found', r.n, r.who; end if;
    select team_id into tid from match_appearances where match_id = mid and player_id = pid and status = 'played';
    if tid is null then raise exception 'Day 6 Match %: "%" did not play in this match', r.n, r.who; end if;
    if r.elapsed is null then
      insert into match_events (match_id, team_id, player_id, event_type, half, is_penalty, created_at)
      values (mid, tid, pid, r.typ, 2, false, clock_timestamp());
    else
      insert into match_events (match_id, team_id, player_id, event_type, half, minute, second, time_remaining, related_player_id, is_penalty, created_at)
      values (mid, tid, pid, r.typ, r.half, r.elapsed / 60, r.elapsed % 60, (case when r.half = 1 then 600 else 1200 end) - r.elapsed,
              (select id from players where full_name = r.rel), false, clock_timestamp());
    end if;
  end loop;

  update matches x set status = 'completed', live_phase = null, clock_running = false,
    home_score = (select count(*) from match_events e where e.match_id = x.id and ((e.event_type = 'goal' and e.team_id = x.home_team_id) or (e.event_type = 'own_goal' and e.team_id = x.away_team_id))),
    away_score = (select count(*) from match_events e where e.match_id = x.id and ((e.event_type = 'goal' and e.team_id = x.away_team_id) or (e.event_type = 'own_goal' and e.team_id = x.home_team_id)))
  where x.id = any(m);

  select string_agg(format('Match %s: %s has %s, expected %s', v.n, v.team, got.g, v.goals), '; ') into bad
  from (values (1,'Scouts FC',2),(1,'Desi Steelers FC',0),(2,'Renegades',0),(2,'Muggles FC',0),(3,'Muggles FC',1),(3,'Desi Steelers FC',0),(4,'Renegades',1),(4,'Scouts FC',1)) v(n, team, goals)
  cross join lateral (select case when x.home_team_id = t.id then x.home_score else x.away_score end g from matches x, teams t where x.id = m[v.n] and t.name = v.team) got
  where got.g is distinct from v.goals;
  if bad is not null then raise exception 'Scores do not match the scorecards: %', bad; end if;
end $$;

-- check: Day 6 as recorded
select m.match_number as match_of_day6, h.name as home, m.home_score, m.away_score, a.name as away, m.status,
  (select name from teams where id = m.toss_winner_team_id) as toss_won_by, m.toss_choice,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'played') as played,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'rested') as rested,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'absent') as absent,
  (select count(*) from match_events e where e.match_id = m.id) as events,
  (select p.full_name from match_events e join players p on p.id = e.player_id where e.match_id = m.id and e.event_type = 'player_of_match') as player_of_match
from matches m join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id
where m.match_day = 6 order by m.match_number;
-- Vivek should show only Desi Steelers FC, in Match 1 and Match 3
select m.match_number, t.name as played_for, ma.status from match_appearances ma join matches m on m.id = ma.match_id join teams t on t.id = ma.team_id
where m.match_day = 6 and ma.player_id = (select id from players where full_name = 'Vivek') order by 1;
