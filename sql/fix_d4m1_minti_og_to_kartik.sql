-- Day 4 Match 1 (Renegades v Scouts FC): the 1st-half goal at 1:50 was recorded as a Minti OWN GOAL (Renegades).
-- Owner: remove the own goal and give the goal to Kartik (Scouts FC). Same time. The score stays Renegades 0-3 Scouts FC.
-- Safe to re-run. Stops and changes nothing if the match, Kartik's lineup entry or the score does not fit.
do $$
declare
  s uuid := (select id from seasons where is_current limit 1);
  mid uuid; kid uuid; kteam uuid; n int;
begin
  select id into mid from matches where season_id = s and match_day = 4 and match_number = 1;
  select id into kid from players where full_name = 'Kartik';
  select team_id into kteam from match_appearances where match_id = mid and player_id = kid and status = 'played';
  if mid is null or kid is null or kteam is null then raise exception 'Day 4 Match 1: Kartik did not play in this match; nothing changed'; end if;
  if kteam <> (select id from teams where name = 'Scouts FC') then raise exception 'Kartik is not on Scouts FC in this match; nothing changed'; end if;
  update match_events set event_type = 'goal', player_id = kid, team_id = kteam
   where match_id = mid and event_type = 'own_goal' and player_id = (select id from players where full_name = 'Minti');
  get diagnostics n = row_count;
  if n > 1 then raise exception 'More than one Minti own goal found; nothing changed'; end if;
  -- score from the goals (own goals count for the other team); must still be 0-3
  update matches x set
    home_score = (select count(*) from match_events e where e.match_id = x.id and ((e.event_type = 'goal' and e.team_id = x.home_team_id) or (e.event_type = 'own_goal' and e.team_id = x.away_team_id))),
    away_score = (select count(*) from match_events e where e.match_id = x.id and ((e.event_type = 'goal' and e.team_id = x.away_team_id) or (e.event_type = 'own_goal' and e.team_id = x.home_team_id)))
   where x.id = mid;
  if (select home_score from matches where id = mid) <> 0 or (select away_score from matches where id = mid) <> 3 then
    raise exception 'Score is no longer Renegades 0-3 Scouts FC; nothing changed';
  end if;
end $$;

select p.full_name, t.name as team, e.event_type, e.minute, e.second, m.home_score, m.away_score
from match_events e join matches m on m.id = e.match_id join players p on p.id = e.player_id join teams t on t.id = e.team_id
where m.match_day = 4 and m.match_number = 1 and e.event_type in ('goal','own_goal','assist') order by e.minute, e.second, e.event_type;
