-- ============================================================================
-- ROLLBACK for sql/migration_live_scoring.sql  ("Rollback Live scoring")
-- Removes the live-scoring rules, policies, co-admin accounts' access and the edit lock.
-- KEEPS all your data: matches, events, lineups, scores, the audit_log history, and the
-- (harmless, unused) columns live_phase, clock_*, time_remaining, created_by, changed_by_label.
-- Co-admin sign-ups (the coadmins table) are deleted; their logins can be removed in
-- Supabase > Authentication > Users if you want. Safe to re-run.
-- Run it together with reverting the website code (git revert of the live-scoring commit).
-- ============================================================================

-- any match still shown as live goes back to a normal scheduled match
update matches set live_phase = null, clock_running = false where live_phase is not null and status = 'scheduled';

drop trigger if exists trg_matches_live_guard on matches;
drop trigger if exists trg_match_events_live_guard on match_events;
drop trigger if exists trg_audit_match_appearances on match_appearances;
drop trigger if exists trg_audit_coadmins on coadmins;
drop trigger if exists trg_audit_note_stamp on audit_log;

drop policy if exists "live editors update matches" on matches;
drop policy if exists "live editors write events" on match_events;
drop policy if exists "live editors write appearances" on match_appearances;
drop policy if exists "live editors read audit" on audit_log;
drop policy if exists "live editors add notes" on audit_log;

drop table if exists live_locks;
drop table if exists coadmins cascade;

-- audit trigger function back to its original form
create or replace function log_audit_event() returns trigger
language plpgsql security definer set search_path = public
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
end $$;

drop function if exists matches_live_guard();
drop function if exists match_events_live_guard();
drop function if exists audit_note_stamp();
drop function if exists log_audit_coadmin();
drop function if exists is_live_editor();
drop function if exists live_editor_label();
drop function if exists live_half_seconds();
drop function if exists server_now();
drop function if exists is_admin();

do $$
begin
  begin alter publication supabase_realtime drop table match_appearances; exception when others then null; end;
end $$;

-- player stats view back to counting every event
create or replace view player_season_stats as
SELECT p.id AS player_id,
    p.full_name,
    tsr.season_id,
    tsr.team_id,
    count(DISTINCT m.id) FILTER (WHERE m.status = 'completed'::text AND (m.home_team_id = tsr.team_id OR m.away_team_id = tsr.team_id) AND (ma.status = 'played'::text OR ma.id IS NULL AND NOT (EXISTS ( SELECT 1
           FROM match_appearances x
          WHERE x.match_id = m.id AND x.team_id = tsr.team_id)))) AS games_played,
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
     LEFT JOIN match_events me ON me.player_id = p.id AND me.match_id = m.id
  GROUP BY p.id, p.full_name, tsr.season_id, tsr.team_id;
