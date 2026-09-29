-- Live auction support.
-- 1) When a player was sold (for the live feed + undo-last).
alter table team_season_rosters add column if not exists sold_at timestamptz default now();

-- 2) Points each team may spend in the auction (200 per team).
alter table seasons add column if not exists auction_budget int not null default 200;

-- 3) Players passed on in the auction -> Round 2.
--    round 1 = passed in Round 1 (available in Round 2)
--    round 2 = passed again in Round 2 (final unsold)
create table if not exists auction_unsold (
  season_id uuid not null references seasons(id) on delete cascade,
  player_id uuid not null references players(id) on delete cascade,
  round int not null default 1 check (round in (1, 2)),
  created_at timestamptz not null default now(),
  primary key (season_id, player_id)
);

-- 4) Which player is "on the block" right now (shown live to viewers).
create table if not exists auction_state (
  season_id uuid primary key references seasons(id) on delete cascade,
  current_player_id uuid references players(id) on delete set null,
  updated_at timestamptz not null default now()
);

alter table auction_unsold enable row level security;
alter table auction_state enable row level security;
drop policy if exists "public read auction unsold" on auction_unsold;
drop policy if exists "admin write auction unsold" on auction_unsold;
drop policy if exists "public read auction state" on auction_state;
drop policy if exists "admin write auction state" on auction_state;
create policy "public read auction unsold" on auction_unsold for select using (true);
create policy "admin write auction unsold" on auction_unsold for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));
create policy "public read auction state" on auction_state for select using (true);
create policy "admin write auction state" on auction_state for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));
