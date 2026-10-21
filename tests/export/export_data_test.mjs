// Tests for scripts/export-data.mjs against a mock PostgREST server.
// Run: node --test tests/export/
import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { mkdtemp, readFile, readdir, writeFile, mkdir, access } from "node:fs/promises";
import { exportData, DATASETS } from "../../scripts/export-data.mjs";

const KEY = "test-anon-key";
const PRIVATE_PLAYER_FIELDS = ["bio_notes", "fitness_notes", "leave_plan", "fun_fact", "age", "jersey_size"];

// Mock server: serves rows per table, honours ?select= and the Range header
// (like PostgREST), and records every request.
function startMock({ rowsByTable, failTable } = {}) {
  const seen = [];
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://x");
    const table = url.pathname.replace("/rest/v1/", "");
    seen.push({ table, select: url.searchParams.get("select"), apikey: req.headers.apikey,
                auth: req.headers.authorization, range: req.headers.range });
    if (req.headers.apikey !== KEY) { res.writeHead(401).end("bad key"); return; }
    if (table === failTable) { res.writeHead(500).end("boom"); return; }
    let rows = rowsByTable[table] ?? [];
    const sel = url.searchParams.get("select");
    if (sel && sel !== "*") {
      const cols = sel.split(",");
      rows = rows.map((r) => Object.fromEntries(cols.map((c) => [c, r[c] ?? null])));
    }
    const [from, to] = (req.headers.range ?? "0-999").split("-").map(Number);
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(rows.slice(from, to + 1)));
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => {
    const { port } = server.address();
    resolve({ seen, url: `http://127.0.0.1:${port}`, close: () => new Promise((r) => server.close(r)) });
  }));
}

function sampleRows() {
  const players = Array.from({ length: 3 }, (_, i) => ({
    id: `p${i}`, full_name: `Player ${i}`, preferred_position: "Defense", skill_rating: 5,
    bio_notes: "private", fitness_notes: "private", leave_plan: "private", fun_fact: "x", age: 30, jersey_size: "M",
  }));
  const events = Array.from({ length: 2300 }, (_, i) => ({ id: `e${i}`, match_id: "m1", event_type: "goal" }));
  return {
    seasons: [{ id: "s1", name: "S1", is_current: true }],
    teams: [{ id: "t1", name: "Scouts FC" }],
    players,
    team_season_rosters: [{ season_id: "s1", team_id: "t1", player_id: "p0" }],
    matches: [{ id: "m1", match_day: 4, match_number: 1, status: "scheduled", notes: "private note" }],
    match_events: events,
    match_appearances: [{ match_id: "m1", player_id: "p0", status: "rested" }],
    league_standings: [{ team_id: "t1", pts: 5 }],
    player_season_stats: [{ player_id: "p0", goals: 1 }],
  };
}

const exists = (p) => access(p).then(() => true, () => false);

test("writes every dataset plus an index with row counts", async () => {
  const mock = await startMock({ rowsByTable: sampleRows() });
  const out = path.join(await mkdtemp(path.join(os.tmpdir(), "exp-")), "data");
  try {
    const idx = await exportData(out, { url: mock.url, key: KEY });
    const files = (await readdir(out)).sort();
    assert.deepEqual(files, [...DATASETS.map((d) => `${d.name}.json`), "index.json"].sort());
    assert.equal(idx.counts.players, 3);
    assert.equal(idx.counts.matches, 1);
    const onDisk = JSON.parse(await readFile(path.join(out, "index.json"), "utf8"));
    assert.ok(!Number.isNaN(Date.parse(onDisk.generated_at)));
    assert.ok(mock.seen.every((r) => r.apikey === KEY && r.auth === `Bearer ${KEY}`));
  } finally { await mock.close(); }
});

test("paginates past 1000 rows without losing any", async () => {
  const mock = await startMock({ rowsByTable: sampleRows() });
  const out = path.join(await mkdtemp(path.join(os.tmpdir(), "exp-")), "data");
  try {
    const idx = await exportData(out, { url: mock.url, key: KEY });
    assert.equal(idx.counts.match_events, 2300);
    const events = JSON.parse(await readFile(path.join(out, "match_events.json"), "utf8"));
    assert.equal(new Set(events.map((e) => e.id)).size, 2300);
    assert.equal(mock.seen.filter((r) => r.table === "match_events").length, 3);
  } finally { await mock.close(); }
});

test("private player and match fields are neither requested nor written", async () => {
  const mock = await startMock({ rowsByTable: sampleRows() });
  const out = path.join(await mkdtemp(path.join(os.tmpdir(), "exp-")), "data");
  try {
    await exportData(out, { url: mock.url, key: KEY });
    const asked = mock.seen.find((r) => r.table === "players").select;
    for (const f of PRIVATE_PLAYER_FIELDS) assert.ok(!asked.split(",").includes(f), `requested ${f}`);
    const players = JSON.parse(await readFile(path.join(out, "players.json"), "utf8"));
    for (const p of players) for (const f of PRIVATE_PLAYER_FIELDS) assert.ok(!(f in p), `leaked ${f}`);
    const matches = JSON.parse(await readFile(path.join(out, "matches.json"), "utf8"));
    assert.ok(!("notes" in matches[0]));
    assert.equal(matches[0].match_day, 4);
  } finally { await mock.close(); }
});

test("a failing table throws and leaves no output or temp folders", async () => {
  const mock = await startMock({ rowsByTable: sampleRows(), failTable: "match_appearances" });
  const parent = await mkdtemp(path.join(os.tmpdir(), "exp-"));
  const out = path.join(parent, "data");
  try {
    await assert.rejects(exportData(out, { url: mock.url, key: KEY }), /match_appearances: HTTP 500/);
    assert.equal(await exists(out), false);
    assert.deepEqual(await readdir(parent), []);
  } finally { await mock.close(); }
});

test("a failed run keeps the previous good data folder untouched", async () => {
  const mock = await startMock({ rowsByTable: sampleRows(), failTable: "teams" });
  const parent = await mkdtemp(path.join(os.tmpdir(), "exp-"));
  const out = path.join(parent, "data");
  await mkdir(out);
  await writeFile(path.join(out, "keep.json"), "[1]");
  try {
    await assert.rejects(exportData(out, { url: mock.url, key: KEY }));
    assert.equal(await readFile(path.join(out, "keep.json"), "utf8"), "[1]");
  } finally { await mock.close(); }
});

test("a wrong key surfaces as an error, not empty files", async () => {
  const mock = await startMock({ rowsByTable: sampleRows() });
  const out = path.join(await mkdtemp(path.join(os.tmpdir(), "exp-")), "data");
  try {
    await assert.rejects(exportData(out, { url: mock.url, key: "wrong" }), /HTTP 401/);
    assert.equal(await exists(out), false);
  } finally { await mock.close(); }
});
