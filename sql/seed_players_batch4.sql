-- Batch 4: adds 2 new players. Run after migration_player_attributes.sql,
-- seed_players_batch2.sql, seed_players_batch3.sql, and
-- migration_position_categories.sql (uses the position_category column).

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Chirag', 35, 'XL', 'Center Back / Defense', 'Left', 'assets/players/chirag.jpg',
  'Jersey #14 (Chirag).',
  'Medium', 7, 'Intermediate',
  'Amateur leagues',
  'Blossoming beer belly',
  'None',
  'Defense'
),
(
  'Dhruv', 30, 'Adult M', 'Mid / Flex', 'Right', 'assets/players/dhruv.jpg',
  'Jersey #19 or #11 (Dhruv) — two numbers given on card; flagged for the admin to pick one on roster assignment. Card''s name field was left as the template placeholder ("Your Full Name") — used the jersey name "Dhruv" instead; confirm full name with the player.',
  'Medium', 8, 'Advanced',
  'School & College Teams, Corporate Leagues and Pick-Up Soccer',
  'N/A',
  'Work Travel – no specific dates yet',
  'Flex'
);
