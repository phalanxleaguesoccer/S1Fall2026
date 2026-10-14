-- A yellow/red card is NOT a foul. Removes the foul rows that were created automatically alongside cards
-- (the back-fill in migration_fouls.sql and the card+foul pairs from the first day2_results.sql).
-- Only fouls that sit right next to a card (same match, player, half, time, entered within 5 seconds before it)
-- are removed; fouls you recorded on their own are untouched. Safe to run twice.
delete from match_events f
using match_events c
where f.event_type = 'foul'
  and c.event_type in ('yellow_card', 'red_card')
  and c.match_id = f.match_id and c.player_id = f.player_id
  and c.half is not distinct from f.half
  and c.minute is not distinct from f.minute
  and c.second is not distinct from f.second
  and f.created_at <= c.created_at
  and c.created_at - f.created_at <= interval '5 seconds';

select count(*) filter (where event_type = 'foul') as fouls_left, count(*) filter (where event_type = 'yellow_card') as yellows, count(*) filter (where event_type = 'red_card') as reds from match_events;
