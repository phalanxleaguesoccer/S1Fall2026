-- MATCH DAY 4 (Matches 13-16 = Day 4 Match 1-4): lineups (played / rested / absent / injury), Vivek's one-week transfer to Desi Steelers,
-- and the scorecards of Match 13 and Match 14. Replaces day4_results_m13_m14.sql (safe to run even if that one was already run).
-- Times were given as TIME REMAINING in the half; they are converted (1st half: played = 10:00 - remaining; 2nd half: played = 10:00 + (10:00 - remaining)).
-- Safe to re-run. It REPLACES the lineups of all four Day 4 matches and the events of Match 13 and 14 (captain flags already entered are kept).
-- Match 15's events (incl. the own goal, moved from Vija to Vivek) and Match 16's events are left as they are.
-- Run migration_player_loans.sql as well (so Vivek shows for both teams). Teams are taken from each player's squad; if anything does not fit, it stops and changes nothing.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  r record; mid uuid; tid uuid; pid uuid; rid uuid; n_ok int; el int; mm uuid;
  m uuid[]; desi uuid := (select id from teams where name = 'Desi Steelers FC'); vivek uuid := (select id from players where full_name = 'Vivek');
begin
  for i in 1..4 loop
    select id into mm from matches where season_id = s and match_day = 4 and match_number = i;
    if mm is null then raise exception 'Match Day 4 Match % not found', i; end if;
    m := array_append(m, mm);
  end loop;
  if vivek is null or desi is null then raise exception 'Vivek or Desi Steelers FC not found'; end if;
  perform 1 from matches x join teams h on h.id = x.home_team_id join teams a on a.id = x.away_team_id
   where x.id = m[1] and ((h.name = 'Scouts FC' and a.name = 'Renegades') or (h.name = 'Renegades' and a.name = 'Scouts FC'));
  if not found then raise exception 'Match Day 4 Match 1 is not Scouts FC vs Renegades; check which match number this is'; end if;
  perform 1 from matches where id in (m[2], m[3]) and desi in (home_team_id, away_team_id) having count(*) = 2;
  if not found then raise exception 'Desi Steelers FC must play Day 4 Match 2 and Match 3 (Vivek''s transfer)'; end if;

  -- keep captain flags that were already entered
  create temp table cap_keep on commit drop as
    select match_id, player_id, is_captain, captain_stand_in from match_appearances where match_id = any(m) and (is_captain or captain_stand_in);

  -- ---------- 1. lineups: everyone in both squads PLAYED unless listed; Vivek is not a Renegades player in Day 4 ----------
  delete from match_events where match_id in (m[1], m[2]);
  delete from match_appearances where match_id = any(m);
  insert into match_appearances (match_id, player_id, team_id, status, started)
  select x.id, tsr.player_id, tsr.team_id, 'played', true
  from matches x join team_season_rosters tsr on tsr.season_id = x.season_id and tsr.team_id in (x.home_team_id, x.away_team_id)
  where x.id = any(m) and tsr.player_id <> vivek;
  -- Vivek plays for Desi Steelers in both of their matches (Match 2 and Match 3)
  insert into match_appearances (match_id, player_id, team_id, status, started) values (m[2], vivek, desi, 'played', true), (m[3], vivek, desi, 'played', true);

  -- n, status, player, injury?
  for r in
    select * from (values
      (1,'absent','Chirag',true),(1,'absent','Sangram Ghewade',false),(1,'rested','Nuhu Okikiri',false),(1,'rested','Bilal Yaser',false),
      (2,'rested','Amritpal Singh',false),(2,'rested','Vija',false),(2,'rested','Kaushik Apte',false),(2,'absent','Vamshi',true),(2,'absent','Ashu',false),
      (3,'rested','Sangram Ghewade',false),(3,'rested','Rishabh Devgon',false),
      (4,'absent','Ashu',false),(4,'absent','Jitendra',false)
    ) v(n, status, who, inj)
  loop
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Player "%" not found', r.who; end if;
    update match_appearances set status = r.status, started = false, absent_reason = case when r.inj then 'injury' else null end
     where match_id = m[r.n] and player_id = pid;
    get diagnostics n_ok = row_count;
    if n_ok <> 1 then raise exception 'Day 4 Match %: "%" is not in either squad of this match', r.n, r.who; end if;
  end loop;

  update match_appearances a set is_captain = k.is_captain, captain_stand_in = k.captain_stand_in
    from cap_keep k where a.match_id = k.match_id and a.player_id = k.player_id;

  -- ---------- 2. the own goal in Match 3 belongs to Vivek (it was entered under Vija) ----------
  update match_events set player_id = vivek, team_id = desi where match_id = m[3] and event_type = 'own_goal' and player_id = (select id from players where full_name = 'Vija');
  get diagnostics n_ok = row_count;
  if n_ok = 0 then
    perform 1 from match_events where match_id = m[3] and event_type = 'own_goal' and player_id = vivek;
    if not found then raise exception 'Day 4 Match 3: no own goal by Vija (or Vivek) found'; end if;
  end if;

  -- ---------- 3. events of Match 1 (= Match 13) and Match 2 (= Match 14); half, time REMAINING in seconds, related player ----------
  for r in
    select * from (values
      (1,'Minti','own_goal',1, 8*60+10, null::text),
      (1,'Sagar SJ','goal',1, 6*60+52, 'Pradnyal Gandhi'),
      (1,'Pradnyal Gandhi','assist',1, 6*60+52, 'Sagar SJ'),
      (1,'Bhagyesh Rane','goal',2, 0*60+20, 'Pradnyal Gandhi'),
      (1,'Pradnyal Gandhi','assist',2, 0*60+20, 'Bhagyesh Rane'),
      (1,'Bhagyesh Rane','player_of_match',null, null, null),
      (2,'Dhruv','goal',1, 8*60+18, 'Vishnu Mohan'),
      (2,'Vishnu Mohan','assist',1, 8*60+18, 'Dhruv'),
      (2,'Rishabh Devgon','yellow_card',1, 4*60+15, null),
      (2,'Vishnu Mohan','goal',1, 4*60+10, null),
      (2,'Dhruv','goal',2, 8*60+58, null),
      (2,'Nasiq','goal',2, 6*60+30, null)
    ) v(n, who, typ, half, remaining, rel)
  loop
    mid := m[r.n];
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Match %: player "%" not found', r.n, r.who; end if;
    select team_id into tid from match_appearances where match_id = mid and player_id = pid;
    if tid is null then raise exception 'Day 4 Match %: "%" is not in the lineup of this match', r.n, r.who; end if;
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

  -- ---------- 4. final scores of Match 1 and 2 come from the goals (own goals count for the other team) ----------
  update matches x set status = 'completed', live_phase = null, clock_running = false,
    home_score = (select count(*) from match_events e where e.match_id = x.id and ((e.event_type = 'goal' and e.team_id = x.home_team_id) or (e.event_type = 'own_goal' and e.team_id = x.away_team_id))),
    away_score = (select count(*) from match_events e where e.match_id = x.id and ((e.event_type = 'goal' and e.team_id = x.away_team_id) or (e.event_type = 'own_goal' and e.team_id = x.home_team_id)))
  where x.id in (m[1], m[2]);
end $$;

-- Check: what is now recorded for Day 4
select m.match_number as match_of_day4, h.name as home, m.home_score, m.away_score, a.name as away, m.status,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'played') as played,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'rested') as rested,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'absent') as absent,
  (select count(*) from match_events e where e.match_id = m.id) as events
from matches m join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id
where m.match_day = 4 order by m.match_number;
