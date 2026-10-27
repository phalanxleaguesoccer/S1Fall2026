# SQL tests (real Postgres)
`live_scoring_rls.sh` runs the live-scoring database rules against a scratch Postgres 16 (as admin, approved / pending / revoked co-admin, outsider and anonymous visitor).
Setup (once): start a scratch cluster on port 5544 (socket dir /tmp/pgs), create database `lt`, stub the Supabase pieces
(roles `anon`/`authenticated`, schema `auth` with `users` and `uid()` reading `request.jwt.claim.sub`, an empty `supabase_realtime` publication),
then apply `sql/preprod/preprod_setup.sql`, `migration_day2_fields`, `migration_attendance`, `migration_own_goals`, `migration_fouls`, `migration_captains`, `migration_injuries`, and finally `migration_live_scoring.sql`.
Then run `tests/sql/live_scoring_rls.sh` (59 checks).
