-- 10-minute halves: new kickoff times, US Eastern (EDT until 1 Nov, EST after; handled automatically).
--   Match 1 = 8:30 PM, Match 2 = 9:00 PM, Match 3 = 9:30 PM, Match 4 = 10:00 PM
-- Keeps each match day's existing date, only the time changes.
update matches
set kickoff_at = (
  ((kickoff_at at time zone 'America/New_York')::date
    + (case match_number when 1 then time '20:30' when 2 then time '21:00' when 3 then time '21:30' when 4 then time '22:00' end)
  ) at time zone 'America/New_York')
where kickoff_at is not null and match_number between 1 and 4;

select match_day, match_number,
  to_char(kickoff_at at time zone 'America/New_York', 'Dy DD Mon YYYY HH12:MI AM') as eastern_kickoff
from matches order by match_day, match_number;
