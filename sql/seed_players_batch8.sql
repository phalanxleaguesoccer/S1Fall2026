-- Batch 8: adds 1 new player (Bilal Yaser).
--
-- Card notes: jersey number given as "11 or 8" (two options) — both clash with
-- other cards (#11: Dhruv's "19 or 11"; #8: Pradnyal's "10 or 8"), flagged for
-- the admin to resolve on roster assignment. Position "Mid (CAM)" (attacking
-- midfielder) categorized as Center, matching how other midfielders are
-- categorized. Skill level "Inter." recorded as Intermediate. The small
-- "7/10" badge on the photo matches the 7/10 skill rating. Full name taken
-- from the file name (card only says "Bilal").

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Bilal Yaser', 31, 'M', 'Mid (CAM)', 'Right', 'assets/players/bilal.jpg',
  'Jersey name "Bilal"; number given as "11 or 8" — #11 also on Dhruv''s card and #8 also on Pradnyal''s; flagged for the admin to resolve on roster assignment.',
  'Low', 7, 'Intermediate',
  'Played college tournaments and recreational', 'None', 'None',
  'Center'
);
