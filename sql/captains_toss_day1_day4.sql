-- Day 1 captains (Matches 1-4) + Day 4 toss and captains (Day 4 Match 1-4 = Matches 13-16). Owner dictated.
-- If a Day 1 match has no lineup at all, the two captains are added as 'played' (they did play); other Day 1 players stay unrecorded until a lineup is entered.
-- Safe to re-run. Touches ONLY these 8 matches (Days 2, 3 and 5 are left alone). Stops and changes nothing if a name, team or lineup entry does not fit.
-- "Sagar Awate" = the player "Sagar" (Desi Steelers FC): there is no "Awate" in the database.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  r record; mid uuid; tid uuid; pid uuid; n_ok int; mids uuid[] := '{}';
begin
  -- toss (Day 4): match, toss winner, choice
  for r in select * from (values
      (4,1,'Renegades','kickoff'),(4,2,'Muggles FC','side'),(4,3,'Renegades','kickoff'),(4,4,'Muggles FC','kickoff')) v(d, n, team, choice)
  loop
    select id into mid from matches where season_id = s and match_day = r.d and match_number = r.n;
    select id into tid from teams where name = r.team;
    if mid is null or tid is null then raise exception 'Day % Match %: match or team % not found', r.d, r.n, r.team; end if;
    perform 1 from matches where id = mid and tid in (home_team_id, away_team_id);
    if not found then raise exception 'Day % Match %: % is not playing in this match', r.d, r.n, r.team; end if;
    update matches set toss_winner_team_id = tid, toss_choice = r.choice where id = mid;
  end loop;

  -- captains: clear the 8 matches, then set one per team
  for r in select d, n from (values (1,1),(1,2),(1,3),(1,4),(4,1),(4,2),(4,3),(4,4)) v(d, n) loop
    select id into mid from matches where season_id = s and match_day = r.d and match_number = r.n;
    if mid is null then raise exception 'Day % Match % not found', r.d, r.n; end if;
    mids := array_append(mids, mid);
  end loop;
  update match_appearances set is_captain = false, captain_stand_in = false where match_id = any(mids);

  for r in select * from (values
      (1,1,'Amritpal Singh'),(1,1,'Nasiq'),
      (1,2,'Varun'),(1,2,'Pradnyal Gandhi'),
      (1,3,'Varun'),(1,3,'Nasiq'),
      (1,4,'Amritpal Singh'),(1,4,'Pradnyal Gandhi'),
      (4,1,'Dhananjay'),(4,1,'Pradnyal Gandhi'),
      (4,2,'Dhruv'),(4,2,'Sagar'),
      (4,3,'Sagar'),(4,3,'Dhananjay'),
      (4,4,'Amritpal Singh'),(4,4,'Pradnyal Gandhi')) v(d, n, who)
  loop
    select id into mid from matches where season_id = s and match_day = r.d and match_number = r.n;
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Player "%" not found', r.who; end if;
    update match_appearances set is_captain = true, captain_stand_in = false
      where match_id = mid and player_id = pid and status = 'played';
    get diagnostics n_ok = row_count;
    if n_ok = 0 then
      if exists (select 1 from match_appearances where match_id = mid and player_id = pid) then
        raise exception 'Day % Match %: "%" is in the lineup but not as PLAYED (rested/absent)', r.d, r.n, r.who;
      end if;
      -- no lineup was recorded for this match (Day 1): add the captain as played, in his squad's team for this match
      insert into match_appearances (match_id, player_id, team_id, started, status, is_captain)
        select mid, pid, ro.team_id, true, 'played', true from team_season_rosters ro join matches mx on mx.id = mid
        where ro.season_id = s and ro.player_id = pid and ro.team_id in (mx.home_team_id, mx.away_team_id);
      get diagnostics n_ok = row_count;
      if n_ok <> 1 then raise exception 'Day % Match %: "%" is not in a squad of the two teams playing', r.d, r.n, r.who; end if;
      raise notice 'Day % Match %: no lineup existed, added % as played captain', r.d, r.n, r.who;
    end if;
  end loop;
end $$;

-- check: should list 2 captains for each of the 8 matches, and the toss for Day 4
select m.match_day, m.match_number, t.name as team, p.full_name as captain
from match_appearances ma join matches m on m.id = ma.match_id join teams t on t.id = ma.team_id join players p on p.id = ma.player_id
where ma.is_captain and m.match_day in (1, 4) order by m.match_day, m.match_number, t.name;
select m.match_day, m.match_number, tw.name as toss_won_by, m.toss_choice
from matches m left join teams tw on tw.id = m.toss_winner_team_id where m.match_day = 4 order by m.match_number;
