# Preprod

A separate test copy of the league: its own Supabase project and its own site at
`https://phalanxleaguesoccer.github.io/S1Fall2026/preprod/` (red PREPROD strip at the bottom of every page).

- **Database:** a second Supabase project. `preprod_setup.sql` builds it in one paste:
  every live migration and seed in the order they ran on live, plus a snapshot of the
  live rosters and auction prices (`rosters_snapshot.sql`, 4 owners + 33 sold, 780 points).
  It refuses to run on a database that already has league tables, and it is all-or-nothing.
  Regenerate after adding a live migration: `sh sql/preprod/build_preprod_setup.sh`
  (add the new file to the list in that script first).
- **Site:** the deploy workflow copies `public/` to `/preprod/` and swaps in
  `preprod/config.js` (preprod Supabase URL + public key + `ENV: "preprod"`).
  No `preprod/config.js` = no preprod copy; the live site is unaffected either way.
- New features are tested in preprod first: their SQL is run on preprod, then on live at go-live.
