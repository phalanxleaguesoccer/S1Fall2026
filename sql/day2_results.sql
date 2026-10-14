-- WEEK 2 (Match Day 2 = Matches 5-8): scores, toss, lineups (played/rested/absent) and every event.
-- Run sql/migration_day2_fields.sql and sql/migration_fouls.sql FIRST.
-- Safe to re-run: it replaces everything recorded for Match Day 2.
-- Every team/player name is checked against the squads; if anything does not match it stops and changes nothing.
-- Fouls are only the ones listed below; yellow cards are recorded as cards only.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  r record; mid uuid; hid uuid; aid uuid; tid uuid; pid uuid; rid uuid; hs int; as_ int; n_ok int;
  fh int; fm int; fsec int;
begin
  -- ---------- 1. scores + toss ----------
  for r in
    select * from (values
      -- n, team1, team2, goals team1, goals team2, toss winner, toss choice
      (1,'Scouts FC','Desi Steelers FC',0,1,'Desi Steelers FC','side'),
      (2,'Renegades','Muggles FC',0,2,'Muggles FC','kickoff'),
      (3,'Scouts FC','Muggles FC',2,0,'Muggles FC','kickoff'),
      (4,'Desi Steelers FC','Renegades',0,0,'Desi Steelers FC','kickoff')
    ) v(n, t1, t2, g1, g2, toss, choice)
  loop
    select id, home_team_id, away_team_id into mid, hid, aid from matches where season_id = s and match_day = 2 and match_number = r.n;
    if mid is null then raise exception 'Match Day 2 Match % not found', r.n; end if;
    if hid = (select id from teams where name = r.t1) and aid = (select id from teams where name = r.t2) then hs := r.g1; as_ := r.g2;
    elsif hid = (select id from teams where name = r.t2) and aid = (select id from teams where name = r.t1) then hs := r.g2; as_ := r.g1;
    else raise exception 'Match Day 2 Match %: the scheduled teams are not % and %', r.n, r.t1, r.t2; end if;
    update matches set home_score = hs, away_score = as_, status = 'completed',
      toss_winner_team_id = (select id from teams where name = r.toss), toss_choice = r.choice
    where id = mid;
  end loop;

  -- ---------- 2. lineups: everyone in both squads PLAYED unless listed as rested/absent ----------
  delete from match_events where match_id in (select id from matches where season_id = s and match_day = 2);
  delete from match_appearances where match_id in (select id from matches where season_id = s and match_day = 2);
  insert into match_appearances (match_id, player_id, team_id, status, started)
  select m.id, tsr.player_id, tsr.team_id, 'played', true
  from matches m join team_season_rosters tsr on tsr.season_id = m.season_id and tsr.team_id in (m.home_team_id, m.away_team_id)
  where m.season_id = s and m.match_day = 2;

  for r in
    select * from (values
      (1,'Desi Steelers FC','rested','Ketan Shilimkar'),(1,'Scouts FC','rested','Pradnyal Gandhi'),
      (1,'Desi Steelers FC','absent','Vamshi'),(1,'Scouts FC','absent','Kishor Ghadge'),
      (2,'Muggles FC','rested','Preetesh Duvvuri'),(2,'Renegades','rested','Shailesh'),
      (2,'Muggles FC','absent','Ashu'),
      (3,'Muggles FC','rested','Ashu'),(3,'Scouts FC','rested','Kishor Ghadge'),
      (3,'Muggles FC','absent','Preetesh Duvvuri'),
      (4,'Renegades','absent','Shailesh'),(4,'Desi Steelers FC','absent','Vamshi')
    ) v(n, team, status, who)
  loop
    select id into mid from matches where season_id = s and match_day = 2 and match_number = r.n;
    select id into tid from teams where name = r.team;
    select id into pid from players where full_name = r.who;
    if tid is null or pid is null then raise exception 'Match %: team % or player "%" not found', r.n, r.team, r.who; end if;
    update match_appearances set status = r.status, started = false where match_id = mid and team_id = tid and player_id = pid;
    get diagnostics n_ok = row_count;
    if n_ok <> 1 then raise exception 'Match %: "%" is not in the % squad (or % did not play)', r.n, r.who, r.team, r.team; end if;
  end loop;

  -- ---------- 3. events (entered in this order) ----------
  -- n, team (the player's own team), player, type, half, minute, second, related player, penalty
  for r in
    select * from (values
      -- Match 5: Scouts FC 0-1 Desi Steelers FC (own goal by Sagar SJ; assist Rishabh Devgon)
      (1,'Scouts FC','Kartik','yellow_card',1,7,null::int,null::text,false),
      (1,'Scouts FC','Sagar SJ','own_goal',1,8,20,'Rishabh Devgon',false),
      (1,'Desi Steelers FC','Rishabh Devgon','assist',1,8,20,'Sagar SJ',false),
      (1,'Desi Steelers FC','Rishabh Devgon','player_of_match',null::int,null::int,null::int,null::text,false),
      -- Match 6: Renegades 0-2 Muggles FC
      (2,'Renegades','Varun','yellow_card',2,15,2,null,false),
      (2,'Muggles FC','Dhruv','goal',2,16,32,null,true),
      (2,'Muggles FC','Amritpal Singh','goal',2,18,null,null,false),
      (2,'Muggles FC','Dhruv','player_of_match',null,null,null,null,false),
      -- Match 7: Scouts FC 2-0 Muggles FC
      (3,'Scouts FC','Pradnyal Gandhi','goal',1,7,1,null,true),
      (3,'Muggles FC','Dheeraj R Vatti','yellow_card',1,7,18,null,false),
      (3,'Scouts FC','Kartik','goal',1,8,15,null,false),
      (3,'Scouts FC','Bilal Yaser','foul',2,18,50,null,false),
      (3,'Scouts FC','Pradnyal Gandhi','player_of_match',null,null,null,null,false),
      -- Match 8: Desi Steelers FC 0-0 Renegades
      (4,'Renegades','Chirag','foul',1,8,null,null,false),
      (4,'Renegades','Varun','foul',1,9,6,null,false),
      (4,'Desi Steelers FC','Nasiq','yellow_card',2,16,2,null,false),
      (4,'Desi Steelers FC','Rishabh Devgon','yellow_card',2,19,57,null,false),
      (4,'Desi Steelers FC','Vija','player_of_match',null,null,null,null,false)
    ) v(n, team, who, typ, half, minute, second, rel, pen)
  loop
    select id into mid from matches where season_id = s and match_day = 2 and match_number = r.n;
    select id into tid from teams where name = r.team;
    select id into pid from players where full_name = r.who;
    if tid is null or pid is null then raise exception 'Match %: team % or player "%" not found', r.n, r.team, r.who; end if;
    perform 1 from team_season_rosters where season_id = s and player_id = pid and team_id = tid;
    if not found then raise exception 'Match %: "%" is not in the % squad', r.n, r.who, r.team; end if;
    rid := null;
    if r.rel is not null then
      select id into rid from players where full_name = r.rel;
      if rid is null then raise exception 'Match %: player "%" not found', r.n, r.rel; end if;
    end if;
    -- Own goal: team_id = the scorer's OWN team. A yellow card is NOT counted as a foul; fouls are listed separately.
    insert into match_events (match_id, team_id, player_id, event_type, half, minute, second, related_player_id, is_penalty, created_at)
    values (mid, tid, pid, r.typ, r.half, r.minute, r.second, rid, r.pen, clock_timestamp());
  end loop;
end $$;

-- Check: results and event counts for Match Day 2
select m.match_number, h.name as team_1, m.home_score as team_1_goals, m.away_score as team_2_goals, a.name as team_2, m.status,
  (select name from teams where id = m.toss_winner_team_id) as toss_won_by, m.toss_choice,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'played') as played,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'rested') as rested,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'absent') as absent,
  (select count(*) from match_events e where e.match_id = m.id) as events
from matches m join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id
where m.match_day = 2 order by m.match_number;
