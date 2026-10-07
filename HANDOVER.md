# Phalanx League Soccer – Handover (as of 30 Sep 2026)

Paste this whole file into a new chat and say "continue from this handover".

## 1. The project
Static site (HTML/CSS/JS) + Supabase, hosted on GitHub Pages.
- Repo: `phalanxleaguesoccer/s1fall2026` (local clone `/home/claude/s1fall2026` in the cloud workspace; re-clone if missing).
- Live: https://phalanxleaguesoccer.github.io/S1Fall2026/
- Deploy: push to `main` -> GitHub Actions publishes `public/` (~1 min). Push prints a harmless "repository moved" notice.
- Commit messages end with:
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01Rh1kHtbocTxTwX1ScBHyFQ`
- The shell cannot reach Supabase (network allowlist), so all database changes are given to the owner as SQL to paste into the Supabase SQL Editor. The repo/site source is public.

## 2. Working preferences (owner)
- Wants honest assessment, pushback when wrong, "mixed evidence" said plainly.
- Asks for a prototype/screenshot and approval BEFORE deploying visual changes.
- Wants copy-paste SQL for anything touching the database; wants bugs tested ("test the whole website").
- Times are shown in US Eastern (America/New_York), whatever the viewer's timezone.

## 3. Rules implemented
- Points: Win 2, Draw 1, Loss 0. Standings update automatically from completed matches (both scores required) and forfeits.
- Tie-break order: goal difference -> goals scored -> goals conceded -> head-to-head -> penalty shoot-out.
- Shoot-outs are never played in matches; only a last resort after the whole tournament is complete, for teams still tied, stored as a unique order (table `tiebreak_shootout_order`, admin card "Tie-break Penalty Shoot-out") so every team ends with a unique rank.

## 4. Teams
Real teams: Desi Steelers FC (owner Nasiq), Muggles FC (Amritpal Singh), Scouts FC (Bhagyesh Rane), Renegades (Varun).
The schedule (24 matches, 12 each for Team A/B/C/D) still points at placeholder teams until the mapping SQL is run:
Team A -> Renegades, Team B -> Muggles FC, Team C -> Scouts FC, Team D -> Desi Steelers FC.
SQL is in `sql/migration_map_schedule_teams.sql` (idempotent; moves matches and match-linked rows, then hides Team A-D via is_active=false).

## 5. Auction (completed)
- Each team had 200 points; owners count at 0. Sale price is subtracted from the team budget.
- The live auction (wheel, admin sell/unsold/undo/reset, Round 2, shared spin for viewers, sound, profile panel, Minti reserved at pick #22) was built and tested.
- The auction is now CLOSED: `var AUCTION_CLOSED = true;` near the top of the script in `public/auction.html`. Admin and visitors see only "Teams & budgets" and "Auction feed". To reopen a future auction set it to `false`.
  This is a site-only lock; the database would still accept auction writes from an admin. Database lock SQL was offered but not requested.
- Player profile: header shows "Plays for <Team> : Auction sold for N pts" (or ": Team owner") for the current season; Current Season Stats and season-by-season tables have "Bought by" and "Sold for"; All Stats has an "Auction history" block that shows for both filters.
- SQL files for the auction: `sql/migration_auction.sql`, `sql/migration_auction_wheel.sql` (owner should confirm they were run; the feed on the live site working suggests yes).

## 6. Player profiles ingestion (ongoing workflow)
User sends a profile .pptx. Extract data + headshot, avoid duplicates, adapt to DB conventions, flag jersey conflicts/placeholders in `bio_notes`, write seed SQL in `sql/seed_players_batchN.sql` (last: batch10), photo in `public/assets/players/`, commit/push, give the owner the copy-paste SQL.

## 7. Testing setup (in `tests/site/`, see its README)
Playwright + Chromium with a fake in-memory Supabase client (`fake_supabase.js`), a local server on port 8137, fixtures in `fixtures.py`.
- `suite.py` – 81 checks of the public + admin site. Last run: all pass.
- `auction_tests.py` – 62 checks of live auction logic (runs against an "open" copy of the page; ~5 min; use `timeout 590`).
- `extras_tests.py` – 12 checks (side-list bug, Minti at pick 22; ~5 min).
- `closed_tests.py` – 13 checks for the closed auction page and profile auction lines.
- Run test scripts one at a time (they share the port). Do not use `pkill -f <script name>` in the same shell command.
- Standing SQL view logic was also verified on a local Postgres 16.

## 8. Open items / next steps
1. Owner to run `sql/migration_map_schedule_teams.sql` in Supabase, then paste the final check query result (each real team should show 12 matches, Team A-D inactive with 0). Then verify Matches/Schedule/Standings pages read correctly with real names.
2. Owner asked (not yet done): change the site theme to white. Estimate given ~15-25 min; recommended white background keeping green/amber accents; colors mostly in `:root` of `public/css/app.css`, plus ~26 hard-coded colors in `public/auction.html`. Show a screenshot and get approval before pushing.
3. "Build it" for the completed-match page / match-result entry flow – not started.
4. Unanswered questions: whether owners should appear in the team squad grid (currently hidden there); team squad-size cap; whether to run `sql/migration_tiebreak_shootouts.sql` (confirm it was run); a weekly Supabase export backup (offered).
5. Player data to resolve at roster time: jersey conflicts (#8 shared by Kartik/Pradnyal/Bilal/Ajinkya, plus #10, #7, #18, #12, #19, #11 etc.); confirm full names for Kartik, Kaushik, Ajinkya.
6. Optional: SQL to lock auction writes in the database.

## 9. Key files
- `public/index.html` standings + tie-break logic; `matches.html`, `match.html`, `teams.html`, `team.html`, `players.html`, `player.html`, `auction.html`
- `public/js/common.js` (nav, Eastern-time helpers), `public/js/supabase-client.js`, `public/css/app.css`
- `public/admin/dashboard.html/.js` admin tools (match results, shoot-out order)
- `sql/` all migrations and seeds


## Update 7 Oct 2026
- Day 1 results: `sql/day1_results.sql` (Step 1 scores, Step 2 player events - re-run Step 2 after the Stats page change so events keep their entry order and half is not guessed). Standings show shared ranks (1,2,2,4) for teams level on all criteria until the final shoot-out. Table columns: Pts P W D L GD GF GA.
- New Stats page (`public/stats.html`, nav "Stats"): Milestones with tabs Goals / Assists / Yellow / Red; Season filter + View filter (Tournament default or a team); nth numbering; Details button (season, match, opponent, final score, half, minute, assist link, tournament vs team number). Tests: `tests/site/stats_tests.py`.
- Fixed: `match_events` has two foreign keys to players, so embeds must use `players!match_events_player_id_fkey(*)` (match page + admin events list updated).
- Kickoffs for 10-minute halves: `sql/update_match_times_10min_halves.sql`. Placeholder team removal: `sql/remove_placeholder_teams.sql`.
