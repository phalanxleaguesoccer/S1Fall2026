-- Batch 3: adds 2 new players. Run after migration_player_attributes.sql
-- and seed_players_batch2.sql (same columns, no new schema changes needed).

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan
) values
(
  'Rajeev Singh', 45, 'L', 'Def', 'Right', 'assets/players/rajeev.jpg',
  'Jersey #21 (Rajeev).',
  'Medium', 2, 'Beginner',
  'Recreational',
  'None',
  'None'
),
(
  'Nasiq', 37, 'XL / 44', 'Mid/Def', 'Right', 'assets/players/nasiq.jpg',
  'Jersey #12 (Nasiq) — same number as Preetesh Duvvuri''s card; flagged for the admin to resolve on roster assignment.',
  'Low', 5, 'Intermediate',
  'Recreational',
  'None',
  'None'
);
