-- Sets the match date for each match day (all Tuesdays).
-- Time-of-day is left as a placeholder (12:00 PM Eastern) since exact kickoff
-- times per match weren't given — adjust per-match via the admin dashboard
-- (Matches tab) once times are locked in.

update matches set kickoff_at = '2026-10-06 12:00:00-04' where match_day = 1;
update matches set kickoff_at = '2026-10-13 12:00:00-04' where match_day = 2;
update matches set kickoff_at = '2026-10-20 12:00:00-04' where match_day = 3;
update matches set kickoff_at = '2026-10-27 12:00:00-04' where match_day = 4;
update matches set kickoff_at = '2026-11-03 12:00:00-05' where match_day = 5;
update matches set kickoff_at = '2026-11-10 12:00:00-05' where match_day = 6;
