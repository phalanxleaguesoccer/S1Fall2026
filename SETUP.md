# Phalanx League Soccer — Setup Guide

This site is a static frontend (plain HTML/CSS/JS) backed by a free Supabase
database, deployed on free Netlify hosting. You'll need to create two free
accounts (I can't do this step for you — it needs your email/verification).

## 1. Create your Supabase project (free tier)

1. Go to https://supabase.com → sign up (free).
2. Create a new project. Pick any name (e.g. "phalanx-league"), a strong
   database password (save it somewhere), and any region.
3. Once it's ready, go to **Project Settings → API**. Copy:
   - **Project URL**
   - **anon public** key
4. Open `public/js/config.js` in this project and paste them in:
   ```js
   window.PHALANX_CONFIG = {
     SUPABASE_URL: "https://xxxxxxxx.supabase.co",
     SUPABASE_ANON_KEY: "eyJ..."
   };
   ```
5. Go to **SQL Editor** in Supabase, paste the entire contents of
   `sql/schema.sql` from this project, and run it. This creates all tables,
   views, and security policies, plus one starter season ("Season 1").

## 2. Create the two admin logins

1. In Supabase, go to **Authentication → Users → Add user** (create user
   manually), once for you and once for me (or whoever the second admin is).
   Use real email addresses and set passwords.
2. For each user, copy their **User UID** (shown in the users list).
3. Back in **SQL Editor**, run (once per admin):
   ```sql
   insert into admins (user_id, display_name) values ('paste-user-uid-here', 'Your Name');
   ```
4. That's it — those two accounts can now log in at `/admin/login.html` and
   edit everything. Nobody else can, even if they find the login page.

## 3. Deploy to Netlify (free tier)

1. Go to https://netlify.com → sign up (free).
2. Easiest path: **"Add new site" → "Deploy manually"**, then drag-and-drop
   the `public/` folder from this project into the upload area. Netlify
   gives you a live URL immediately (e.g. `phalanx-league.netlify.app`).
3. Optional: for auto-deploys on future changes, connect Netlify to a GitHub
   repo containing this project instead of manual drag-and-drop — ask me and
   I'll set that up too.

## 4. Add your real league data

Once deployed, log in at `yoursite.netlify.app/admin/login.html` and use the
dashboard to add:
- The 4 teams
- All players
- Season roster assignments (who's on which team, jersey numbers, auction price)
- The 24 scheduled matches (day/number/home/away — from your locked fixture list)
- Match results and events as games are played

## Notes / current limits (MVP)

- Only a single "headshot" photo per player — paste any public image URL
  (e.g. from Google Drive with public sharing, or Imgur). A proper upload
  button can be added later.
- Bulk import from your Player Auction Roster spreadsheet isn't built yet —
  you agreed this can come later. For now, players are added one at a time
  in the admin dashboard.
- No activity/audit log yet (also deferred per your answer).
- Head-to-head tie-break (4th tie-breaker) isn't automatically resolved by
  the standings table when 3+ metrics are tied — that edge case needs a
  manual look since it depends on which specific teams are tied.
