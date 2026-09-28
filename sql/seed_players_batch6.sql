-- Batch 6: adds 2 new players (Varun, Ayush).

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Varun', 33, 'M', 'Forward/Winger', 'Right', 'assets/players/varun.jpg',
  'Jersey #10 (Zack) — same number as Dhananjay''s, Jitendra''s, and Dheeraj''s cards; flagged for the admin to resolve on roster assignment.',
  'High', 7, 'Advanced',
  'None', 'None', 'None', 'Forward'
),
(
  'Ayush', 39, 'L', 'Flex', 'Right', 'assets/players/ayush.jpg',
  'Jersey #15 (AJ).',
  'Medium', 6, 'Intermediate',
  'Recreational', 'None', 'Not available until Oct 15', 'Flex'
);
