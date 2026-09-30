#!/bin/sh
# Rebuilds preprod_setup.sql: every live migration + seed in the order they were
# run on live, then the live roster/auction snapshot, then a check query.
# Run from the repo root: sh sql/preprod/build_preprod_setup.sh
set -e
OUT=sql/preprod/preprod_setup.sql
FILES="schema migration_player_attributes migration_position_categories migration_page_views
seed_players_batch1 seed_players_batch2 seed_players_batch3 seed_players_batch4 seed_players_batch5
fix_shailesh_kaushik seed_schedule seed_players_batch6 migration_potm_awards update_match_dates
update_team1_desi_steelers add_teams_muggles_scouts seed_players_batch7 migration_saves_and_tournament_award
untag_desi_steelers_from_team_a add_team_renegades update_match_times migration_longterm_tracking
seed_players_batch8 seed_players_batch9 seed_players_batch10 migration_points_and_tiebreak
migration_tiebreak_shootouts migration_auction migration_auction_wheel migration_map_schedule_teams
update_match_times_10min_halves"
{
  echo "-- PHALANX LEAGUE SOCCER - PREPROD DATABASE SETUP (generated; do not edit by hand)"
  echo "-- Run ONCE in the PREPROD Supabase project's SQL Editor. NEVER run it on the live project."
  echo "-- All-or-nothing: if any statement fails, nothing is kept and it can simply be run again."
  echo "begin;"
  echo "do \$\$ begin if to_regclass('public.players') is not null then raise exception 'STOP: this database already has league tables. The preprod setup only runs on a brand-new, empty Supabase project.'; end if; end \$\$;"
  echo
  for f in $FILES; do echo "-- ======== sql/$f.sql ========"; cat "sql/$f.sql"; echo; done
  echo "-- ======== sql/preprod/rosters_snapshot.sql ========"; cat sql/preprod/rosters_snapshot.sql; echo
  cat <<'Q'
-- ======== CHECK: expect players 37, active teams 4, matches 24, owners 4, sold 33, points 780 ========
Q
  echo "commit;"
  cat <<'Q'
select
  (select count(*) from players) as players,
  (select count(*) from teams where is_active) as active_teams,
  (select count(*) from matches) as matches,
  (select count(*) from team_season_rosters where is_owner) as owners,
  (select count(*) from team_season_rosters where not is_owner) as sold,
  (select sum(auction_price) from team_season_rosters) as points;
Q
} > "$OUT"
echo "wrote $OUT ($(wc -l < $OUT) lines)"
