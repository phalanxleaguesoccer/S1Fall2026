-- MATCH DAY 5 (Matches 17-20): scores, toss, lineups (played / rested / absent), captains (all four matches) and every event, from the owner's scorecards.
--   M17 Scouts FC 4-0 Desi Steelers FC   M18 Renegades 1-1 Muggles FC   M19 Renegades 0-1 Desi Steelers FC   M20 Muggles FC 0-2 Scouts FC
-- Times were given as TIME REMAINING in the half; they are converted (1st half: played = 10:00 - remaining; 2nd half: played = 10:00 + (10:00 - remaining)).
-- Safe to re-run: it REPLACES the lineups and events of the four Day 5 matches (this is the base the stats read from).
-- Final scores are COUNTED FROM THE GOALS and then checked against the scores you gave; if they differ, the script stops and changes nothing.
-- Players are matched by name to their own squad; if anything does not fit, it stops and changes nothing.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  r record; mid uuid; tid uuid; pid uuid; rid uuid; n_ok int; el int; m uuid[]; bad text;
begin
  for i in 1..4 loop
    select id into mid from matches where season_id = s and match_day = 5 and match_number = i;
    if mid is null then raise exception 'Match Day 5 Match % not found', i; end if;
    m := array_append(m, mid);
  end loop;
  -- the schedule must be the one the scorecards describe
  for r in select * from (values (1,'Scouts FC','Desi Steelers FC'),(2,'Renegades','Muggles FC'),(3,'Renegades','Desi Steelers FC'),(4,'Muggles FC','Scouts FC')) v(n,t1,t2) loop
    perform 1 from matches x join teams h on h.id = x.home_team_id join teams a on a.id = x.away_team_id
     where x.id = m[r.n] and ((h.name = r.t1 and a.name = r.t2) or (h.name = r.t2 and a.name = r.t1));
    if not found then raise exception 'Day 5 Match % is not % vs % in the schedule; nothing changed', r.n, r.t1, r.t2; end if;
  end loop;

  -- keep nothing from earlier attempts for these four matches
  delete from match_events where match_id = any(m);
  delete from match_appearances where match_id = any(m);

  -- ---------- 1. toss ----------
  for r in select * from (values (1,'Scouts FC','side'),(2,'Renegades','kickoff'),(3,'Renegades','kickoff'),(4,'Muggles FC','side')) v(n, who, choice) loop
    update matches set toss_winner_team_id = (select id from teams where name = r.who), toss_choice = r.choice where id = m[r.n];
  end loop;

  -- ---------- 2. lineups: everyone in both squads PLAYED unless listed as rested / absent ----------
  insert into match_appearances (match_id, player_id, team_id, status, started)
  select x.id, tsr.player_id, tsr.team_id, 'played', true
  from matches x join team_season_rosters tsr on tsr.season_id = x.season_id and tsr.team_id in (x.home_team_id, x.away_team_id)
  where x.id = any(m);

  for r in
    select * from (values
      -- n, status, player
      (1,'rested','Kartik'),
      (1,'absent','Jitendra'),(1,'absent','Vija'),(1,'absent','Rishabh Devgon'),(1,'absent','Sagar SJ'),(1,'absent','Vamshi'),
      (2,'rested','Minti'),
      (2,'absent','Ashu'),(2,'absent','Dheeraj R Vatti'),
      (3,'rested','Varun'),
      (3,'absent','Vija'),(3,'absent','Rishabh Devgon'),(3,'absent','Vamshi'),
      (4,'rested','Dheeraj R Vatti'),
      (4,'absent','Jitendra'),(4,'absent','Ashu'),(4,'absent','Kartik')
    ) v(n, status, who)
  loop
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Player "%" not found', r.who; end if;
    update match_appearances set status = r.status, started = false where match_id = m[r.n] and player_id = pid;
    get diagnostics n_ok = row_count;
    if n_ok <> 1 then raise exception 'Day 5 Match %: "%" is not in either squad of this match', r.n, r.who; end if;
  end loop;

  -- captains
  for r in
    select * from (values (1,'Desi Steelers FC','Nasiq'),(1,'Scouts FC','Pradnyal Gandhi'),(2,'Muggles FC','Amritpal Singh'),(2,'Renegades','Dhananjay'),
      (3,'Desi Steelers FC','Ketan Shilimkar'),(3,'Renegades','Dhananjay'),(4,'Muggles FC','Amritpal Singh'),(4,'Scouts FC','Pradnyal Gandhi')) v(n, team, who)
  loop
    select id into pid from players where full_name = r.who;
    select id into tid from teams where name = r.team;
    update match_appearances set is_captain = true, captain_stand_in = false
     where match_id = m[r.n] and player_id = pid and team_id = tid and status = 'played';
    get diagnostics n_ok = row_count;
    if n_ok <> 1 then raise exception 'Day 5 Match %: captain "%" did not play for %', r.n, r.who, r.team; end if;
  end loop;

  -- ---------- 3. events: match, player, type, half, time REMAINING in seconds, related player ----------
  for r in
    select * from (values
      -- Match 17: Scouts FC 4-0 Desi Steelers FC
      (1,'Bilal Yaser','goal',1, 6*60+10,'Sandeep Naik'),
      (1,'Sandeep Naik','assist',1, 6*60+10,'Bilal Yaser'),
      (1,'Bilal Yaser','goal',1, 4*60+2,'Bhagyesh Rane'),
      (1,'Bhagyesh Rane','assist',1, 4*60+2,'Bilal Yaser'),
      (1,'Bilal Yaser','goal',1, 2*60+42,'Bhagyesh Rane'),
      (1,'Bhagyesh Rane','assist',1, 2*60+42,'Bilal Yaser'),
      (1,'Sandeep Naik','goal',2, 1*60+54,null),
      (1,'Bilal Yaser','player_of_match',null,null,null),
      -- Match 18: Renegades 1-1 Muggles FC
      (2,'Varun','goal',2, 6*60+55,null),
      (2,'Dhananjay','yellow_card',2, 5*60+20,null),
      (2,'Dhananjay','foul',2, 5*60+20,null),
      (2,'Dhruv','goal',2, 0*60+5,'Rohith'),
      (2,'Rohith','assist',2, 0*60+5,'Dhruv'),
      (2,'Dhruv','player_of_match',null,null,null),
      -- Match 19: Renegades 0-1 Desi Steelers FC
      (3,'Kaushik Apte','goal',1, 4*60+20,'Nasiq'),
      (3,'Nasiq','assist',1, 4*60+20,'Kaushik Apte'),
      (3,'Chirag','foul',2, 8*60+20,null),
      (3,'Nasiq','yellow_card',2, 1*60+20,null),
      (3,'Kaushik Apte','player_of_match',null,null,null),
      -- Match 20: Muggles FC 0-2 Scouts FC
      (4,'Sandeep Naik','yellow_card',1, 7*60+20,null),
      (4,'Bilal Yaser','goal',1, 0*60+20,'Sagar SJ'),
      (4,'Sagar SJ','assist',1, 0*60+20,'Bilal Yaser'),
      (4,'Bhagyesh Rane','goal',2, 0*60+59,null),
      (4,'Bhagyesh Rane','player_of_match',null,null,null)
    ) v(n, who, typ, half, remaining, rel)
  loop
    mid := m[r.n];
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Match %: player "%" not found', r.n, r.who; end if;
    select team_id into tid from match_appearances where match_id = mid and player_id = pid and status = 'played';
    if tid is null then raise exception 'Day 5 Match %: "%" did not play in this match', r.n, r.who; end if;
    rid := null;
    if r.rel is not null then
      select id into rid from players where full_name = r.rel;
      if rid is null then raise exception 'Match %: player "%" not found', r.n, r.rel; end if;
    end if;
    if r.remaining is null then
      insert into match_events (match_id, team_id, player_id, event_type, half, is_penalty, created_at)
      values (mid, tid, pid, r.typ, 2, false, clock_timestamp());
    else
      el := (case when r.half = 1 then 0 else 600 end) + (600 - r.remaining);
      insert into match_events (match_id, team_id, player_id, event_type, half, minute, second, time_remaining, related_player_id, is_penalty, created_at)
      values (mid, tid, pid, r.typ, r.half, el / 60, el % 60, r.remaining, rid, false, clock_timestamp());
    end if;
  end loop;

  -- ---------- 4. final scores = goals counted from the scorecards; must equal the scores you gave ----------
  update matches x set status = 'completed', live_phase = null, clock_running = false,
    home_score = (select count(*) from match_events e where e.match_id = x.id and ((e.event_type = 'goal' and e.team_id = x.home_team_id) or (e.event_type = 'own_goal' and e.team_id = x.away_team_id))),
    away_score = (select count(*) from match_events e where e.match_id = x.id and ((e.event_type = 'goal' and e.team_id = x.away_team_id) or (e.event_type = 'own_goal' and e.team_id = x.home_team_id)))
  where x.id = any(m);

  -- expected goals per team per match (as given by the owner), compared with the goals each team has on the scorecard
  select string_agg(format('Match %s: %s has %s on the scorecard, expected %s', v.n, v.team, got.g, v.goals), '; ') into bad
  from (values (1,'Scouts FC',4),(1,'Desi Steelers FC',0),(2,'Renegades',1),(2,'Muggles FC',1),(3,'Renegades',0),(3,'Desi Steelers FC',1),(4,'Muggles FC',0),(4,'Scouts FC',2)) v(n, team, goals)
  cross join lateral (
    select case when x.home_team_id = t.id then x.home_score else x.away_score end g
    from matches x, teams t where x.id = m[v.n] and t.name = v.team) got
  where got.g is distinct from v.goals;
  if bad is not null then raise exception 'Scores do not match the scorecards: %', bad; end if;
end $$;

-- Check: what is now recorded for Day 5
select m.match_number as match_of_day5, h.name as home, m.home_score, m.away_score, a.name as away, m.status,
  (select name from teams where id = m.toss_winner_team_id) as toss_won_by, m.toss_choice,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'played') as played,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'rested') as rested,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'absent') as absent,
  (select count(*) from match_events e where e.match_id = m.id) as events,
  (select p.full_name from match_events e join players p on p.id = e.player_id where e.match_id = m.id and e.event_type = 'player_of_match') as player_of_match
from matches m join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id
where m.match_day = 5 order by m.match_number;
