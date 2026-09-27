-- Batch 5: adds 7 new players (Kaushik was uploaded twice as identical
-- files — only inserted once here). Run after all previous migration/seed
-- scripts (needs stamina_level/skill_rating/skill_level/position_category
-- columns already in place).
--
-- Also includes the fitness-notes fix for Jitendra and Minti requested in
-- the same message.

update players set fitness_notes = 'None' where full_name = 'Jitendra';
update players set fitness_notes = 'None' where full_name = 'Minti';

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Dhananjay', 36, 'M', 'Def', 'Right', 'assets/players/dhananjay.jpg',
  'Jersey #10 (DJ) — same number as Jitendra''s and Dheeraj''s cards; flagged for the admin to resolve on roster assignment.',
  'Medium', 6, 'Intermediate',
  'Recreational',
  'None',
  'None',
  'Defense'
),
(
  'Shailesh', 44, 'Adult M', 'Mid / Winger', 'Right', 'assets/players/shailesh.jpg',
  'Jersey #45 (Shailesh). Card left Skill Rating unfilled (showed the template''s blank "X/10") — recorded as no rating; Skill Level read "Intermediate". Position combo (Mid/Winger) — category recorded as Flex.',
  'Low', null, 'Intermediate',
  'Recreational',
  'Knee Pain',
  'Oct 11-18',
  'Flex'
),
(
  'Prajna', 41, 'L', 'Mid Fielder / Right Wing', 'Right', 'assets/players/prajna.jpg',
  'Jersey #99 (Prajna).',
  'Low', 6, 'Intermediate',
  'Intra College',
  'None',
  'None',
  'Flex'
),
(
  'Amritpal Singh', 30, 'Adult XL / US 42-44', 'Felx except keeper', 'Right', 'assets/players/amritpal.jpg',
  'Jersey #1 (AMRIT).',
  'Low', 7, 'Intermediate',
  'Played Competitive in College / Recreational & pick-up post college',
  'Sciatica; cannot run for longer durations due to lower back pain.',
  'None',
  'Flex'
),
(
  'Sandeep Naik', 39, 'Medium', 'Forward', 'Right', 'assets/players/sandeep-naik.jpg',
  'Jersey #777 (Sandeep) — unusual number as given on the card, kept as-is.',
  'Medium', 3, 'Beginner',
  'Beginner',
  'Hamstring/Tennis Elbow',
  'No plans',
  'Forward'
),
(
  'Ashu', 30, 'L', 'Def/Goalie/Mid', 'Both', 'assets/players/ashu.jpg',
  'Jersey #7 (Ashu) — same number as Sangram Ghewade''s, Vivek''s, and Nuhu''s cards; flagged for the admin to resolve on roster assignment.',
  'Medium', 6, 'Advanced',
  '16 years',
  'NA',
  'NA',
  'Flex'
),
(
  'Kaushik', 31, 'Adult M', 'Flex', 'Both', 'assets/players/kaushik.jpg',
  'Jersey #19 (Kaushik) — same number as Dhruv''s card (which itself listed "19 or 11"); flagged for the admin to resolve on roster assignment. Card''s name field was left as the template placeholder ("Your Full Name") — used the jersey name "Kaushik" instead; confirm full name with the player. Card''s skill rating was 6.5/10 — rounded to 7 since the column stores whole numbers. Uploaded twice as identical files — inserted once.',
  'Low', 7, 'Intermediate',
  'Intra-mural leagues',
  null,
  'Out Nov 10th onwards',
  'Flex'
);
