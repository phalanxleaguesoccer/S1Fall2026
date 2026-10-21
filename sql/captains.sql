-- Captains for Match Days 1-3 (Matches 1-12).
-- Run sql/migration_captains.sql FIRST. Safe to re-run. Re-run this file after re-running any day*_results.sql
-- (those rebuild the lineups and clear captain flags).
-- Stand-ins: Match 5 Bhagyesh Rane for Pradnyal (rested), Match 9 Vija for Nasiq (rested).
-- Chirag replaced Varun as Renegades captain from Match Day 3 (first captain change of the league).
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  r record; mid uuid; tid uuid; pid uuid; n_ok int;
begin
  update match_appearances set is_captain = false, captain_stand_in = false
  where match_id in (select id from matches where season_id = s);
  for r in
    select * from (values
      -- day, match, team, captain, stand-in?
      (1,1,'Muggles FC','Amritpal Singh',false),(1,1,'Desi Steelers FC','Nasiq',false),
      (1,2,'Renegades','Varun',false),(1,2,'Scouts FC','Pradnyal Gandhi',false),
      (1,3,'Renegades','Varun',false),(1,3,'Desi Steelers FC','Nasiq',false),
      (1,4,'Muggles FC','Amritpal Singh',false),(1,4,'Scouts FC','Pradnyal Gandhi',false),
      (2,1,'Scouts FC','Bhagyesh Rane',true),(2,1,'Desi Steelers FC','Nasiq',false),
      (2,2,'Renegades','Varun',false),(2,2,'Muggles FC','Amritpal Singh',false),
      (2,3,'Scouts FC','Pradnyal Gandhi',false),(2,3,'Muggles FC','Amritpal Singh',false),
      (2,4,'Desi Steelers FC','Nasiq',false),(2,4,'Renegades','Varun',false),
      (3,1,'Muggles FC','Amritpal Singh',false),(3,1,'Desi Steelers FC','Vija',true),
      (3,2,'Renegades','Chirag',false),(3,2,'Scouts FC','Pradnyal Gandhi',false),
      (3,3,'Desi Steelers FC','Nasiq',false),(3,3,'Scouts FC','Pradnyal Gandhi',false),
      (3,4,'Muggles FC','Amritpal Singh',false),(3,4,'Renegades','Chirag',false)
    ) v(d, n, team, who, stand)
  loop
    select id into mid from matches where season_id = s and match_day = r.d and match_number = r.n;
    select id into tid from teams where name = r.team;
    select id into pid from players where full_name = r.who;
    if mid is null or tid is null or pid is null then raise exception 'Day % Match %: match, team % or player "%" not found', r.d, r.n, r.team, r.who; end if;
    update match_appearances set is_captain = true, captain_stand_in = r.stand where match_id = mid and team_id = tid and player_id = pid;
    get diagnostics n_ok = row_count;
    if n_ok <> 1 then raise exception 'Day % Match %: "%" has no lineup entry for %', r.d, r.n, r.who, r.team; end if;
  end loop;
end $$;

select m.match_day, m.match_number, t.name as team, p.full_name as captain, ma.captain_stand_in as stand_in, ma.status
from match_appearances ma join matches m on m.id = ma.match_id join teams t on t.id = ma.team_id join players p on p.id = ma.player_id
where ma.is_captain order by m.match_day, m.match_number, t.name;
