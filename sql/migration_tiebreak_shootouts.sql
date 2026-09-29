-- Penalty shoot-outs are NEVER played in matches. They are used only as the
-- very last standings tie-break, only after the whole tournament is complete,
-- for teams that nothing else (points, goal difference, goals scored, goals
-- conceded, head-to-head) can separate. This table stores the final
-- shoot-out order (1 = best) so every team ends with a unique rank.
drop table if exists tiebreak_shootouts;
create table if not exists tiebreak_shootout_order (
  season_id uuid not null references seasons(id) on delete cascade,
  team_id uuid not null references teams(id),
  position int not null check (position >= 1),
  created_at timestamptz not null default now(),
  primary key (season_id, team_id),
  unique (season_id, position)
);
alter table tiebreak_shootout_order enable row level security;
drop policy if exists "public read tiebreak order" on tiebreak_shootout_order;
drop policy if exists "admin write tiebreak order" on tiebreak_shootout_order;
create policy "public read tiebreak order" on tiebreak_shootout_order for select using (true);
create policy "admin write tiebreak order" on tiebreak_shootout_order for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));

alter table matches drop column if exists shootout_winner_team_id;
