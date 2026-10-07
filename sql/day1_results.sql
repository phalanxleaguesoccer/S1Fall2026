-- DAY 1 RESULTS.  Run STEP 1 now (updates the standings). Run STEP 2 when you want goals/assists/cards/POTM on player stats.
-- Needs sql/migration_map_schedule_teams.sql to have been run first (so matches use the real team names).

-- ===================== STEP 1: scores + completed (standings update automatically) =====================
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  r record; mid uuid; hid uuid; aid uuid;
begin
  for r in select * from (values
    (1, 'Muggles FC',      'Desi Steelers FC', 0, 0),   -- Match 1
    (2, 'Renegades',       'Scouts FC',        0, 0),   -- Match 2
    (3, 'Renegades',       'Desi Steelers FC', 0, 0),   -- Match 3
    (4, 'Muggles FC',      'Scouts FC',        1, 2)    -- Match 4: Scouts won 2-1
  ) v(n, team1, team2, g1, g2)
  loop
    select m.id, m.home_team_id, m.away_team_id into mid, hid, aid
    from matches m where m.season_id = s and m.match_day = 1 and m.match_number = r.n;
    if mid is null then raise exception 'Day 1 match % not found', r.n; end if;
    if not ((hid = (select id from teams where name = r.team1) and aid = (select id from teams where name = r.team2))
         or (hid = (select id from teams where name = r.team2) and aid = (select id from teams where name = r.team1))) then
      raise exception 'Day 1 match % is not % vs % in the schedule - nothing changed for it', r.n, r.team1, r.team2;
    end if;
    update matches set status = 'completed',
      home_score = case when hid = (select id from teams where name = r.team1) then r.g1 else r.g2 end,
      away_score = case when hid = (select id from teams where name = r.team1) then r.g2 else r.g1 end
    where id = mid;
  end loop;
end $$;

select m.match_number, h.name as home, m.home_score, m.away_score, a.name as away, m.status
from matches m join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id
where m.match_day = 1 order by m.match_number;

-- ===================== STEP 2: player events (goals, assists, yellow card, player of the match) =====================
-- Team of each player is taken from the current season's squads. Minutes are not recorded.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  ev record; mid uuid; pid uuid; tid uuid; rid uuid;
begin
  delete from match_events where match_id in (select id from matches where season_id = s and match_day = 1);
  for ev in select * from (values
    (1, 'player_of_match', 'Dhruv',          null),
    (2, 'player_of_match', 'Kartik',         null),
    (3, 'player_of_match', 'Nuhu Okikiri',   null),
    (3, 'yellow_card',     'Chirag',         null),
    (4, 'player_of_match', 'Bhagyesh Rane',  null),
    (4, 'goal',            'Vishnu Mohan',   null),             -- Muggles FC
    (4, 'goal',            'Bhagyesh Rane',  'Kartik'),         -- Scouts FC (assist: Kartik)
    (4, 'assist',          'Kartik',         null),
    (4, 'goal',            'Bilal Yaser',    'Pradnyal Gandhi'),-- Scouts FC (assist: Pradnyal)
    (4, 'assist',          'Pradnyal Gandhi',null)
  ) v(n, typ, who, assist_by)
  loop
    select id into mid from matches where season_id = s and match_day = 1 and match_number = ev.n;
    select id into pid from players where full_name = ev.who;
    select team_id into tid from team_season_rosters where season_id = s and player_id = pid;
    if mid is null or pid is null or tid is null then raise exception 'Cannot resolve match %, player % or his team', ev.n, ev.who; end if;
    rid := null;
    if ev.assist_by is not null then select id into rid from players where full_name = ev.assist_by; end if;
    insert into match_events (match_id, team_id, player_id, event_type, half, related_player_id)
    values (mid, tid, pid, ev.typ, 1, rid);
  end loop;
end $$;

select m.match_number, e.event_type, p.full_name, t.name as team
from match_events e join matches m on m.id = e.match_id join players p on p.id = e.player_id join teams t on t.id = e.team_id
where m.match_day = 1 order by m.match_number, e.event_type;
