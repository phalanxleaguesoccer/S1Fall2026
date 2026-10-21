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

## Attendance (Played / Rested / Absent) - 7 Oct 2026
- SQL order: `sql/migration_attendance.sql` (status column + player_season_stats now has rested/absent; games_played counts only matches actually played; a completed match with NO lineup entered counts everyone as played), then `sql/day1_lineups.sql` (Day 1 lineups + Chirag yellow card = second half).
- Site: match page "Lineups" card, schedule shows Rested/Absent counts, profile tables have Rested/Absent columns, team squad cards show Played/Rested/Absent, Stats page has Rested and Absent tabs (list + per-player totals), admin Records tab has a bulk "Match Lineup" form (default Played, saves whole squads).
- Name mapping used: Vamsi=Vamshi, Ayush Jain=Ayush, Vivek Shrivatava=Vivek, Kaushik Apte=Kaushik, Rishab Devgon=Rishabh Devgon, Sagar (Desi)=Sagar, Sagar SJ (Scouts).
- Tests: `tests/site/attendance_tests.py` (21).


## Own goals (added 14 Oct)
- Event type `own_goal`: player_id = the player who scored it, team_id = his OWN team; it counts for the opponent and is not a goal for him.
- Run `sql/migration_own_goals.sql` (adds `own_goals` column to `player_season_stats`).
- Shown on: match page (OWN GOAL chip, `(og)` under the scoreboard, Own goals stat row, OG column), Stats > Milestones > Own goals tab, player profile OG column, admin event form.
- The match score itself is still the score entered on the match; enter it including the own goal.
- Clean sheets are not tracked and were removed from all pages.

## Fouls (added 14 Oct)
- Event type `foul` (player_id = who committed it), recorded only when entered as a foul. Yellow/red cards are separate and are NOT counted as fouls (see the later update below).
- Run `sql/migration_fouls.sql`: adds `fouls` to `player_season_stats`.
- Shown on: match page (Fouls stat bar, FL column, FOUL chip, "N fouls" line), Stats > Milestones > Fouls tab (details say which card, if any), Season Stats Fouls and OG columns (not part of ranking), player profile Fouls column, team page totals (OG and Fouls).

## Week 2 (Match Day 2 = Matches 5-8) (added 14 Oct)
- New: toss (`matches.toss_winner_team_id`, `toss_choice` side|kickoff), event seconds (`match_events.second`) and penalty flag (`is_penalty`). Run `sql/migration_day2_fields.sql`, then `sql/day2_results.sql` (scores, toss, lineups, events; re-runnable; validates every name/squad).
- Match page shows the toss, times as m:ss when seconds were entered, "(pen)" under the scoreboard and "Penalty" on the goal row; an own goal can carry an assist (assist.related_player_id = own-goal scorer).
- Admin: event form has Second + Penalty; the Match Lineup card has Toss won by / Chose.
- "Saurabh" in the sheet = Vija (Desi Steelers FC); "Rishab" = Rishabh Devgon; "Amrit" = Amritpal Singh; "Vamsi" = Vamshi.


## Update (14 Oct, later): cards are NOT fouls
- A foul is only recorded when entered as a foul. Yellow/red cards are separate and never counted as fouls. Run `sql/remove_card_fouls.sql` once to delete the fouls that had been created automatically next to cards. The admin 'also a foul' checkbox was removed.

## Ranking (In QA) — Stats sub-page `stats.html#ranking`
- Third Stats sub-page, same filters/columns as Season Stats plus **Points** (after Team). Code shares one parametrized board (`BOARDS.ss` / `BOARDS.rk`) in `stats.html`.
- Points: win 2, draw 1 (only matches actually played), goal 3, assist 2, POTM 1, red −5, yellow −2, foul −1; losses, own goals, saves = 0. See `POINT_RULES` / `calcPoints`.
- Order (`RK_CHAIN`): 0-match players last, then Points, then the Season Stats chain. Ties share a rank shown with "=".
- Row "Details" button shows the breakdown. A blocking pop-up ("Don't take it seriously yet" / "I accept") shows once per page load when the tab is opened.
- Tests: `tests/site/ranking_tests.py`.
- Ranking (In QA) week-by-week: "week" = `match_day` of completed matches. `buildHistory()` in `stats.html` recomputes cumulative stats/points/rank after each match day from matches + appearances + `match_events` (paginated with `.range`). Details shows the points calculation plus a "Week by week" table (week points, running total, rank, ▲/▼ movement). The main table shows a green ▲n / red ▼n before the rank for the latest week vs the week before; no sign if unchanged. Ranks are always among every player of the season — team/rested/search filters only hide rows. "All seasons" shows no weekly history or arrows. Tests: `tests/site/ranking_weeks_tests.py`. The fake Supabase now supports `.range()`.
- Rank movement arrows use the change in **players strictly ahead** (1 + count with a better rank), not the change in the dense rank number, because a big tied group splitting (e.g. 9= x14 in Week 1) inflates rank numbers without anyone actually passing anyone.
- Ranking (In QA) phone headers: iPhone Safari rendered rotated (writing-mode + transform) headers upside-down and overlapping. Replaced with short horizontal labels on small screens (Pts P W D L G A PM YC RC F OG Rs Ab, each header has a `.lg` full and `.sh` short span) plus a legend line. Do not use writing-mode/transform on table header cells.

## Week 3 (Match Day 3 = Matches 9-12)
- `sql/day3_results.sql` (same pattern as day2: scores, toss, lineups, events; re-runnable; validates every name). Needs `migration_day2_fields.sql` + `migration_fouls.sql` already run. No code changes needed; Stats, Ranking (In QA), standings and match pages read the data.
- Results: M9 Muggles 1-0 Desi, M10 Renegades 1-0 Scouts, M11 Scouts 2-0 Desi (Pradnyal's goal a penalty), M12 Muggles 2-0 Renegades (sheet said "Desi Steelers 0-0 Renegades"; owner confirmed 2-0 Muggles).

## Captains
- Data lives on `match_appearances.is_captain` (existing column) + new `captain_stand_in` (run `sql/migration_captains.sql`; one captain per team per match via a partial unique index). `sql/captains.sql` records Day 1-3 (Varun to Chirag on Renegades from Day 3 = first captain change of the league; Bhagyesh stood in for Pradnyal in Match 5; Vija for Nasiq in Match 9; Chirag stayed Renegades captain in Match 12 although rested). Re-run `captains.sql` after re-running any `dayN_results.sql` (they rebuild lineups and clear the flags).
- `captainTimeline()` in `common.js` derives changes/stand-ins/current captain; used by Stats > Milestones > Captains, team page "Captains" card, player page "Captaincy" card. Match page shows (C) badges + "Captain:" line. Admin > Records > Match Lineup has a Captain select per team and a stand-in tick box (saving needs the migration).
- Tests: `tests/site/captain_tests.py`.

## Injuries + sort by ranking
- `match_appearances.absent_reason` ('injury' or null; `sql/migration_injuries.sql`). `sql/injuries.sql` marks Vamshi absent (injury) in every completed match of his team except the one he was rested (re-run after any dayN_results.sql / captains.sql order: day results, captains, injuries).
- Stats > Milestones > Injury tab: own season filter (each season + All seasons, current preselected); counts only completed matches; lists matches missed per player and every match. Match page tags absent injured players "(injury)". Admin lineup form has an "injury" tick next to each player (only used when Absent).
- Season Stats and Ranking (In QA): the "#" header is sortable: click = ranking order (best first), click again = worst first (rank numbers unchanged).
- Tests: `injury_tests.py`, `rank_sort_tests.py`.
- Captains tab "Matches captained" table: As captain / As stand-in / Total / Won / Drawn / Lost / Win % / Goals for / POTM. Record counts every match captained (stand-in included; a rested captain's team result still counts); POTM only in matches he captained; Win % = wins / completed matches. Sortable headers + "Reset sort" button (default: most matches, then name).

## Availability tab (replaces the Rested and Absent tabs)
- Stats > Milestones > Availability: "Not rested yet" first (a card per team, played counts; absent-only players still count as not rested), then "Rested and absent": a grid per team, columns = that team's completed matches (header links to the match), R = rested, A = absent, A+ = absent (injury). The old Rested/Absent tabs and their code were removed. Tests updated (`attendance_tests.py`, `injury_tests.py`, `season_stats_tests.py`).

## Injury counting (rested + absent)
- A match counts as an injury miss when `absent_reason = 'injury'` and status is `rested` OR `absent`.
- `sql/injuries.sql` flags all of Vamshi's completed matches (rested one stays `rested`, others `absent`) -> Missed 6 = Rested 1 + Absent 5.
- Injury tab: Player/Team/Missed/Rested/Absent; match list has a Status column. Availability grid shows `R✚` / `A✚`.
- Admin lineup: the injury checkbox saves for Rested or Absent rows.
- Re-run order after any results script: dayN_results -> captains.sql -> injuries.sql.
