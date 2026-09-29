insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Rishabh Devgon', 26, 'M', 'Mid', 'Right', 'assets/players/rishabh.jpg',
  'Jersey name "RISHABH", #42 (no conflicts with other cards). Skill rating given as 6.9/10; stored as 7 (the column is a whole number).',
  'Medium', 7, 'Advanced',
  '20 years of playing experience; IIIT Delhi varsity team, Delhi', 'None', 'None',
  'Center'
);
