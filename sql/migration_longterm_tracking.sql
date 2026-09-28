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
