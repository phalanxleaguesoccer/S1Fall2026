-- Sets kickoff time-of-day for every match, based on match_number, on top of
-- the dates already set in update_match_dates.sql (Day 1-6 = the Tuesdays
-- Oct 6 - Nov 10, 2026). Same time slots apply on every match day:
--   Match 1: 9:00 PM Eastern
--   Match 2: 9:25 PM Eastern
--   Match 3: 9:50 PM Eastern
--   Match 4: 10:15 PM Eastern
-- (Offset is -04 for Oct dates during Eastern Daylight Time, -05 for the
-- Nov 3 and Nov 10 dates once EDT ends; both represent the same "9:00 PM
-- Eastern" wall-clock time.)

update matches set kickoff_at = '2026-10-06 21:00:00-04' where match_day = 1 and match_number = 1;
update matches set kickoff_at = '2026-10-06 21:25:00-04' where match_day = 1 and match_number = 2;
update matches set kickoff_at = '2026-10-06 21:50:00-04' where match_day = 1 and match_number = 3;
update matches set kickoff_at = '2026-10-06 22:15:00-04' where match_day = 1 and match_number = 4;

update matches set kickoff_at = '2026-10-13 21:00:00-04' where match_day = 2 and match_number = 1;
update matches set kickoff_at = '2026-10-13 21:25:00-04' where match_day = 2 and match_number = 2;
update matches set kickoff_at = '2026-10-13 21:50:00-04' where match_day = 2 and match_number = 3;
update matches set kickoff_at = '2026-10-13 22:15:00-04' where match_day = 2 and match_number = 4;

update matches set kickoff_at = '2026-10-20 21:00:00-04' where match_day = 3 and match_number = 1;
update matches set kickoff_at = '2026-10-20 21:25:00-04' where match_day = 3 and match_number = 2;
update matches set kickoff_at = '2026-10-20 21:50:00-04' where match_day = 3 and match_number = 3;
update matches set kickoff_at = '2026-10-20 22:15:00-04' where match_day = 3 and match_number = 4;

update matches set kickoff_at = '2026-10-27 21:00:00-04' where match_day = 4 and match_number = 1;
update matches set kickoff_at = '2026-10-27 21:25:00-04' where match_day = 4 and match_number = 2;
update matches set kickoff_at = '2026-10-27 21:50:00-04' where match_day = 4 and match_number = 3;
update matches set kickoff_at = '2026-10-27 22:15:00-04' where match_day = 4 and match_number = 4;

update matches set kickoff_at = '2026-11-03 21:00:00-05' where match_day = 5 and match_number = 1;
update matches set kickoff_at = '2026-11-03 21:25:00-05' where match_day = 5 and match_number = 2;
update matches set kickoff_at = '2026-11-03 21:50:00-05' where match_day = 5 and match_number = 3;
update matches set kickoff_at = '2026-11-03 22:15:00-05' where match_day = 5 and match_number = 4;

update matches set kickoff_at = '2026-11-10 21:00:00-05' where match_day = 6 and match_number = 1;
update matches set kickoff_at = '2026-11-10 21:25:00-05' where match_day = 6 and match_number = 2;
update matches set kickoff_at = '2026-11-10 21:50:00-05' where match_day = 6 and match_number = 3;
update matches set kickoff_at = '2026-11-10 22:15:00-05' where match_day = 6 and match_number = 4;
