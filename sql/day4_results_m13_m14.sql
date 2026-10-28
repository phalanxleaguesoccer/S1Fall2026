-- MATCH DAY 4, MATCH 13 (Scouts FC vs Renegades) and MATCH 14: lineups (rested), goals, assists, own goal, yellow card, player of the match.
-- Times were given as TIME REMAINING in the half; this converts them (1st half: played = 10:00 - remaining; 2nd half: played = 10:00 + (10:00 - remaining)).
-- Safe to re-run: it REPLACES whatever is recorded for these two matches. Needs migration_live_scoring.sql (time_remaining column) already run.
-- Teams are taken from each player's current squad. If a name or team does not fit, it stops and changes nothing.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  r record; mid uuid; tid uuid; pid uuid; rid uuid; ptid uuid; n_ok int; el int; rem int;
  m13 uuid; m14 uuid;
begin
  select id into m13 from matches where season_id = s and match_day = 4 and match_number = 1;
  select id into m14 from matches where season_id = s and match_day = 4 and match_number = 2;
  if m13 is null or m14 is null then raise exception 'Match Day 4 Match 1 or 2 not found'; end if;
  -- Match 13 must be Scouts FC vs Renegades (either way round)
  perform 1 from matches m join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id
   where m.id = m13 and ((h.name = 'Scouts FC' and a.name = 'Renegades') or (h.name = 'Renegades' and a.name = 'Scouts FC'));
  if not found then raise exception 'Match Day 4 Match 1 is not Scouts FC vs Renegades; check which match number this is'; end if;

  -- ---------- 1. start clean for these two matches, then everybody in both squads PLAYED ----------
  delete from match_events where match_id in (m13, m14);
  delete from match_appearances where match_id in (m13, m14);
  insert into match_appearances (match_id, player_id, team_id, status, started)
  select m.id, tsr.player_id, tsr.team_id, 'played', true
  from matches m join team_season_rosters tsr on tsr.season_id = m.season_id and tsr.team_id in (m.home_team_id, m.away_team_id)
  where m.id in (m13, m14);

  -- ---------- 2. rested ----------
  for r in select * from (values (13,'Nuhu Okikiri'),(13,'Bilal Yaser'),(14,'Amritpal Singh'),(14,'Vija')) v(n, who)
  loop
    mid := case r.n when 13 then m13 else m14 end;
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Player "%" not found', r.who; end if;
    update match_appearances set status = 'rested', started = false where match_id = mid and player_id = pid;
    get diagnostics n_ok = row_count;
    if n_ok <> 1 then raise exception 'Match %: "%" is not in either squad of this match', r.n, r.who; end if;
  end loop;

  -- ---------- 3. events (in the order given). half, time REMAINING in seconds, related player (assist: the scorer; goal: the assister) ----------
  for r in
    select * from (values
      -- Match 13: Scouts FC vs Renegades
      (13,'Minti','own_goal',1, 8*60+10, null::text),      -- own goal: counts for the other side
      (13,'Sagar SJ','goal',1, 6*60+52, 'Pradnyal Gandhi'),
      (13,'Pradnyal Gandhi','assist',1, 6*60+52, 'Sagar SJ'),
      (13,'Bhagyesh Rane','goal',2, 0*60+20, 'Pradnyal Gandhi'),
      (13,'Pradnyal Gandhi','assist',2, 0*60+20, 'Bhagyesh Rane'),
      (13,'Bhagyesh Rane','player_of_match',null, null, null),
      -- Match 14
      (14,'Dhruv','goal',1, 8*60+18, 'Vishnu Mohan'),
      (14,'Vishnu Mohan','assist',1, 8*60+18, 'Dhruv'),
      (14,'Rishabh Devgon','yellow_card',1, 4*60+15, null),
      (14,'Vishnu Mohan','goal',1, 4*60+10, null),
      (14,'Dhruv','goal',2, 8*60+58, null),
      (14,'Nasiq','goal',2, 6*60+30, null)
    ) v(n, who, typ, half, remaining, rel)
  loop
    mid := case r.n when 13 then m13 else m14 end;
    select id into pid from players where full_name = r.who;
    if pid is null then raise exception 'Match %: player "%" not found', r.n, r.who; end if;
    select team_id into tid from team_season_rosters where season_id = s and player_id = pid limit 1;
    perform 1 from matches where id = mid and tid in (home_team_id, away_team_id);
    if tid is null or not found then raise exception 'Match %: "%" is not in a team playing this match', r.n, r.who; end if;
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

  -- ---------- 4. final scores come from the goals (own goals count for the other team) ----------
  update matches m set status = 'completed', live_phase = null, clock_running = false,
    home_score = (select count(*) from match_events e where e.match_id = m.id and ((e.event_type = 'goal' and e.team_id = m.home_team_id) or (e.event_type = 'own_goal' and e.team_id = m.away_team_id))),
    away_score = (select count(*) from match_events e where e.match_id = m.id and ((e.event_type = 'goal' and e.team_id = m.away_team_id) or (e.event_type = 'own_goal' and e.team_id = m.home_team_id)))
  where m.id in (m13, m14);
end $$;

-- Check: what is now recorded
select m.match_number as match_of_day4, h.name as home, m.home_score, m.away_score, a.name as away, m.status,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'played') as played,
  (select count(*) from match_appearances x where x.match_id = m.id and x.status = 'rested') as rested,
  (select count(*) from match_events e where e.match_id = m.id) as events
from matches m join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id
where m.match_day = 4 and m.match_number in (1, 2) order by m.match_number;
