-- ============================================================================
-- LIVE SCORING (live match desk for admin + co-admin)
-- Run in the Supabase SQL editor. Safe to re-run.
-- Needs these earlier migrations (already on live): migration_day2_fields, migration_attendance, migration_longterm_tracking.
-- Undo with sql/rollback_live_scoring.sql.
--
-- What it adds
--  * co-admins: people who sign up (email + password) and are APPROVED by an admin.
--    They can run live matches only; they can not touch teams, players, rosters,
--    seasons, awards, the auction, or any match that is not scheduled/live.
--  * live clock + phase columns on matches (live_phase, clock_*), and time_remaining on events
--  * server-side rules so a mistake in the browser can never corrupt a result
--      - event times (minute/second) are computed by the database from half + time remaining
--      - the final score is computed by the database from the goal events when a match is confirmed
--      - co-admins can only move a match through h1 -> ht -> h2 -> ft -> completed
--  * audit trail: reuses the existing audit_log (who, what, when) and extends it to
--    match_appearances, adds the editor's name, and lets editors add a typed "reason" note
--  * edit lock (live_locks) so two people don't both score the same match by accident
--  * realtime publication for matches / match_events / match_appearances
-- ============================================================================

-- ---------- 1. who is allowed ----------
create table if not exists coadmins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null,
  email text,
  status text not null default 'pending' check (status in ('pending','approved','revoked')),
  requested_at timestamptz not null default now(),
  decided_at timestamptz,
  decided_by uuid
);
alter table coadmins enable row level security;

create or replace function is_admin() returns boolean
language sql stable security definer set search_path = public
as $$ select exists (select 1 from admins where user_id = auth.uid()) $$;

create or replace function is_live_editor() returns boolean
language sql stable security definer set search_path = public
as $$ select is_admin() or exists (select 1 from coadmins where user_id = auth.uid() and status = 'approved') $$;

create or replace function live_editor_label() returns text
language sql stable security definer set search_path = public, auth
as $$ select coalesce(
  (select display_name from admins where user_id = auth.uid()),
  (select display_name from coadmins where user_id = auth.uid()),
  (select email from auth.users where id = auth.uid()),
  'system') $$;

create or replace function server_now() returns timestamptz
language sql stable as $$ select now() $$;

-- length of one half, in seconds (10 minutes). Change here AND LIVE_HALF_SECONDS in public/js/live_common.js.
create or replace function live_half_seconds() returns int
language sql immutable as $$ select 600 $$;

drop policy if exists "coadmin read own or admin" on coadmins;
create policy "coadmin read own or admin" on coadmins for select using (user_id = auth.uid() or is_admin());
drop policy if exists "coadmin request access" on coadmins;
create policy "coadmin request access" on coadmins for insert to authenticated
  with check (user_id = auth.uid() and status = 'pending');
drop policy if exists "admin manage coadmins" on coadmins;
create policy "admin manage coadmins" on coadmins for update using (is_admin()) with check (is_admin());
drop policy if exists "admin delete coadmins" on coadmins;
create policy "admin delete coadmins" on coadmins for delete using (is_admin());

-- ---------- 2. live columns ----------
alter table matches add column if not exists live_phase text;            -- null = not live; h1 | ht | h2 | ft
alter table matches add column if not exists clock_rem int;              -- seconds left in the current half, as of clock_at
alter table matches add column if not exists clock_running boolean not null default false;
alter table matches add column if not exists clock_at timestamptz;       -- set by the database whenever the clock changes
alter table matches drop constraint if exists matches_live_phase_check;
alter table matches add constraint matches_live_phase_check check (live_phase is null or live_phase in ('h1','ht','h2','ft'));
alter table matches drop constraint if exists matches_clock_rem_check;
alter table matches add constraint matches_clock_rem_check check (clock_rem is null or clock_rem between 0 and 600);

alter table match_events add column if not exists time_remaining int;    -- what the admin typed (seconds left in that half)
alter table match_events add column if not exists created_by uuid default auth.uid();
alter table match_events drop constraint if exists match_events_time_remaining_check;
alter table match_events add constraint match_events_time_remaining_check check (time_remaining is null or time_remaining between 0 and 600);

-- ---------- 3. rules enforced by the database ----------
-- 3a. matches: clock stamp, who may change what, final score from events
create or replace function matches_live_guard() returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  h int; a int;
  allowed text[] := array['toss_winner_team_id','toss_choice','live_phase','clock_rem','clock_running','clock_at','status','home_score','away_score'];
begin
  -- (auth.uid() is null = the Supabase SQL editor / service role: allowed, so your own SQL scripts keep working)
  if auth.uid() is not null and not is_admin() then
    if not is_live_editor() then
      raise exception 'Not allowed';
    end if;
    -- a co-admin may only change live/toss/result fields
    if (to_jsonb(new) - allowed) is distinct from (to_jsonb(old) - allowed) then
      raise exception 'Co-admins can only change live match fields';
    end if;
    if old.status <> 'scheduled' then
      raise exception 'This match is already finished; only an admin can change it';
    end if;
    -- phase can only move forward one step at a time (or stay)
    if new.live_phase is distinct from old.live_phase then
      if (coalesce(old.live_phase,'-') || '>' || coalesce(new.live_phase,'-')) not in ('->h1','h1>ht','ht>h2','h2>ft','ft>-')
         or (old.live_phase = 'ft' and new.status is distinct from 'completed') then
        raise exception 'Invalid match phase change % -> %', coalesce(old.live_phase,'none'), coalesce(new.live_phase,'none');
      end if;
    end if;
    if new.status is distinct from old.status and not (new.status = 'completed' and old.live_phase = 'ft') then
      raise exception 'A match can only be confirmed from full time';
    end if;
    if old.live_phase is null and new.live_phase = 'h1' and (new.toss_winner_team_id is null or new.toss_choice is null) then
      raise exception 'Record the toss before kick-off';
    end if;
  end if;

  if new.live_phase is distinct from old.live_phase
     or new.clock_rem is distinct from old.clock_rem
     or new.clock_running is distinct from old.clock_running then
    new.clock_at := now();
  end if;

  -- confirming a live match: the score always comes from the goal events, never from the browser
  if new.status = 'completed' and old.status = 'scheduled' and old.live_phase is not null then
    select count(*) filter (where (event_type = 'goal' and team_id = new.home_team_id) or (event_type = 'own_goal' and team_id = new.away_team_id)),
           count(*) filter (where (event_type = 'goal' and team_id = new.away_team_id) or (event_type = 'own_goal' and team_id = new.home_team_id))
      into h, a from match_events where match_id = new.id;
    new.home_score := h; new.away_score := a;
    new.live_phase := null; new.clock_running := false; new.clock_at := now();
  end if;
  return new;
end $$;
drop trigger if exists trg_matches_live_guard on matches;
create trigger trg_matches_live_guard before update on matches
  for each row execute function matches_live_guard();

-- 3b. events: minute/second come from half + time remaining; co-admin limits
create or replace function match_events_live_guard() returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  ph text; el int; hs int := live_half_seconds();
begin
  if tg_op <> 'DELETE' and new.time_remaining is not null then
    if new.half is null or new.half not in (1,2) then raise exception 'Half must be 1 or 2'; end if;
    el := (case when new.half = 1 then 0 else hs end) + (hs - new.time_remaining);
    new.minute := el / 60; new.second := el % 60;
  end if;
  if auth.uid() is not null and not is_admin() then
    select live_phase into ph from matches where id = (case when tg_op = 'DELETE' then old.match_id else new.match_id end);
    if tg_op <> 'DELETE' and new.half is not null then
      if new.half = 2 and ph = 'h1' then raise exception 'Second-half event during the first half'; end if;
    end if;
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;
drop trigger if exists trg_match_events_live_guard on match_events;
create trigger trg_match_events_live_guard before insert or update or delete on match_events
  for each row execute function match_events_live_guard();

-- ---------- 4. row level security for co-admins (admins keep their existing full policies) ----------
drop policy if exists "live editors update matches" on matches;
create policy "live editors update matches" on matches for update
  using (is_live_editor() and status = 'scheduled')
  with check (is_live_editor() and status in ('scheduled','completed'));

drop policy if exists "live editors write events" on match_events;
create policy "live editors write events" on match_events for all
  using (is_live_editor() and exists (select 1 from matches m where m.id = match_events.match_id and m.live_phase is not null))
  with check (is_live_editor() and exists (select 1 from matches m where m.id = match_events.match_id and m.live_phase is not null));

drop policy if exists "live editors write appearances" on match_appearances;
create policy "live editors write appearances" on match_appearances for all
  using (is_live_editor() and exists (select 1 from matches m where m.id = match_appearances.match_id and m.status = 'scheduled'))
  with check (is_live_editor() and exists (select 1 from matches m where m.id = match_appearances.match_id and m.status = 'scheduled'));

-- ---------- 5. audit trail ----------
alter table audit_log add column if not exists changed_by_label text;

create or replace function log_audit_event() returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  insert into audit_log (table_name, record_id, action, changed_by, changed_by_label, old_data, new_data)
  values (
    TG_TABLE_NAME,
    coalesce((case when TG_OP = 'DELETE' then old.id else new.id end), gen_random_uuid()),
    TG_OP,
    auth.uid(),
    live_editor_label(),
    case when TG_OP in ('UPDATE', 'DELETE') then to_jsonb(old) else null end,
    case when TG_OP in ('INSERT', 'UPDATE') then to_jsonb(new) else null end
  );
  return coalesce(new, old);
end $$;

drop trigger if exists trg_audit_match_appearances on match_appearances;
create trigger trg_audit_match_appearances after insert or update or delete on match_appearances
  for each row execute function log_audit_event();
create or replace function log_audit_coadmin() returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  insert into audit_log (table_name, record_id, action, changed_by, changed_by_label, old_data, new_data)
  values ('coadmins', coalesce(case when TG_OP = 'DELETE' then old.user_id else new.user_id end, gen_random_uuid()), TG_OP, auth.uid(), live_editor_label(),
    case when TG_OP in ('UPDATE','DELETE') then to_jsonb(old) else null end,
    case when TG_OP = 'UPDATE' then to_jsonb(new) else null end);
  return coalesce(new, old);
end $$;
drop trigger if exists trg_audit_coadmins on coadmins;
create trigger trg_audit_coadmins after update or delete on coadmins
  for each row execute function log_audit_coadmin();

-- editors can read the match-related audit rows; typed reasons are stored as 'live_note' rows
drop policy if exists "live editors read audit" on audit_log;
create policy "live editors read audit" on audit_log for select
  using (is_live_editor() and table_name in ('matches','match_events','match_appearances','live_note'));
drop policy if exists "live editors add notes" on audit_log;
create policy "live editors add notes" on audit_log for insert to authenticated
  with check (is_live_editor() and table_name = 'live_note');

-- the server stamps who/when on notes so they can not be forged
create or replace function audit_note_stamp() returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  if new.table_name = 'live_note' then
    new.changed_by := auth.uid(); new.changed_at := now(); new.changed_by_label := live_editor_label(); new.action := 'NOTE';
    new.old_data := null;
  end if;
  return new;
end $$;
drop trigger if exists trg_audit_note_stamp on audit_log;
create trigger trg_audit_note_stamp before insert on audit_log for each row execute function audit_note_stamp();

-- ---------- 6. edit lock (one active scorer per match) ----------
create table if not exists live_locks (
  match_id uuid primary key references matches(id) on delete cascade,
  user_id uuid not null,
  label text not null,
  beat_at timestamptz not null default now()
);
alter table live_locks enable row level security;
drop policy if exists "editors read locks" on live_locks;
create policy "editors read locks" on live_locks for select using (is_live_editor());
drop policy if exists "editors write locks" on live_locks;
create policy "editors write locks" on live_locks for all
  using (is_live_editor()) with check (is_live_editor() and user_id = auth.uid());

-- ---------- 7. realtime ----------
do $$
begin
  begin alter publication supabase_realtime add table matches; exception when others then null; end;
  begin alter publication supabase_realtime add table match_events; exception when others then null; end;
  begin alter publication supabase_realtime add table match_appearances; exception when others then null; end;
end $$;

-- ---------- 8. player stats ignore events of a match until its result is confirmed ----------
-- (also: a completed match with NO lineup yet counts as 'details pending' = nobody has a game played until the lineup is entered)
-- (a live match keeps status 'scheduled', so goals/cards typed live do not move Ranking / Season Stats
--  until the match is confirmed, exactly like the Standings)
create or replace view player_season_stats as
SELECT p.id AS player_id,
    p.full_name,
    tsr.season_id,
    tsr.team_id,
    count(DISTINCT m.id) FILTER (WHERE m.status = 'completed'::text AND (m.home_team_id = tsr.team_id OR m.away_team_id = tsr.team_id) AND ma.status = 'played'::text) AS games_played,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'goal'::text) AS goals,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'assist'::text) AS assists,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'yellow_card'::text) AS yellow_cards,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'red_card'::text) AS red_cards,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'player_of_match'::text) AS potm_awards,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'save'::text) AS saves,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'player_of_tournament'::text) AS tournament_awards,
    count(DISTINCT ma.match_id) FILTER (WHERE ma.status = 'played'::text AND m.status = 'completed'::text AND (m.home_team_id = tsr.team_id AND m.away_score = 0 OR m.away_team_id = tsr.team_id AND m.home_score = 0)) AS clean_sheets,
    count(DISTINCT ma.match_id) FILTER (WHERE ma.status = 'rested'::text AND m.status = 'completed'::text) AS rested,
    count(DISTINCT ma.match_id) FILTER (WHERE ma.status = 'absent'::text AND m.status = 'completed'::text) AS absent,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'own_goal'::text) AS own_goals,
    count(DISTINCT me.id) FILTER (WHERE me.event_type = 'foul'::text) AS fouls
   FROM players p
     JOIN team_season_rosters tsr ON tsr.player_id = p.id
     LEFT JOIN matches m ON m.season_id = tsr.season_id AND (m.home_team_id = tsr.team_id OR m.away_team_id = tsr.team_id)
     LEFT JOIN match_appearances ma ON ma.player_id = p.id AND ma.match_id = m.id
     LEFT JOIN match_events me ON me.player_id = p.id AND me.match_id = m.id AND m.status = 'completed'
  GROUP BY p.id, p.full_name, tsr.season_id, tsr.team_id;
