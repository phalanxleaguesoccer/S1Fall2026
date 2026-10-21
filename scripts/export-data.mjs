#!/usr/bin/env node
// Exports the league's public data as static JSON so tools that cannot run the
// site's JavaScript (link previews, scripts, AI assistants) can read it.
//
// Runs in the GitHub Pages build (see .github/workflows/deploy-pages.yml), where
// the network is open. It reads only what the public anon key can already read
// (row level security: public read), using the URL/key already published in
// public/js/config.js. Nothing here needs a secret.
//
// Usage: node scripts/export-data.mjs [outDir]      (default outDir: _site/data)
// Env:   SUPABASE_URL / SUPABASE_ANON_KEY override config.js (used by tests).
//
// Output is written to a temp folder and moved into place only when every
// table was fetched, so a failed run never leaves half-written data behind.

import { readFile, writeFile, mkdir, rm, rename } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const PAGE_SIZE = 1000; // Supabase's default max rows per request

// Explicit column lists: new columns added to a table later are NOT published
// until they are listed here. Free-text personal notes are left out on purpose
// (players.bio_notes, fitness_notes, leave_plan, fun_fact, age, jersey_size).
export const DATASETS = [
  { name: "seasons", table: "seasons",
    columns: ["id", "name", "is_current", "points_win", "points_draw", "points_loss"] },
  { name: "teams", table: "teams",
    columns: ["id", "name", "crest_url", "color_primary"] },
  { name: "players", table: "players",
    columns: ["id", "full_name", "preferred_position", "position_category", "preferred_foot",
              "skill_rating", "skill_level", "stamina_level", "is_active", "photo_url"] },
  { name: "rosters", table: "team_season_rosters",
    columns: ["season_id", "team_id", "player_id", "is_owner", "jersey_number", "auction_price"] },
  { name: "matches", table: "matches",
    columns: ["id", "season_id", "match_day", "match_number", "home_team_id", "away_team_id",
              "kickoff_at", "status", "home_score", "away_score", "forfeited_by_team_id",
              "toss_winner_team_id", "toss_choice"] },
  { name: "match_events", table: "match_events",
    columns: ["id", "match_id", "team_id", "player_id", "event_type", "minute", "second",
              "half", "related_player_id", "is_penalty"] },
  { name: "appearances", table: "match_appearances",
    columns: ["match_id", "player_id", "team_id", "status", "absent_reason", "is_captain", "started"] },
  { name: "standings", table: "league_standings", columns: null },        // view, all columns
  { name: "player_season_stats", table: "player_season_stats", columns: null }, // view, all columns
];

// Stable ordering so the JSON only changes when the data does.
const ORDER = {
  seasons: "name", teams: "name", players: "full_name",
  team_season_rosters: "player_id", matches: "match_day,match_number,id",
  match_events: "match_id,id", match_appearances: "match_id,player_id",
  league_standings: null, player_season_stats: null,
};

async function readConfig() {
  if (process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY) {
    return { url: process.env.SUPABASE_URL, key: process.env.SUPABASE_ANON_KEY };
  }
  const src = await readFile(path.join(REPO_ROOT, "public/js/config.js"), "utf8");
  const url = /SUPABASE_URL\s*:\s*"([^"]+)"/.exec(src)?.[1];
  const key = /SUPABASE_ANON_KEY\s*:\s*"([^"]+)"/.exec(src)?.[1];
  if (!url || !key) throw new Error("Could not read SUPABASE_URL / SUPABASE_ANON_KEY from public/js/config.js");
  return { url, key };
}

async function fetchAll({ url, key }, { table, columns }) {
  const rows = [];
  const select = columns ? columns.join(",") : "*";
  const order = ORDER[table];
  for (let offset = 0; ; offset += PAGE_SIZE) {
    const qs = new URLSearchParams({ select });
    if (order) qs.set("order", order);
    const res = await fetch(`${url}/rest/v1/${table}?${qs}`, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Range: `${offset}-${offset + PAGE_SIZE - 1}`,
        "Range-Unit": "items",
      },
    });
    if (!res.ok) {
      const body = (await res.text()).slice(0, 200);
      throw new Error(`${table}: HTTP ${res.status} ${body}`);
    }
    const page = await res.json();
    if (!Array.isArray(page)) throw new Error(`${table}: unexpected response shape`);
    rows.push(...page);
    if (page.length < PAGE_SIZE) return rows;
  }
}

export async function exportData(outDir, config) {
  const cfg = config ?? (await readConfig());
  const tmp = `${outDir}.tmp-${process.pid}`;
  await rm(tmp, { recursive: true, force: true });
  await mkdir(tmp, { recursive: true });
  try {
    const counts = {};
    for (const ds of DATASETS) {
      const rows = await fetchAll(cfg, ds);
      counts[ds.name] = rows.length;
      await writeFile(path.join(tmp, `${ds.name}.json`), JSON.stringify(rows, null, 1) + "\n");
    }
    const index = {
      generated_at: new Date().toISOString(),
      note: "Public league data exported at site build time. Rows: see counts. Files: <name>.json",
      counts,
      files: DATASETS.map((d) => `${d.name}.json`),
    };
    await writeFile(path.join(tmp, "index.json"), JSON.stringify(index, null, 1) + "\n");
    await rm(outDir, { recursive: true, force: true });
    await mkdir(path.dirname(outDir), { recursive: true });
    await rename(tmp, outDir);
    return index;
  } catch (err) {
    await rm(tmp, { recursive: true, force: true });
    throw err;
  }
}

// Run only when executed directly (not when imported by the test).
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const outDir = path.resolve(process.argv[2] ?? path.join(REPO_ROOT, "_site/data"));
  exportData(outDir)
    .then((idx) => console.log(`Exported ${idx.files.length} files to ${outDir}`, idx.counts))
    .catch((err) => { console.error(`Data export failed: ${err.message}`); process.exit(1); });
}
