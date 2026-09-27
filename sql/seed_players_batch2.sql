-- Batch 2: adds 17 new players extracted from their PowerPoint/PDF profile
-- cards. Run migration_player_attributes.sql FIRST (adds the columns this
-- insert writes to).
--
-- Skipped on purpose (already in the database from batch 1, same person,
-- just a resubmitted/updated file) — NOT re-inserted here to avoid duplicates:
--   - Minti                (2 copies uploaded again — same person)
--   - Ketan Shilimkar       (uploaded again as "White Font Adjusted Pic" — same person)
--   - Preetesh Duvvuri      (uploaded again as "Final" — same person)
--
-- Note: "Ketan Gaikwad" below is a DIFFERENT person from "Ketan Shilimkar"
-- already in the database — both are kept, distinguished by full name.
-- Note: "Sagar SJ" and "Sagar" are two different people (different age,
-- position, jersey #) — both kept.
--
-- Jersey numbers are entered here directly on the player record for
-- reference, but the number that actually counts is the one you set on the
-- Season Roster assignment once the auction happens (same as batch 1).

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan
) values
(
  'Rohith', 39, 'XL', 'Mid-field/Defence', 'Right', 'assets/players/rohith.jpg',
  'Jersey #08 (Rohith).',
  'Medium', 7, 'Intermediate',
  'University player/Corporate tournament/Recreational/League tournaments',
  null,
  'Might have unplanned business trips'
),
(
  'Sangram Ghewade', 34, 'M', 'Defender / Right Wing', 'Right', 'assets/players/sangram.jpg',
  'Jersey #7 (Sangram). Skill level on card read "Medium" — recorded as Intermediate, closest standard tier.',
  'Medium', 7, 'Intermediate',
  'College Football/Recreation',
  'None',
  'Unavailable from Nov 1'
),
(
  'Taranjot Singh Dang', 26, 'Adult M', 'LM/CDM/CM/Wing/LB', 'Right', 'assets/players/taranjot.jpg',
  'Jersey #17 (T DANG). Card stamina read "Med-high" — recorded as Medium.',
  'Medium', 6, 'Intermediate',
  'Local leagues',
  'NA',
  '15-18 October'
),
(
  'Jitendra', 45, 'M', 'Fwd', 'Right', 'assets/players/jitendra.jpg',
  'Jersey #10 (Ronaldo).',
  'Low', 4, 'Beginner',
  '3 years',
  'Good',
  'None'
),
(
  'Vivek', 36, 'US M', 'Forward / Defense', 'Right', 'assets/players/vivek.jpg',
  'Jersey #7 (Vivek). Card had two different skill-rating numbers (5/10 and 6/10) in different spots — recorded as 5/10.',
  'Medium', 5, 'Intermediate',
  'Mostly recreational',
  'NA',
  'No plans yet'
),
(
  'Sagar SJ', 40, 'US (M)', 'Winger', 'Right', 'assets/players/sagar-sj.jpg',
  'Jersey #20 (Sagar SJ).',
  'Medium', 6, 'Intermediate',
  'Mostly recreational',
  'None',
  'None'
),
(
  'Vignesh', 36, 'Adult – Small (US)', 'Goalkeeper', 'Right', 'assets/players/vignesh.jpeg',
  'Jersey #4 (Vignesh).',
  'Medium', 7, 'Intermediate',
  'Recreational. Good reflex action, has been doing goalkeeping for many years.',
  'Ankle injury history. Limits himself to fulltime goalkeeping; can switch to defense/midfield temporarily if a player is tired.',
  'Might need to go on business travel at short notice. Will try to make alternate travel plans, but customer meetings may not be flexible.'
),
(
  'Vija', 35, 'XL', 'Mid/Def', 'Right', 'assets/players/vija.jpg',
  'Jersey #18 (Vija).',
  'Low', 3, 'Beginner',
  'Recreational',
  'NA',
  'NA'
),
(
  'Kishor Ghadge', 37, 'Medium (US)', 'Mid / Wing', 'Right', 'assets/players/kishor.jpg',
  'Jersey #18 (Kish) — same number as Vija''s card; flagged for the admin to resolve on roster assignment. Card skill level read "Basic" — recorded as Beginner.',
  'Medium', 3, 'Beginner',
  'Just started playing.',
  'NA',
  'NA'
),
(
  'Vamshi', 32, 'M', 'Mid / Winger', 'Right', 'assets/players/vamshi.jpg',
  'No jersey number given on card.',
  'Medium', 6, 'Intermediate',
  'College football / recreation',
  null,
  null
),
(
  'Pradnyal Gandhi', 28, 'M', 'Flex, prefer Mid', 'Right', 'assets/players/pradnyal.jpeg',
  'Jersey #10 / 8 (Pradnyal) — two numbers given on card; flagged for the admin to pick one on roster assignment.',
  'High', 8, 'Advanced',
  'College team, intramural leagues, pickup soccer',
  null,
  'Oct 8 - 13'
),
(
  'Vishnu Mohan', 37, 'Adult M', 'Prefer Mid / Wing', 'Right', 'assets/players/vishnu.jpg',
  'Jersey #10/18 (Vishnu) — two numbers given on card; flagged for the admin to pick one on roster assignment.',
  'Medium', 7, 'Advanced',
  'Been playing soccer since college; played for college team, corporate tournaments and pickup soccer',
  'NA',
  'Oct 9-12; Nov 11-14'
),
(
  'Sagar', 33, 'US M', 'Forward / Defence', 'Right', 'assets/players/sagar.jpg',
  'No jersey number given on card. Distinct person from "Sagar SJ" (different age/position/card).',
  'Medium', 6, 'Intermediate',
  'Mostly recreational',
  'NA',
  'No plans yet'
),
(
  'Ketan Gaikwad', 33, 'Adult L', 'Defence', 'Right', 'assets/players/ketan-gaikwad.jpg',
  'Jersey #05. Distinct person from "Ketan Shilimkar" already on file. Card stamina read "Average" — recorded as Medium.',
  'Medium', 3, 'Beginner',
  'School-level experience; last played about 15 years ago.',
  'None',
  'None known'
),
(
  'Dheeraj R Vatti', 37, 'Large', 'Mid', 'Right', 'assets/players/dheeraj.jpg',
  'Jersey #10 (Dheeraj).',
  'Medium', 7, 'Intermediate',
  'College Football and Recreational games post-college',
  null,
  'None'
),
(
  'Kartik', 39, 'Adult M', 'Mid', 'Both', 'assets/players/kartik.jpg',
  'Jersey #8 (Kartik). Card''s name field was left as the template placeholder ("Your Full Name") — used the jersey name "Kartik" instead; confirm full name with the player.',
  'Medium', 7, 'Advanced',
  '32 years played — school, college, company, club and recreational for the last 6 years',
  null,
  'Last minute business related travel'
),
(
  'Nuhu Okikiri', 38, 'Adult M', 'Left Wing/Right Wing', 'Right', 'assets/players/nuhu.jpg',
  'Jersey #7 (Nuhu).',
  'Medium', 7, 'Intermediate',
  '2 years - non consistent',
  'Minor ankle injury',
  'N/A'
);
