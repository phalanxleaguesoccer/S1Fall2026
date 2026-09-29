-- Penalty shoot-outs are NEVER played in matches. They are used only as the
-- very last standings tie-break, between teams that are level on points,
-- goal difference, goals scored, goals conceded and head-to-head.
-- Each row = one shoot-out between two teams in a season, and who won it.
create table if not exists tiebreak_shootouts (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references seasons(id) on delete cascade,
  team_a_id uuid not null references teams(id),
  team_b_id uuid not null references teams(id),
  winner_team_id uuid not null references teams(id),
  created_at timestamptz not null default now(),
  check (team_a_id <> team_b_id),
  check (winner_team_id in (team_a_id, team_b_id)),
  unique (season_id, team_a_id, team_b_id)
);
alter table tiebreak_shootouts enable row level security;
drop policy if exists "public read tiebreak shootouts" on tiebreak_shootouts;
drop policy if exists "admin write tiebreak shootouts" on tiebreak_shootouts;
create policy "public read tiebreak shootouts" on tiebreak_shootouts for select using (true);
create policy "admin write tiebreak shootouts" on tiebreak_shootouts for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));

-- The per-match shoot-out column added earlier is no longer used.
alter table matches drop column if exists shootout_winner_team_id;
