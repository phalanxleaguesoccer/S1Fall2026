-- Phalanx League Soccer — Database Schema (Supabase/Postgres)
-- Run this in Supabase SQL editor once, on a fresh project.

-- ============ CORE TABLES ============

create table seasons (
  id uuid primary key default gen_random_uuid(),
  name text not null,                 -- e.g. "Season 1 - 2026"
  is_current boolean not null default false,
  points_win int not null default 2,
  points_draw int not null default 1,
  points_loss int not null default 0,
  created_at timestamptz not null default now()
);

create table teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  crest_url text,                     -- team logo/crest image
  color_primary text,                 -- hex, optional per-team accent
  created_at timestamptz not null default now()
);

create table players (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  age int,
  jersey_size text,
  preferred_position text,
  preferred_foot text,                -- Left / Right / Both
  photo_url text,                     -- single headshot
  fun_fact text,
  bio_notes text,
  created_at timestamptz not null default now()
);

-- A player's team assignment is per-season (auction-based; locked once assigned,
-- but a NEW season can move a player to a different team).
create table team_season_rosters (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references seasons(id) on delete cascade,
  team_id uuid not null references teams(id) on delete cascade,
  player_id uuid not null references players(id) on delete cascade,
  is_owner boolean not null default false,   -- team owner = first player, not auctioned
  jersey_number int,
  auction_price int,                          -- points spent to acquire (nullable for owner)
  unique (season_id, player_id)                -- a player is on exactly 1 team per season
);

create table matches (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references seasons(id) on delete cascade,
  match_day int not null,             -- 1-6 per handover doc schedule
  match_number int not null,          -- 1-4 within the day
  home_team_id uuid not null references teams(id),
  away_team_id uuid not null references teams(id),
  kickoff_at timestamptz,             -- nullable until scheduled
  status text not null default 'scheduled', -- scheduled | completed | forfeited | postponed
  home_score int,                     -- null until played; null permanently if forfeited
  away_score int,
  forfeited_by_team_id uuid references teams(id), -- set if status = forfeited
  notes text,
  created_at timestamptz not null default now()
);

-- Every logged match event: goal, assist, yellow card, red card, sub, etc.
create table match_events (
  id uuid primary key default gen_random_uuid(),
  match_id uuid not null references matches(id) on delete cascade,
  team_id uuid not null references teams(id),
  player_id uuid not null references players(id),
  event_type text not null,           -- goal | assist | yellow_card | red_card | substitution_in | substitution_out
  minute int,                         -- 1-7 (first half) or 8-14 (second half), matches your 7-min halves
  half int,                           -- 1 or 2
  related_player_id uuid references players(id), -- e.g. assist-to on a goal, or sub partner
  notes text,
  created_at timestamptz not null default now()
);

-- ============ ADMIN ACCESS ============
-- Uses Supabase Auth (auth.users) for the 2 admin logins.
-- This table whitelists which auth.users are allowed to edit.
create table admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text
);

-- ============ VIEWS FOR DERIVED DATA ============

-- Aggregated player stats per season (computed from match_events + matches)
create or replace view player_season_stats as
select
  p.id as player_id,
  p.full_name,
  tsr.season_id,
  tsr.team_id,
  count(distinct m.id) filter (
    where m.status = 'completed'
    and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
  ) as games_played,
  count(*) filter (where me.event_type = 'goal') as goals,
  count(*) filter (where me.event_type = 'assist') as assists,
  count(*) filter (where me.event_type = 'yellow_card') as yellow_cards,
  count(*) filter (where me.event_type = 'red_card') as red_cards
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;

-- League standings per season, with the doc's tie-breaker order:
-- points -> goal difference -> goals scored -> goals conceded -> head-to-head -> penalty shoot-out
-- (head-to-head and penalty shoot-out are applied manually/at the UI level for ties this view can't resolve)
create or replace view league_standings as
with raw_team_matches as (
  select
    s.id as season_id,
    t.id as team_id,
    m.id as match_id,
    m.status,
    m.forfeited_by_team_id,
    case when m.home_team_id = t.id then m.home_score else m.away_score end as goals_for,
    case when m.home_team_id = t.id then m.away_score else m.home_score end as goals_against
  from seasons s
  join teams t on true
  join matches m on m.season_id = s.id and (m.home_team_id = t.id or m.away_team_id = t.id)
  where m.status in ('completed', 'forfeited')
),
team_matches as (
  select
    season_id,
    team_id,
    match_id,
    status,
    goals_for,
    goals_against,
    case
      when status = 'forfeited' and forfeited_by_team_id = team_id then 'loss'
      when status = 'forfeited' and forfeited_by_team_id != team_id then 'win'
      when status = 'completed' and goals_for > goals_against then 'win'
      when status = 'completed' and goals_for < goals_against then 'loss'
      when status = 'completed' then 'draw'
      else null
    end as result
  from raw_team_matches
)
select
  tm.season_id,
  tm.team_id,
  count(*) as played,
  count(*) filter (where result = 'win') as wins,
  count(*) filter (where result = 'draw') as draws,
  count(*) filter (where result = 'loss') as losses,
  coalesce(sum(goals_for), 0) as goals_for,
  coalesce(sum(goals_against), 0) as goals_against,
  coalesce(sum(goals_for), 0) - coalesce(sum(goals_against), 0) as goal_difference,
  (count(*) filter (where result = 'win')) * (select points_win from seasons where id = tm.season_id)
  + (count(*) filter (where result = 'draw')) * (select points_draw from seasons where id = tm.season_id)
  + (count(*) filter (where result = 'loss')) * (select points_loss from seasons where id = tm.season_id)
  as points
from team_matches tm
group by tm.season_id, tm.team_id;

-- ============ ROW LEVEL SECURITY ============
-- Public can READ everything. Only whitelisted admins can WRITE.

alter table seasons enable row level security;
alter table teams enable row level security;
alter table players enable row level security;
alter table team_season_rosters enable row level security;
alter table matches enable row level security;
alter table match_events enable row level security;
alter table admins enable row level security;

create policy "public read seasons" on seasons for select using (true);
create policy "public read teams" on teams for select using (true);
create policy "public read players" on players for select using (true);
create policy "public read rosters" on team_season_rosters for select using (true);
create policy "public read matches" on matches for select using (true);
create policy "public read events" on match_events for select using (true);

create policy "admin write seasons" on seasons for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));
create policy "admin write teams" on teams for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));
create policy "admin write players" on players for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));
create policy "admin write rosters" on team_season_rosters for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));
create policy "admin write matches" on matches for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));
create policy "admin write events" on match_events for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));

-- Only admins can see the admins table itself (avoid leaking who the admins are)
create policy "admins read self" on admins for select using (auth.uid() = user_id);

-- ============ SEED: current season + 4 teams (names TBD post-auction) ============
insert into seasons (name, is_current) values ('Season 1', true);
