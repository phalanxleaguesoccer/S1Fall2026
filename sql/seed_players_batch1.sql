-- Adds 3 players extracted from their PowerPoint profile cards.
-- Photos are served from your own site at /assets/players/<name>.jpg
-- (already included in the site files — just needs redeploying).
--
-- NOTE: jersey numbers below (Minti #13, Ketan #11, Preetesh #12) are NOT
-- set here — jersey number lives on the season roster assignment, which
-- needs a team to attach to. Once you assign these players to teams in the
-- admin dashboard's "Season Rosters" tab, enter these numbers there.

insert into players (full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes)
values
(
  'Minti',
  39,
  '40/M',
  'Def',
  'Right',
  'assets/players/minti.jpg',
  'Stamina: Medium. Skill rating: 4/10. Skill level: Intermediate. Experience: Exposure to corporate league, practice matches. Fitness/injury notes: None that will affect game. Leave plan: None. (Jersey #13 — set on roster assignment.)'
),
(
  'Ketan Shilimkar',
  38,
  'M',
  'Midfield / Goal Keeper',
  'Right',
  'assets/players/ketan.jpg',
  'Stamina: Medium. Skill rating: 5/10. Skill level: Beginner. Experience: Beginner. Leave plan: NA. (Jersey #11 — set on roster assignment.)'
),
(
  'Preetesh Duvvuri',
  41,
  'Large',
  'Goal Keeper / Defender',
  'Right',
  'assets/players/preetesh.jpg',
  'Stamina: Low. Skill rating: 3/10. Skill level: Beginner. Experience: Recreational. Leave plan: No leave plan. (Jersey #12 — set on roster assignment.)'
);
