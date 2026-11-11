-- Day 1 Match 4 (Muggles FC v Scouts FC): Vishnu Mohan's goal was assisted by Dhruv (both Muggles FC).
-- Links the goal to the assist and adds Dhruv's assist (1st half, like the goal; Day 1 has no exact times). The score does not change.
-- Safe to re-run. Stops and changes nothing if the match, the goal or the players do not fit.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  mid uuid; vid uuid; did uuid; muggles uuid := (select id from teams where name = 'Muggles FC'); g match_events%rowtype; n int;
begin
  select id into mid from matches where season_id = s and match_day = 1 and match_number = 4;
  select id into vid from players where full_name = 'Vishnu Mohan';
  select id into did from players where full_name = 'Dhruv';
  if mid is null or vid is null or did is null or muggles is null then raise exception 'Day 1 Match 4, Vishnu Mohan, Dhruv or Muggles FC not found; nothing changed'; end if;
  perform 1 from team_season_rosters where season_id = s and team_id = muggles and player_id = did;
  if not found then raise exception 'Dhruv is not in the Muggles FC squad; nothing changed'; end if;
  select count(*) into n from match_events where match_id = mid and event_type = 'goal' and player_id = vid;
  if n <> 1 then raise exception 'Expected exactly one Vishnu Mohan goal in Day 1 Match 4, found %; nothing changed', n; end if;
  select * into g from match_events where match_id = mid and event_type = 'goal' and player_id = vid;
  update match_events set related_player_id = did where id = g.id;
  delete from match_events where match_id = mid and event_type = 'assist' and player_id = did and related_player_id = vid;
  insert into match_events (match_id, team_id, player_id, event_type, half, minute, second, time_remaining, related_player_id, is_penalty, created_at)
  values (mid, muggles, did, 'assist', g.half, g.minute, g.second, g.time_remaining, vid, false, clock_timestamp());
end $$;

select p.full_name as player, t.name as team, e.event_type, e.half, rp.full_name as related_player
from match_events e join matches m on m.id = e.match_id join players p on p.id = e.player_id join teams t on t.id = e.team_id left join players rp on rp.id = e.related_player_id
where m.match_day = 1 and m.match_number = 4 and e.event_type in ('goal','assist') order by e.half, e.event_type, p.full_name;
