-- DAY 1 LINEUPS (Played / Rested / Absent) + Chirag's yellow card half.
-- Run sql/migration_attendance.sql first. Safe to re-run (replaces Day 1 lineups).
-- Every name is checked against the team's squad; if anything does not match it stops and changes nothing.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  r record; mid uuid; pid uuid; tid uuid; hid uuid; aid uuid; cnt int;
begin
  delete from match_appearances where match_id in (select id from matches where season_id = s and match_day = 1);
  for r in
    select n, team, status, who from (values
      -- Match 1: Muggles FC vs Desi Steelers FC
      (1,'Muggles FC','rested','Vishnu Mohan'),(1,'Muggles FC','absent','Ayush'),
      (1,'Muggles FC','played','Amritpal Singh'),(1,'Muggles FC','played','Preetesh Duvvuri'),(1,'Muggles FC','played','Dheeraj R Vatti'),
      (1,'Muggles FC','played','Dhruv'),(1,'Muggles FC','played','Ashu'),(1,'Muggles FC','played','Taranjot Singh Dang'),(1,'Muggles FC','played','Rohith'),
      (1,'Desi Steelers FC','rested','Vamshi'),
      (1,'Desi Steelers FC','played','Nasiq'),(1,'Desi Steelers FC','played','Ketan Shilimkar'),(1,'Desi Steelers FC','played','Vija'),
      (1,'Desi Steelers FC','played','Vignesh'),(1,'Desi Steelers FC','played','Kaushik'),(1,'Desi Steelers FC','played','Rishabh Devgon'),
      (1,'Desi Steelers FC','played','Ajinkya P'),(1,'Desi Steelers FC','played','Sagar'),
      -- Match 2: Renegades vs Scouts FC
      (2,'Renegades','rested','Vivek'),
      (2,'Renegades','played','Varun'),(2,'Renegades','played','Minti'),(2,'Renegades','played','Nuhu Okikiri'),(2,'Renegades','played','Shailesh'),
      (2,'Renegades','played','Chirag'),(2,'Renegades','played','Prajna'),(2,'Renegades','played','Sangram Ghewade'),(2,'Renegades','played','Dhananjay'),(2,'Renegades','played','Rajeev Singh'),
      (2,'Scouts FC','rested','Sandeep Naik'),
      (2,'Scouts FC','played','Bhagyesh Rane'),(2,'Scouts FC','played','Ketan Gaikwad'),(2,'Scouts FC','played','Pradnyal Gandhi'),(2,'Scouts FC','played','Kishor Ghadge'),
      (2,'Scouts FC','played','Sagar SJ'),(2,'Scouts FC','played','Kartik'),(2,'Scouts FC','played','Bilal Yaser'),(2,'Scouts FC','played','Jitendra'),
      -- Match 3: Renegades vs Desi Steelers FC
      (3,'Renegades','rested','Rajeev Singh'),
      (3,'Renegades','played','Varun'),(3,'Renegades','played','Minti'),(3,'Renegades','played','Nuhu Okikiri'),(3,'Renegades','played','Shailesh'),
      (3,'Renegades','played','Chirag'),(3,'Renegades','played','Prajna'),(3,'Renegades','played','Sangram Ghewade'),(3,'Renegades','played','Dhananjay'),(3,'Renegades','played','Vivek'),
      (3,'Desi Steelers FC','played','Nasiq'),(3,'Desi Steelers FC','played','Ketan Shilimkar'),(3,'Desi Steelers FC','played','Vija'),(3,'Desi Steelers FC','played','Vignesh'),
      (3,'Desi Steelers FC','played','Kaushik'),(3,'Desi Steelers FC','played','Rishabh Devgon'),(3,'Desi Steelers FC','played','Ajinkya P'),(3,'Desi Steelers FC','played','Sagar'),
      -- Match 4: Muggles FC vs Scouts FC
      (4,'Muggles FC','rested','Ayush'),
      (4,'Muggles FC','played','Amritpal Singh'),(4,'Muggles FC','played','Preetesh Duvvuri'),(4,'Muggles FC','played','Dheeraj R Vatti'),(4,'Muggles FC','played','Dhruv'),
      (4,'Muggles FC','played','Ashu'),(4,'Muggles FC','played','Taranjot Singh Dang'),(4,'Muggles FC','played','Rohith'),(4,'Muggles FC','played','Vishnu Mohan'),
      (4,'Scouts FC','rested','Jitendra'),
      (4,'Scouts FC','played','Bhagyesh Rane'),(4,'Scouts FC','played','Ketan Gaikwad'),(4,'Scouts FC','played','Pradnyal Gandhi'),(4,'Scouts FC','played','Kishor Ghadge'),
      (4,'Scouts FC','played','Sagar SJ'),(4,'Scouts FC','played','Kartik'),(4,'Scouts FC','played','Bilal Yaser'),(4,'Scouts FC','played','Sandeep Naik')
    ) v(n, team, status, who)
  loop
    select id, home_team_id, away_team_id into mid, hid, aid from matches where season_id = s and match_day = 1 and match_number = r.n;
    select id into tid from teams where name = r.team;
    select id into pid from players where full_name = r.who;
    if mid is null or tid is null or pid is null then raise exception 'Match %, team % or player "%" not found', r.n, r.team, r.who; end if;
    if tid <> hid and tid <> aid then raise exception 'Match %: % did not play in this match', r.n, r.team; end if;
    perform 1 from team_season_rosters where season_id = s and player_id = pid and team_id = tid;
    if not found then raise exception 'Match %: "%" is not in the % squad', r.n, r.who, r.team; end if;
    insert into match_appearances (match_id, player_id, team_id, status, started) values (mid, pid, tid, r.status, r.status = 'played');
  end loop;

  -- Chirag's yellow card was in the second half
  update match_events set half = 2
  where event_type = 'yellow_card'
    and player_id = (select id from players where full_name = 'Chirag')
    and match_id = (select id from matches where season_id = s and match_day = 1 and match_number = 3);
end $$;

select m.match_number, t.name as team,
  count(*) filter (where a.status = 'played') as played,
  count(*) filter (where a.status = 'rested') as rested,
  count(*) filter (where a.status = 'absent') as absent
from match_appearances a join matches m on m.id = a.match_id join teams t on t.id = a.team_id
where m.match_day = 1 group by m.match_number, t.name order by m.match_number, t.name;
