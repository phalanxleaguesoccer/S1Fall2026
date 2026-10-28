# Layer 1: real Postgres views vs independent oracle on random leagues.  usage: pg_audit.py [n_seeds]
import sys, json, subprocess, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import gen, load_sql; from oracle import oracle, standings
PSQL = ['psql', '-h', '/tmp/pgs', '-p', '5544', '-U', 'postgres', '-d', 'audit', '-At', '-q', '-v', 'ON_ERROR_STOP=1']
def run(sql): 
    r = subprocess.run(PSQL + ['-c', sql], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    return r.stdout
def run_file(sql):
    r = subprocess.run(PSQL, input=sql, capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
bad = 0; N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
cols = ['games_played', 'rested', 'absent', 'goals', 'assists', 'yellow_cards', 'red_cards', 'potm_awards', 'saves', 'own_goals', 'fouls']
for seed in range(N):
    d = gen(seed); run_file(load_sql(d)); exp = oracle(d)
    got = json.loads(run("select coalesce(json_agg(t),'[]') from (select * from player_season_stats) t") or '[]')
    gm = {(r['player_id'], r['team_id']): r for r in got}
    # view returns a row for every stint that exists (roster rows + loans)
    for k, e in exp.items():
        g = gm.get(k)
        if not g: print('seed', seed, 'MISSING row', k); bad += 1; continue
        for c in cols:
            if int(g[c]) != e[c]:
                print('seed', seed, 'player', next(p['full_name'] for p in d['players'] if p['id'] == k[0]), 'team', next(t['name'] for t in d['teams'] if t['id'] == k[1]), c, 'view', g[c], 'expected', e[c]); bad += 1
    if len(gm) != len(exp): print('seed', seed, 'row count view', len(gm), 'expected', len(exp)); bad += 1
    st = json.loads(run("select coalesce(json_agg(t),'[]') from (select * from league_standings) t"))
    es = standings(d); sm = {r['team_id']: r for r in st}
    for t, e in es.items():
        for c in e:
            if int(sm.get(t, {}).get(c, -1)) != e[c]: print('seed', seed, 'standings', t, c, sm.get(t, {}).get(c), e[c]); bad += 1
    if len(sm) != len(es): print('seed', seed, 'standings rows', len(sm), len(es)); bad += 1
print('PG audit: %d seeds, %d mismatches' % (N, bad)); sys.exit(1 if bad else 0)
