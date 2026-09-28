-- Batch 7: adds 1 new player (Bhagyesh Rane).
--
-- Card left Jersey Size / Name on Jersey / Player # as unfilled template
-- placeholders — left null per admin's instruction, to be filled once he
-- provides them. Skill Level card literally listed all 3 options
-- unselected ("Beginner / Inter. / Advanced") — set to Advanced per admin.
-- Stamina was given as "6/10" (not a Low/Med/High label like other cards) —
-- mapped to Medium as the closest match on that 1-10 scale.

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Bhagyesh Rane', 34, null, 'Defense', 'Right', 'assets/players/bhagyesh.jpg',
  'Jersey size, jersey name, and player # left blank on the card (template placeholders) — to be confirmed with the player before roster assignment.',
  'Medium', 7, 'Advanced',
  '14+ years', 'NA', 'None', 'Defense'
);
