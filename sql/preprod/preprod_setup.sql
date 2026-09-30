-- PHALANX LEAGUE SOCCER - PREPROD DATABASE SETUP (generated; do not edit by hand)
-- Run ONCE in the PREPROD Supabase project's SQL Editor. NEVER run it on the live project.
-- All-or-nothing: if any statement fails, nothing is kept and it can simply be run again.
begin;
do $$ begin if to_regclass('public.players') is not null then raise exception 'STOP: this database already has league tables. The preprod setup only runs on a brand-new, empty Supabase project.'; end if; end $$;

-- ======== sql/schema.sql ========
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

-- ======== sql/migration_player_attributes.sql ========
-- Migration: adds real columns for the attributes needed by the Players
-- page "Sort & Filter" feature. Run this once in the Supabase SQL editor.
-- Safe to run even if some columns already exist (uses IF NOT EXISTS).

alter table players add column if not exists stamina_level text;      -- 'Low' | 'Medium' | 'High'
alter table players add column if not exists stamina_rank int;        -- 1=Low, 2=Medium, 3=High (drives sort order)
alter table players add column if not exists skill_rating int;        -- numeric rating out of 10
alter table players add column if not exists skill_level text;        -- 'Beginner' | 'Intermediate' | 'Advanced' | 'Pro'
alter table players add column if not exists skill_level_rank int;    -- 1=Beginner..4=Pro (drives sort order)
alter table players add column if not exists playing_experience text; -- free text, filter-only
alter table players add column if not exists fitness_notes text;      -- free text, filter-only
alter table players add column if not exists leave_plan text;         -- free text, filter-only

-- Keep the two rank columns in sync automatically whenever stamina_level /
-- skill_level is set or changed via the admin dashboard, so you never have
-- to remember to update the rank by hand.
create or replace function set_player_attribute_ranks()
returns trigger as $$
begin
  new.stamina_rank := case lower(coalesce(new.stamina_level, ''))
    when 'low' then 1
    when 'medium' then 2
    when 'high' then 3
    else null
  end;
  new.skill_level_rank := case lower(coalesce(new.skill_level, ''))
    when 'beginner' then 1
    when 'intermediate' then 2
    when 'advanced' then 3
    when 'pro' then 4
    else null
  end;
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_set_player_attribute_ranks on players;
create trigger trg_set_player_attribute_ranks
  before insert or update on players
  for each row execute function set_player_attribute_ranks();

-- ============ RE-ENTER THE 3 EXISTING PLAYERS' DATA INTO THE NEW COLUMNS ============
-- (Previously bundled into one bio_notes text blob — now split out. bio_notes
-- itself is left as-is/untouched so nothing is lost.)

update players set
  stamina_level = 'Medium',
  skill_rating = 4,
  skill_level = 'Intermediate',
  playing_experience = 'Exposure to corporate league, practice matches.',
  fitness_notes = 'None that will affect game.',
  leave_plan = 'None.'
where full_name = 'Minti';

update players set
  stamina_level = 'Medium',
  skill_rating = 5,
  skill_level = 'Beginner',
  playing_experience = 'Beginner.',
  fitness_notes = null,
  leave_plan = 'NA'
where full_name = 'Ketan Shilimkar';

update players set
  stamina_level = 'Low',
  skill_rating = 3,
  skill_level = 'Beginner',
  playing_experience = 'Recreational.',
  fitness_notes = null,
  leave_plan = 'No leave plan.'
where full_name = 'Preetesh Duvvuri';

-- ======== sql/migration_position_categories.sql ========
-- Migration: adds a standardized position_category column (Forward / Center /
-- Defense / Flex / Goalkeeper) used for the Players page filter, and
-- categorizes all 22 players currently on file per your answers.
--
-- The original detailed position (e.g. "Mid-field/Defence", "LM/CDM/CM/Wing/LB")
-- stays exactly as-is in preferred_position — position_category is a new,
-- separate column just for filtering; nothing is overwritten or lost.

alter table players add column if not exists position_category text
  check (position_category in ('Forward', 'Center', 'Defense', 'Flex', 'Goalkeeper'));

update players set position_category = 'Defense'    where full_name = 'Minti';
update players set position_category = 'Flex'       where full_name = 'Ketan Shilimkar';
update players set position_category = 'Flex'       where full_name = 'Preetesh Duvvuri';
update players set position_category = 'Flex'       where full_name = 'Rohith';
update players set position_category = 'Defense'    where full_name = 'Sangram Ghewade';
update players set position_category = 'Flex'       where full_name = 'Taranjot Singh Dang';
update players set position_category = 'Forward'    where full_name = 'Jitendra';
update players set position_category = 'Flex'       where full_name = 'Vivek';
update players set position_category = 'Forward'    where full_name = 'Sagar SJ';
update players set position_category = 'Goalkeeper' where full_name = 'Vignesh';
update players set position_category = 'Flex'       where full_name = 'Vija';
update players set position_category = 'Flex'       where full_name = 'Kishor Ghadge';
update players set position_category = 'Flex'       where full_name = 'Vamshi';
update players set position_category = 'Flex'       where full_name = 'Pradnyal Gandhi';
update players set position_category = 'Flex'       where full_name = 'Vishnu Mohan';
update players set position_category = 'Flex'       where full_name = 'Sagar';
update players set position_category = 'Defense'    where full_name = 'Ketan Gaikwad';
update players set position_category = 'Center'     where full_name = 'Dheeraj R Vatti';
update players set position_category = 'Center'     where full_name = 'Kartik';
update players set position_category = 'Forward'    where full_name = 'Nuhu Okikiri';
update players set position_category = 'Defense'    where full_name = 'Rajeev Singh';
update players set position_category = 'Center'     where full_name = 'Nasiq';

-- ======== sql/migration_page_views.sql ========
-- Migration: adds page-view tracking (total site views + per-page views,
-- including individual player/team/match pages).
--
-- Design: a narrow table (page_views) holds one row per tracked page, plus
-- one row keyed 'site' for the running total-site-views count. Public reads
-- are allowed directly (so the count can be displayed), but public WRITES
-- go only through the increment_page_view() function below, not directly
-- against the table — this keeps the counts from being trivially
-- overwritten/reset by anyone with the publishable key, while still letting
-- anonymous visitors trigger a view increment without needing to log in.

create table if not exists page_views (
  page_key text primary key,
  view_count bigint not null default 0,
  updated_at timestamptz not null default now()
);

alter table page_views enable row level security;

create policy "public read page views" on page_views for select using (true);
-- Intentionally NO public insert/update/delete policy — all writes happen
-- through the SECURITY DEFINER function below instead.

create or replace function increment_page_view(p_key text)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
  new_count bigint;
begin
  insert into page_views (page_key, view_count, updated_at)
  values (p_key, 1, now())
  on conflict (page_key) do update
    set view_count = page_views.view_count + 1,
        updated_at = now()
  returning view_count into new_count;
  return new_count;
end;
$$;

-- Anyone (including anonymous/public-key visitors) may call the function,
-- since it only ever adds 1 and cannot be used to read or modify anything
-- else in the database.
grant execute on function increment_page_view(text) to anon, authenticated;

insert into page_views (page_key, view_count) values ('site', 0)
on conflict (page_key) do nothing;

-- ======== sql/seed_players_batch1.sql ========
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

-- ======== sql/seed_players_batch2.sql ========
-- Batch 2: adds 17 new players extracted from their PowerPoint/PDF profile
-- cards. Run migration_player_attributes.sql FIRST (adds the columns this
-- insert writes to).
--
-- Skipped on purpose (already in the database from batch 1, same person,
-- just a resubmitted/updated file) — NOT re-inserted here to avoid duplicates:
--   - Minti                (2 copies uploaded again — same person)
--   - Ketan Shilimkar       (uploaded again as "White Font Adjusted Pic" — same person)
--   - Preetesh Duvvuri      (uploaded again as "Final" — same person)
--
-- Note: "Ketan Gaikwad" below is a DIFFERENT person from "Ketan Shilimkar"
-- already in the database — both are kept, distinguished by full name.
-- Note: "Sagar SJ" and "Sagar" are two different people (different age,
-- position, jersey #) — both kept.
--
-- Jersey numbers are entered here directly on the player record for
-- reference, but the number that actually counts is the one you set on the
-- Season Roster assignment once the auction happens (same as batch 1).

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan
) values
(
  'Rohith', 39, 'XL', 'Mid-field/Defence', 'Right', 'assets/players/rohith.jpg',
  'Jersey #08 (Rohith).',
  'Medium', 7, 'Intermediate',
  'University player/Corporate tournament/Recreational/League tournaments',
  null,
  'Might have unplanned business trips'
),
(
  'Sangram Ghewade', 34, 'M', 'Defender / Right Wing', 'Right', 'assets/players/sangram.jpg',
  'Jersey #7 (Sangram). Skill level on card read "Medium" — recorded as Intermediate, closest standard tier.',
  'Medium', 7, 'Intermediate',
  'College Football/Recreation',
  'None',
  'Unavailable from Nov 1'
),
(
  'Taranjot Singh Dang', 26, 'Adult M', 'LM/CDM/CM/Wing/LB', 'Right', 'assets/players/taranjot.jpg',
  'Jersey #17 (T DANG). Card stamina read "Med-high" — recorded as Medium.',
  'Medium', 6, 'Intermediate',
  'Local leagues',
  'NA',
  '15-18 October'
),
(
  'Jitendra', 45, 'M', 'Fwd', 'Right', 'assets/players/jitendra.jpg',
  'Jersey #10 (Ronaldo).',
  'Low', 4, 'Beginner',
  '3 years',
  'Good',
  'None'
),
(
  'Vivek', 36, 'US M', 'Forward / Defense', 'Right', 'assets/players/vivek.jpg',
  'Jersey #7 (Vivek). Card had two different skill-rating numbers (5/10 and 6/10) in different spots — recorded as 5/10.',
  'Medium', 5, 'Intermediate',
  'Mostly recreational',
  'NA',
  'No plans yet'
),
(
  'Sagar SJ', 40, 'US (M)', 'Winger', 'Right', 'assets/players/sagar-sj.jpg',
  'Jersey #20 (Sagar SJ).',
  'Medium', 6, 'Intermediate',
  'Mostly recreational',
  'None',
  'None'
),
(
  'Vignesh', 36, 'Adult – Small (US)', 'Goalkeeper', 'Right', 'assets/players/vignesh.jpeg',
  'Jersey #4 (Vignesh).',
  'Medium', 7, 'Intermediate',
  'Recreational. Good reflex action, has been doing goalkeeping for many years.',
  'Ankle injury history. Limits himself to fulltime goalkeeping; can switch to defense/midfield temporarily if a player is tired.',
  'Might need to go on business travel at short notice. Will try to make alternate travel plans, but customer meetings may not be flexible.'
),
(
  'Vija', 35, 'XL', 'Mid/Def', 'Right', 'assets/players/vija.jpg',
  'Jersey #18 (Vija).',
  'Low', 3, 'Beginner',
  'Recreational',
  'NA',
  'NA'
),
(
  'Kishor Ghadge', 37, 'Medium (US)', 'Mid / Wing', 'Right', 'assets/players/kishor.jpg',
  'Jersey #18 (Kish) — same number as Vija''s card; flagged for the admin to resolve on roster assignment. Card skill level read "Basic" — recorded as Beginner.',
  'Medium', 3, 'Beginner',
  'Just started playing.',
  'NA',
  'NA'
),
(
  'Vamshi', 32, 'M', 'Mid / Winger', 'Right', 'assets/players/vamshi.jpg',
  'No jersey number given on card.',
  'Medium', 6, 'Intermediate',
  'College football / recreation',
  null,
  null
),
(
  'Pradnyal Gandhi', 28, 'M', 'Flex, prefer Mid', 'Right', 'assets/players/pradnyal.jpeg',
  'Jersey #10 / 8 (Pradnyal) — two numbers given on card; flagged for the admin to pick one on roster assignment.',
  'High', 8, 'Advanced',
  'College team, intramural leagues, pickup soccer',
  null,
  'Oct 8 - 13'
),
(
  'Vishnu Mohan', 37, 'Adult M', 'Prefer Mid / Wing', 'Right', 'assets/players/vishnu.jpg',
  'Jersey #10/18 (Vishnu) — two numbers given on card; flagged for the admin to pick one on roster assignment.',
  'Medium', 7, 'Advanced',
  'Been playing soccer since college; played for college team, corporate tournaments and pickup soccer',
  'NA',
  'Oct 9-12; Nov 11-14'
),
(
  'Sagar', 33, 'US M', 'Forward / Defence', 'Right', 'assets/players/sagar.jpg',
  'No jersey number given on card. Distinct person from "Sagar SJ" (different age/position/card).',
  'Medium', 6, 'Intermediate',
  'Mostly recreational',
  'NA',
  'No plans yet'
),
(
  'Ketan Gaikwad', 33, 'Adult L', 'Defence', 'Right', 'assets/players/ketan-gaikwad.jpg',
  'Jersey #05. Distinct person from "Ketan Shilimkar" already on file. Card stamina read "Average" — recorded as Medium.',
  'Medium', 3, 'Beginner',
  'School-level experience; last played about 15 years ago.',
  'None',
  'None known'
),
(
  'Dheeraj R Vatti', 37, 'Large', 'Mid', 'Right', 'assets/players/dheeraj.jpg',
  'Jersey #10 (Dheeraj).',
  'Medium', 7, 'Intermediate',
  'College Football and Recreational games post-college',
  null,
  'None'
),
(
  'Kartik', 39, 'Adult M', 'Mid', 'Both', 'assets/players/kartik.jpg',
  'Jersey #8 (Kartik). Card''s name field was left as the template placeholder ("Your Full Name") — used the jersey name "Kartik" instead; confirm full name with the player.',
  'Medium', 7, 'Advanced',
  '32 years played — school, college, company, club and recreational for the last 6 years',
  null,
  'Last minute business related travel'
),
(
  'Nuhu Okikiri', 38, 'Adult M', 'Left Wing/Right Wing', 'Right', 'assets/players/nuhu.jpg',
  'Jersey #7 (Nuhu).',
  'Medium', 7, 'Intermediate',
  '2 years - non consistent',
  'Minor ankle injury',
  'N/A'
);

-- ======== sql/seed_players_batch3.sql ========
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

-- ======== sql/seed_players_batch4.sql ========
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

-- ======== sql/seed_players_batch5.sql ========
-- Batch 5: adds 7 new players (Kaushik was uploaded twice as identical
-- files — only inserted once here). Run after all previous migration/seed
-- scripts (needs stamina_level/skill_rating/skill_level/position_category
-- columns already in place).
--
-- Also includes the fitness-notes fix for Jitendra and Minti requested in
-- the same message.

update players set fitness_notes = 'None' where full_name = 'Jitendra';
update players set fitness_notes = 'None' where full_name = 'Minti';

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Dhananjay', 36, 'M', 'Def', 'Right', 'assets/players/dhananjay.jpg',
  'Jersey #10 (DJ) — same number as Jitendra''s and Dheeraj''s cards; flagged for the admin to resolve on roster assignment.',
  'Medium', 6, 'Intermediate',
  'Recreational',
  'None',
  'None',
  'Defense'
),
(
  'Shailesh', 44, 'Adult M', 'Mid / Winger', 'Right', 'assets/players/shailesh.jpg',
  'Jersey #45 (Shailesh). Card left Skill Rating unfilled (showed the template''s blank "X/10") — recorded as no rating; Skill Level read "Intermediate". Position combo (Mid/Winger) — category recorded as Flex.',
  'Low', null, 'Intermediate',
  'Recreational',
  'Knee Pain',
  'Oct 11-18',
  'Flex'
),
(
  'Prajna', 41, 'L', 'Mid Fielder / Right Wing', 'Right', 'assets/players/prajna.jpg',
  'Jersey #99 (Prajna).',
  'Low', 6, 'Intermediate',
  'Intra College',
  'None',
  'None',
  'Flex'
),
(
  'Amritpal Singh', 30, 'Adult XL / US 42-44', 'Felx except keeper', 'Right', 'assets/players/amritpal.jpg',
  'Jersey #1 (AMRIT).',
  'Low', 7, 'Intermediate',
  'Played Competitive in College / Recreational & pick-up post college',
  'Sciatica; cannot run for longer durations due to lower back pain.',
  'None',
  'Flex'
),
(
  'Sandeep Naik', 39, 'Medium', 'Forward', 'Right', 'assets/players/sandeep-naik.jpg',
  'Jersey #777 (Sandeep) — unusual number as given on the card, kept as-is.',
  'Medium', 3, 'Beginner',
  'Beginner',
  'Hamstring/Tennis Elbow',
  'No plans',
  'Forward'
),
(
  'Ashu', 30, 'L', 'Def/Goalie/Mid', 'Both', 'assets/players/ashu.jpg',
  'Jersey #7 (Ashu) — same number as Sangram Ghewade''s, Vivek''s, and Nuhu''s cards; flagged for the admin to resolve on roster assignment.',
  'Medium', 6, 'Advanced',
  '16 years',
  'NA',
  'NA',
  'Flex'
),
(
  'Kaushik', 31, 'Adult M', 'Flex', 'Both', 'assets/players/kaushik.jpg',
  'Jersey #19 (Kaushik) — same number as Dhruv''s card (which itself listed "19 or 11"); flagged for the admin to resolve on roster assignment. Card''s name field was left as the template placeholder ("Your Full Name") — used the jersey name "Kaushik" instead; confirm full name with the player. Card''s skill rating was 6.5/10 — rounded to 7 since the column stores whole numbers. Uploaded twice as identical files — inserted once.',
  'Low', 7, 'Intermediate',
  'Intra-mural leagues',
  null,
  'Out Nov 10th onwards',
  'Flex'
);

-- ======== sql/fix_shailesh_kaushik.sql ========
-- Fix: Shailesh's skill rating (was left blank, now set to 3) and
-- Kaushik's full name (was using just the jersey name "Kaushik", now his
-- full name "Kaushik Apte").

update players set skill_rating = 3
where full_name = 'Shailesh';

update players set full_name = 'Kaushik Apte'
where full_name = 'Kaushik';

-- ======== sql/seed_schedule.sql ========
-- Adds 4 placeholder teams (A/B/C/D) and the full 24-match schedule.
-- Safe to run once on a fresh project with no teams yet.
-- Kickoff dates/times are left NULL (TBD) — update them later via the admin dashboard
-- or by re-running an UPDATE once dates are locked.

insert into teams (name) values ('Team A'), ('Team B'), ('Team C'), ('Team D');

with s as (
  select id as season_id from seasons where is_current = true limit 1
),
t as (
  select name, id from teams where name in ('Team A','Team B','Team C','Team D')
)
insert into matches (season_id, match_day, match_number, home_team_id, away_team_id, status)
select s.season_id, v.match_day, v.match_number, home.id, away.id, 'scheduled'
from s,
(values
  (1, 1, 'Team B', 'Team D'),
  (1, 2, 'Team A', 'Team C'),
  (1, 3, 'Team A', 'Team D'),
  (1, 4, 'Team B', 'Team C'),
  (2, 1, 'Team C', 'Team D'),
  (2, 2, 'Team A', 'Team B'),
  (2, 3, 'Team B', 'Team C'),
  (2, 4, 'Team A', 'Team D'),
  (3, 1, 'Team B', 'Team D'),
  (3, 2, 'Team A', 'Team C'),
  (3, 3, 'Team C', 'Team D'),
  (3, 4, 'Team A', 'Team B'),
  (4, 1, 'Team A', 'Team C'),
  (4, 2, 'Team B', 'Team D'),
  (4, 3, 'Team A', 'Team D'),
  (4, 4, 'Team B', 'Team C'),
  (5, 1, 'Team C', 'Team D'),
  (5, 2, 'Team A', 'Team B'),
  (5, 3, 'Team A', 'Team D'),
  (5, 4, 'Team B', 'Team C'),
  (6, 1, 'Team C', 'Team D'),
  (6, 2, 'Team A', 'Team B'),
  (6, 3, 'Team B', 'Team D'),
  (6, 4, 'Team A', 'Team C')
) as v(match_day, match_number, home_name, away_name)
join teams home on home.name = v.home_name
join teams away on away.name = v.away_name;

-- ======== sql/seed_players_batch6.sql ========
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

-- ======== sql/migration_potm_awards.sql ========
-- Migration: adds "Player of the Match" awards to a player's stats.
--
-- Design: reuses the existing match_events table (event_type is free text,
-- no schema change needed there) with a new event_type value
-- 'player_of_match', logged once per match for the awarded player via the
-- admin dashboard's Event Log form (Team/Player/Half/Minute can be left at
-- defaults since only the award matters). player_season_stats is updated to
-- surface a potm_awards count alongside goals/assists/cards.

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
  count(*) filter (where me.event_type = 'red_card') as red_cards,
  count(*) filter (where me.event_type = 'player_of_match') as potm_awards
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;

-- ======== sql/update_match_dates.sql ========
-- Sets the match date for each match day (all Tuesdays).
-- Time-of-day is left as a placeholder (12:00 PM Eastern) since exact kickoff
-- times per match weren't given — adjust per-match via the admin dashboard
-- (Matches tab) once times are locked in.

update matches set kickoff_at = '2026-10-06 12:00:00-04' where match_day = 1;
update matches set kickoff_at = '2026-10-13 12:00:00-04' where match_day = 2;
update matches set kickoff_at = '2026-10-20 12:00:00-04' where match_day = 3;
update matches set kickoff_at = '2026-10-27 12:00:00-04' where match_day = 4;
update matches set kickoff_at = '2026-11-03 12:00:00-05' where match_day = 5;
update matches set kickoff_at = '2026-11-10 12:00:00-05' where match_day = 6;

-- ======== sql/update_team1_desi_steelers.sql ========
-- Renames "Team A" to "Desi Steelers FC" with a new crest, and sets Nasiq as
-- the team owner for the current season. Only the teams.name/crest_url and a
-- team_season_rosters row change here — match_day fixtures in `matches`
-- reference teams by team_id (a stable UUID), not by name, so the existing
-- schedule (seed_schedule.sql) is untouched by this rename.

update teams
set name = 'Desi Steelers FC',
    crest_url = 'assets/teams/desi-steelers-fc.png'
where name = 'Team A';

-- Assigns Nasiq to Desi Steelers FC as owner for the current season.
-- (No jersey_number/auction_price yet since owners are pre-auction.)
insert into team_season_rosters (season_id, team_id, player_id, is_owner)
select s.id, t.id, p.id, true
from seasons s, teams t, players p
where s.is_current = true
  and t.name = 'Desi Steelers FC'
  and p.full_name = 'Nasiq'
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = true;

-- ======== sql/add_teams_muggles_scouts.sql ========
-- Adds 2 new teams: Muggles FC (owner: Amritpal Singh) and Scouts FC
-- (owner: Bhagyesh Rane — run seed_players_batch7.sql first, since this
-- depends on his player row existing).
--
-- Note: the original 24-match schedule (seed_schedule.sql) only fixtures
-- Team A/B/C/D (now including the renamed Desi Steelers FC) — these 2 new
-- teams get no matches automatically; add fixtures for them separately if
-- they're meant to play this season.

insert into teams (name, crest_url) values
  ('Muggles FC', 'assets/teams/muggles-fc.png'),
  ('Scouts FC', 'assets/teams/scouts-fc.png');

insert into team_season_rosters (season_id, team_id, player_id, is_owner)
select s.id, t.id, p.id, true
from seasons s, teams t, players p
where s.is_current = true
  and t.name = 'Muggles FC'
  and p.full_name = 'Amritpal Singh'
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = true;

insert into team_season_rosters (season_id, team_id, player_id, is_owner)
select s.id, t.id, p.id, true
from seasons s, teams t, players p
where s.is_current = true
  and t.name = 'Scouts FC'
  and p.full_name = 'Bhagyesh Rane'
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = true;

-- ======== sql/seed_players_batch7.sql ========
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

-- ======== sql/migration_saves_and_tournament_award.sql ========
-- Migration: adds "Goals Saved" (goalkeeper saves) and "Player of the
-- Tournament" to player stats.
--
-- Both reuse the existing match_events table (event_type is free text, no
-- schema change needed there):
--   - 'save'                 — log once per save via the admin dashboard,
--                              same as a goal/assist/card.
--   - 'player_of_tournament' — a season-wide award, not really tied to one
--                              match, but match_events requires a match_id,
--                              so log it once against any match played in
--                              that season (e.g. the final match day) for
--                              the awarded player — it's counted per
--                              season/team via the match's season_id, not
--                              tied to that specific match's outcome.

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
  count(*) filter (where me.event_type = 'red_card') as red_cards,
  count(*) filter (where me.event_type = 'player_of_match') as potm_awards,
  count(*) filter (where me.event_type = 'save') as saves,
  count(*) filter (where me.event_type = 'player_of_tournament') as tournament_awards
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;

-- ======== sql/untag_desi_steelers_from_team_a.sql ========
-- Undoes the earlier merge of "Desi Steelers FC" into the schedule's Team A
-- slot. No draw has happened yet to decide which real team identity plays
-- as Team A/B/C/D, so Desi Steelers FC (name, crest, and Nasiq as owner)
-- becomes its own standalone team entity — same as Muggles FC and Scouts FC
-- — while the actual schedule slot reverts to a plain, unassigned "Team A".

-- Step 1: revert the schedule's team back to a plain, unbranded slot.
update teams set name = 'Team A', crest_url = null where name = 'Desi Steelers FC';

-- Step 2: create Desi Steelers FC as its own standalone team, not tied to
-- any scheduled match.
insert into teams (name, crest_url) values ('Desi Steelers FC', 'assets/teams/desi-steelers-fc.png');

-- Step 3: move Nasiq's owner assignment off the (now reverted) Team A and
-- onto the new standalone Desi Steelers FC team.
update team_season_rosters
set team_id = (select id from teams where name = 'Desi Steelers FC')
where player_id = (select id from players where full_name = 'Nasiq')
  and is_owner = true;

-- ======== sql/add_team_renegades.sql ========
-- Adds Renegades as a 4th standalone identity team (owner: Varun, "Zack" on
-- his jersey), not tied to any scheduled match — same as Desi Steelers FC,
-- Muggles FC, and Scouts FC. The actual Team A/B/C/D schedule slots are
-- untouched; those get assigned to real teams once the draw happens.

insert into teams (name, crest_url) values
  ('Renegades', 'assets/teams/renegades.png');

insert into team_season_rosters (season_id, team_id, player_id, is_owner)
select s.id, t.id, p.id, true
from seasons s, teams t, players p
where s.is_current = true
  and t.name = 'Renegades'
  and p.full_name = 'Varun'
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = true;

-- ======== sql/update_match_times.sql ========
-- Sets kickoff time-of-day for every match, based on match_number, on top of
-- the dates already set in update_match_dates.sql (Day 1-6 = the Tuesdays
-- Oct 6 - Nov 10, 2026). Same time slots apply on every match day:
--   Match 1: 9:00 PM Eastern
--   Match 2: 9:25 PM Eastern
--   Match 3: 9:50 PM Eastern
--   Match 4: 10:15 PM Eastern
-- (Offset is -04 for Oct dates during Eastern Daylight Time, -05 for the
-- Nov 3 and Nov 10 dates once EDT ends; both represent the same "9:00 PM
-- Eastern" wall-clock time.)

update matches set kickoff_at = '2026-10-06 21:00:00-04' where match_day = 1 and match_number = 1;
update matches set kickoff_at = '2026-10-06 21:25:00-04' where match_day = 1 and match_number = 2;
update matches set kickoff_at = '2026-10-06 21:50:00-04' where match_day = 1 and match_number = 3;
update matches set kickoff_at = '2026-10-06 22:15:00-04' where match_day = 1 and match_number = 4;

update matches set kickoff_at = '2026-10-13 21:00:00-04' where match_day = 2 and match_number = 1;
update matches set kickoff_at = '2026-10-13 21:25:00-04' where match_day = 2 and match_number = 2;
update matches set kickoff_at = '2026-10-13 21:50:00-04' where match_day = 2 and match_number = 3;
update matches set kickoff_at = '2026-10-13 22:15:00-04' where match_day = 2 and match_number = 4;

update matches set kickoff_at = '2026-10-20 21:00:00-04' where match_day = 3 and match_number = 1;
update matches set kickoff_at = '2026-10-20 21:25:00-04' where match_day = 3 and match_number = 2;
update matches set kickoff_at = '2026-10-20 21:50:00-04' where match_day = 3 and match_number = 3;
update matches set kickoff_at = '2026-10-20 22:15:00-04' where match_day = 3 and match_number = 4;

update matches set kickoff_at = '2026-10-27 21:00:00-04' where match_day = 4 and match_number = 1;
update matches set kickoff_at = '2026-10-27 21:25:00-04' where match_day = 4 and match_number = 2;
update matches set kickoff_at = '2026-10-27 21:50:00-04' where match_day = 4 and match_number = 3;
update matches set kickoff_at = '2026-10-27 22:15:00-04' where match_day = 4 and match_number = 4;

update matches set kickoff_at = '2026-11-03 21:00:00-05' where match_day = 5 and match_number = 1;
update matches set kickoff_at = '2026-11-03 21:25:00-05' where match_day = 5 and match_number = 2;
update matches set kickoff_at = '2026-11-03 21:50:00-05' where match_day = 5 and match_number = 3;
update matches set kickoff_at = '2026-11-03 22:15:00-05' where match_day = 5 and match_number = 4;

update matches set kickoff_at = '2026-11-10 21:00:00-05' where match_day = 6 and match_number = 1;
update matches set kickoff_at = '2026-11-10 21:25:00-05' where match_day = 6 and match_number = 2;
update matches set kickoff_at = '2026-11-10 21:50:00-05' where match_day = 6 and match_number = 3;
update matches set kickoff_at = '2026-11-10 22:15:00-05' where match_day = 6 and match_number = 4;

-- ======== sql/migration_longterm_tracking.sql ========
-- Migration: long-term stat tracking foundations (see chat discussion on
-- "what to capture so 5 years of history stays trustworthy").
--
-- Adds:
--   1. match_appearances   — real per-match appearances (fixes GP being
--                            "team played" instead of "this player played")
--   2. player_notes_log    — historized fitness/injury + leave-plan notes
--                            (players.fitness_notes/leave_plan stay as the
--                            "current" snapshot; this table keeps history)
--   3. player_rating_log   — historized skill_rating/skill_level changes
--   4. suspensions         — card-driven or admin-issued match bans
--   5. season_awards       — top scorer / assists / golden glove / fair
--                            play / most improved / champion / runner-up
--   6. teams.is_active / players.is_active — archive instead of delete
--   7. team_head_to_head   — view for head-to-head tiebreaks
--   8. player_season_stats — rebuilt on match_appearances for accurate GP,
--                            adds clean_sheets

-- ---------- 1. Match appearances ----------
create table if not exists match_appearances (
  id uuid primary key default gen_random_uuid(),
  match_id uuid not null references matches(id) on delete cascade,
  player_id uuid not null references players(id) on delete cascade,
  team_id uuid not null references teams(id),
  started boolean not null default true,
  minutes_played int,                  -- optional; null = not tracked to the minute
  position_played text,                -- optional; this match's actual position
  is_captain boolean not null default false,
  created_at timestamptz not null default now(),
  unique (match_id, player_id)
);
alter table match_appearances enable row level security;
create policy "public read appearances" on match_appearances for select using (true);
create policy "admin write appearances" on match_appearances for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));

-- ---------- 2. Historized fitness/injury + leave-plan notes ----------
create table if not exists player_notes_log (
  id uuid primary key default gen_random_uuid(),
  player_id uuid not null references players(id) on delete cascade,
  note_type text not null check (note_type in ('fitness', 'leave_plan')),
  note text not null,
  recorded_at timestamptz not null default now(),
  resolved_at timestamptz               -- null = still open/current
);
alter table player_notes_log enable row level security;
create policy "public read player notes log" on player_notes_log for select using (true);
create policy "admin write player notes log" on player_notes_log for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));

-- ---------- 3. Historized skill rating/level ----------
create table if not exists player_rating_log (
  id uuid primary key default gen_random_uuid(),
  player_id uuid not null references players(id) on delete cascade,
  season_id uuid references seasons(id),
  skill_rating int,
  skill_level text,
  recorded_at timestamptz not null default now(),
  notes text
);
alter table player_rating_log enable row level security;
create policy "public read player rating log" on player_rating_log for select using (true);
create policy "admin write player rating log" on player_rating_log for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));

-- ---------- 4. Suspensions ----------
create table if not exists suspensions (
  id uuid primary key default gen_random_uuid(),
  player_id uuid not null references players(id) on delete cascade,
  season_id uuid not null references seasons(id) on delete cascade,
  reason text not null,
  matches_banned int not null default 1,
  start_match_id uuid references matches(id),
  created_at timestamptz not null default now()
);
alter table suspensions enable row level security;
create policy "public read suspensions" on suspensions for select using (true);
create policy "admin write suspensions" on suspensions for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));

-- ---------- 5. Season awards ----------
create table if not exists season_awards (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references seasons(id) on delete cascade,
  award_type text not null check (award_type in (
    'top_scorer', 'most_assists', 'golden_glove', 'fair_play',
    'most_improved', 'champion', 'runner_up', 'player_of_tournament'
  )),
  player_id uuid references players(id) on delete cascade,
  team_id uuid references teams(id) on delete cascade,
  notes text,
  created_at timestamptz not null default now(),
  check (player_id is not null or team_id is not null)
);
alter table season_awards enable row level security;
create policy "public read season awards" on season_awards for select using (true);
create policy "admin write season awards" on season_awards for all
  using (exists (select 1 from admins where user_id = auth.uid()))
  with check (exists (select 1 from admins where user_id = auth.uid()));

-- ---------- 5b. Audit log (who changed what, and when) ----------
create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  table_name text not null,
  record_id uuid not null,
  action text not null,             -- 'INSERT' | 'UPDATE' | 'DELETE'
  changed_by uuid,                  -- auth.uid() of the admin, if any
  changed_at timestamptz not null default now(),
  old_data jsonb,
  new_data jsonb
);
alter table audit_log enable row level security;
create policy "admin read audit log" on audit_log for select
  using (exists (select 1 from admins where user_id = auth.uid()));
-- No write policy for anyone — only the trigger function (SECURITY DEFINER)
-- inserts into this table, so even an admin's public-key session can't
-- tamper with the log directly.

create or replace function log_audit_event()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into audit_log (table_name, record_id, action, changed_by, old_data, new_data)
  values (
    TG_TABLE_NAME,
    coalesce((case when TG_OP = 'DELETE' then old.id else new.id end), gen_random_uuid()),
    TG_OP,
    auth.uid(),
    case when TG_OP in ('UPDATE', 'DELETE') then to_jsonb(old) else null end,
    case when TG_OP in ('INSERT', 'UPDATE') then to_jsonb(new) else null end
  );
  return coalesce(new, old);
end;
$$;

drop trigger if exists trg_audit_players on players;
create trigger trg_audit_players after insert or update or delete on players
  for each row execute function log_audit_event();

drop trigger if exists trg_audit_teams on teams;
create trigger trg_audit_teams after insert or update or delete on teams
  for each row execute function log_audit_event();

drop trigger if exists trg_audit_matches on matches;
create trigger trg_audit_matches after insert or update or delete on matches
  for each row execute function log_audit_event();

drop trigger if exists trg_audit_match_events on match_events;
create trigger trg_audit_match_events after insert or update or delete on match_events
  for each row execute function log_audit_event();

drop trigger if exists trg_audit_team_season_rosters on team_season_rosters;
create trigger trg_audit_team_season_rosters after insert or update or delete on team_season_rosters
  for each row execute function log_audit_event();

-- ---------- 6. Archive instead of delete ----------
alter table teams add column if not exists is_active boolean not null default true;
alter table players add column if not exists is_active boolean not null default true;

-- ---------- 7. Head-to-head view (for standings tiebreaks) ----------
create or replace view team_head_to_head as
select
  m.season_id,
  least(m.home_team_id, m.away_team_id) as team_a,
  greatest(m.home_team_id, m.away_team_id) as team_b,
  count(*) filter (
    where m.status = 'completed' and
      ((m.home_team_id = least(m.home_team_id, m.away_team_id) and m.home_score > m.away_score) or
       (m.away_team_id = least(m.home_team_id, m.away_team_id) and m.away_score > m.home_score))
  ) as team_a_wins,
  count(*) filter (
    where m.status = 'completed' and
      ((m.home_team_id = greatest(m.home_team_id, m.away_team_id) and m.home_score > m.away_score) or
       (m.away_team_id = greatest(m.home_team_id, m.away_team_id) and m.away_score > m.home_score))
  ) as team_b_wins,
  count(*) filter (where m.status = 'completed' and m.home_score = m.away_score) as draws
from matches m
where m.status in ('completed', 'forfeited')
group by m.season_id, least(m.home_team_id, m.away_team_id), greatest(m.home_team_id, m.away_team_id);

-- ---------- 8. player_season_stats: real GP from appearances, event stats
--              stay independent so nothing already logged goes to 0 just
--              because an appearance row hasn't been added for it yet.
--              (games_played falls back to the old "team played" count
--              whenever this player has zero rows in match_appearances for
--              that season/team, so existing seasons don't regress to 0
--              until appearances start getting logged.)
create or replace view player_season_stats as
select
  p.id as player_id,
  p.full_name,
  tsr.season_id,
  tsr.team_id,
  coalesce(
    nullif(count(distinct ma.match_id), 0),
    count(distinct m.id) filter (
      where m.status = 'completed'
      and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
    )
  ) as games_played,
  count(distinct me.id) filter (where me.event_type = 'goal') as goals,
  count(distinct me.id) filter (where me.event_type = 'assist') as assists,
  count(distinct me.id) filter (where me.event_type = 'yellow_card') as yellow_cards,
  count(distinct me.id) filter (where me.event_type = 'red_card') as red_cards,
  count(distinct me.id) filter (where me.event_type = 'player_of_match') as potm_awards,
  count(distinct me.id) filter (where me.event_type = 'save') as saves,
  count(distinct me.id) filter (where me.event_type = 'player_of_tournament') as tournament_awards,
  count(distinct ma.match_id) filter (
    where m.status = 'completed'
      and ((m.home_team_id = tsr.team_id and m.away_score = 0)
        or (m.away_team_id = tsr.team_id and m.home_score = 0))
  ) as clean_sheets
from players p
join team_season_rosters tsr on tsr.player_id = p.id
left join matches m on m.season_id = tsr.season_id
  and (m.home_team_id = tsr.team_id or m.away_team_id = tsr.team_id)
left join match_appearances ma on ma.player_id = p.id and ma.match_id = m.id
left join match_events me on me.player_id = p.id and me.match_id = m.id
group by p.id, p.full_name, tsr.season_id, tsr.team_id;

-- ======== sql/seed_players_batch8.sql ========
-- Batch 8: adds 1 new player (Bilal Yaser).
--
-- Card notes: jersey number given as "11 or 8" (two options) — both clash with
-- other cards (#11: Dhruv's "19 or 11"; #8: Pradnyal's "10 or 8"), flagged for
-- the admin to resolve on roster assignment. Position "Mid (CAM)" (attacking
-- midfielder) categorized as Center, matching how other midfielders are
-- categorized. Skill level "Inter." recorded as Intermediate. The small
-- "7/10" badge on the photo matches the 7/10 skill rating. Full name taken
-- from the file name (card only says "Bilal").

insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Bilal Yaser', 31, 'M', 'Mid (CAM)', 'Right', 'assets/players/bilal.jpg',
  'Jersey name "Bilal"; number given as "11 or 8" — #11 also on Dhruv''s card and #8 also on Pradnyal''s; flagged for the admin to resolve on roster assignment.',
  'Low', 7, 'Intermediate',
  'Played college tournaments and recreational', 'None', 'None',
  'Center'
);

-- ======== sql/seed_players_batch9.sql ========
insert into players (
  full_name, age, jersey_size, preferred_position, preferred_foot, photo_url, bio_notes,
  stamina_level, skill_rating, skill_level, playing_experience, fitness_notes, leave_plan,
  position_category
) values
(
  'Ajinkya P', 28, 'L', 'Mid', 'Right', 'assets/players/ajinkya.jpg',
  'Jersey name "Ajinkya P", #8. Card''s name field was left as the template placeholder ("Your Full Name") — used the jersey name; confirm full surname with the player. Jersey #8 is also on Kartik''s, Pradnyal''s and Bilal''s cards; flagged for the admin to resolve on roster assignment.',
  'Medium', 6, 'Beginner',
  'Have been playing since childhood, mostly pickup games', 'None', 'Out of town from Nov 5 - Nov 9',
  'Center'
);

-- ======== sql/seed_players_batch10.sql ========
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

-- ======== sql/migration_points_and_tiebreak.sql ========
-- Points: Win 2, Draw 1, Loss 0 (standings recalculate automatically from
-- completed matches, so nothing else is needed after a result is saved).
alter table seasons alter column points_win set default 2;
alter table seasons alter column points_draw set default 1;
alter table seasons alter column points_loss set default 0;
update seasons set points_win = 2, points_draw = 1, points_loss = 0;

-- (Penalty shoot-out tie-break lives in migration_tiebreak_shootouts.sql)

-- Safety: a match marked "completed" with blank scores must not hand both
-- teams a draw. Only count completed matches that actually have scores.
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
  where m.status = 'forfeited'
     or (m.status = 'completed' and m.home_score is not null and m.away_score is not null)
),
team_matches as (
  select
    season_id, team_id, match_id, status, goals_for, goals_against,
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

-- ======== sql/migration_tiebreak_shootouts.sql ========
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

-- ======== sql/migration_auction.sql ========
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

-- ======== sql/migration_auction_wheel.sql ========
-- Shared wheel: every visitor sees the same spin. The admin publishes the
-- spin (pool order, winner, landing offset) and each browser animates it.
alter table auction_state add column if not exists wheel_round int not null default 1;
alter table auction_state add column if not exists spin_seq int not null default 0;
alter table auction_state add column if not exists spin_pool jsonb;
alter table auction_state add column if not exists spin_winner_id uuid;
alter table auction_state add column if not exists spin_offset numeric not null default 0;
alter table auction_state add column if not exists spin_started_at timestamptz;

-- ======== sql/migration_map_schedule_teams.sql ========
-- Maps the schedule slots to the real teams:
--   Team A -> Renegades, Team B -> Muggles FC, Team C -> Scouts FC, Team D -> Desi Steelers FC
-- Every match (and anything recorded against a match) is moved to the real team,
-- then the four placeholder teams are hidden (is_active = false, nothing is deleted).
-- Safe to re-run: once the placeholders have no matches, it changes nothing.
do $$
declare
  m record;
  tbl text;
begin
  for m in
    select a.id as old_id, b.id as new_id, a.name as old_name, b.name as new_name
    from (values ('Team A','Renegades'),('Team B','Muggles FC'),('Team C','Scouts FC'),('Team D','Desi Steelers FC')) v(o,n)
    join teams a on a.name = v.o
    join teams b on b.name = v.n
  loop
    update matches set home_team_id = m.new_id where home_team_id = m.old_id;
    update matches set away_team_id = m.new_id where away_team_id = m.old_id;
    update matches set forfeited_by_team_id = m.new_id where forfeited_by_team_id = m.old_id;
    foreach tbl in array array['match_events','match_appearances','season_awards','tiebreak_shootout_order'] loop
      if to_regclass('public.' || tbl) is not null then
        execute format('update %I set team_id = $1 where team_id = $2', tbl) using m.new_id, m.old_id;
      end if;
    end loop;
    update teams set is_active = false where id = m.old_id;
    raise notice 'Mapped % -> %', m.old_name, m.new_name;
  end loop;
end $$;

-- Check: every scheduled match should now list real teams only.
select t.name, t.is_active,
  (select count(*) from matches m where m.home_team_id = t.id or m.away_team_id = t.id) as matches
from teams t order by t.is_active desc, t.name;

-- ======== sql/update_match_times_10min_halves.sql ========
-- 10-minute halves: new kickoff times, US Eastern (EDT until 1 Nov, EST after; handled automatically).
--   Match 1 = 8:30 PM, Match 2 = 9:00 PM, Match 3 = 9:30 PM, Match 4 = 10:00 PM
-- Keeps each match day's existing date, only the time changes.
update matches
set kickoff_at = (
  ((kickoff_at at time zone 'America/New_York')::date
    + (case match_number when 1 then time '20:30' when 2 then time '21:00' when 3 then time '21:30' when 4 then time '22:00' end)
  ) at time zone 'America/New_York')
where kickoff_at is not null and match_number between 1 and 4;

select match_day, match_number,
  to_char(kickoff_at at time zone 'America/New_York', 'Dy DD Mon YYYY HH12:MI AM') as eastern_kickoff
from matches order by match_day, match_number;

-- ======== sql/preprod/rosters_snapshot.sql ========
-- PREPROD ONLY. Copies the live team rosters and auction prices (as of 30 Sep 2026)
-- into the preprod database: 4 owners + 33 auctioned players, 780 points spent.
-- Safe to re-run.
insert into team_season_rosters (season_id, team_id, player_id, is_owner, auction_price)
select s.id, t.id, p.id, v.is_owner, v.price
from (values
  ('Muggles FC', 'Amritpal Singh', true, null::int),
  ('Scouts FC', 'Bhagyesh Rane', true, null::int),
  ('Desi Steelers FC', 'Nasiq', true, null::int),
  ('Renegades', 'Varun', true, null::int),
  ('Renegades', 'Minti', false, 20),
  ('Scouts FC', 'Ketan Gaikwad', false, 10),
  ('Desi Steelers FC', 'Ketan Shilimkar', false, 4),
  ('Muggles FC', 'Preetesh Duvvuri', false, 8),
  ('Desi Steelers FC', 'Vamshi', false, 30),
  ('Renegades', 'Nuhu Okikiri', false, 24),
  ('Renegades', 'Shailesh', false, 12),
  ('Desi Steelers FC', 'Vija', false, 28),
  ('Scouts FC', 'Pradnyal Gandhi', false, 82),
  ('Muggles FC', 'Dheeraj R Vatti', false, 26),
  ('Muggles FC', 'Vishnu Mohan', false, 72),
  ('Scouts FC', 'Kishor Ghadge', false, 2),
  ('Desi Steelers FC', 'Vignesh', false, 22),
  ('Desi Steelers FC', 'Kaushik Apte', false, 40),
  ('Muggles FC', 'Dhruv', false, 44),
  ('Renegades', 'Chirag', false, 72),
  ('Scouts FC', 'Sagar SJ', false, 30),
  ('Scouts FC', 'Kartik', false, 32),
  ('Scouts FC', 'Sandeep Naik', false, 10),
  ('Renegades', 'Prajna', false, 24),
  ('Renegades', 'Sangram Ghewade', false, 14),
  ('Desi Steelers FC', 'Rishabh Devgon', false, 50),
  ('Renegades', 'Dhananjay', false, 26),
  ('Muggles FC', 'Ashu', false, 16),
  ('Scouts FC', 'Bilal Yaser', false, 24),
  ('Desi Steelers FC', 'Ajinkya P', false, 10),
  ('Muggles FC', 'Ayush', false, 8),
  ('Desi Steelers FC', 'Sagar', false, 10),
  ('Muggles FC', 'Taranjot Singh Dang', false, 10),
  ('Muggles FC', 'Rohith', false, 10),
  ('Renegades', 'Vivek', false, 2),
  ('Renegades', 'Rajeev Singh', false, 6),
  ('Scouts FC', 'Jitendra', false, 2)
) v(team, player, is_owner, price)
join seasons s on s.is_current
join teams t on t.name = v.team
join players p on p.full_name = v.player
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = excluded.is_owner, auction_price = excluded.auction_price;

-- ======== CHECK: expect players 37, active teams 4, matches 24, owners 4, sold 33, points 780 ========
commit;
select
  (select count(*) from players) as players,
  (select count(*) from teams where is_active) as active_teams,
  (select count(*) from matches) as matches,
  (select count(*) from team_season_rosters where is_owner) as owners,
  (select count(*) from team_season_rosters where not is_owner) as sold,
  (select sum(auction_price) from team_season_rosters) as points;
