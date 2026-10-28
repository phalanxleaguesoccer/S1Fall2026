# Layer 2: what the SITE shows (Ranking page, Records engine, Standings page) vs the independent oracle.
# The two database views are the real Postgres views, so this checks SQL + JS together.  usage: site_audit.py [n_seeds]
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'site'))
from gen import gen, load_sql; from oracle import oracle, standings
from harness import *
PSQL = ['psql', '-h', '/tmp/pgs', '-p', '5544', '-U', 'postgres', '-d', 'audit', '-At', '-q', '-v', 'ON_ERROR_STOP=1']
def run(sql, inp=None):
    r = subprocess.run(PSQL + ([] if inp else ['-c', sql]), input=inp, capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    return r.stdout
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
serve(); bad = 0
def fail(*a):
    global bad; bad += 1; print('MISMATCH', *a)
def points(r): return 2*r['won'] + r['drawn'] + 3*r['goals'] + 2*r['assists'] + r['potm_awards'] - 5*r['red_cards'] - 2*r['yellow_cards'] - r['fouls']
with sync_playwright() as pw:
    for seed in range(N):
        d = gen(seed); run(None, load_sql(d))
        views = {v: json.loads(run("select coalesce(json_agg(t),'[]') from (select * from %s) t" % v)) for v in ('player_season_stats', 'league_standings')}
        T = {t['id']: t['name'] for t in d['teams']}; Pn = {p['id']: p['full_name'] for p in d['players']}
        db = {'seasons': [dict(d['season'], created_at='2026-01-01')], 'teams': [dict(t, is_active=True, crest_url=None) for t in d['teams']],
              'players': [dict(p, age=30, preferred_position='Mid', position_category='Center', is_active=True, photo_url=None, created_at='2026-01-01') for p in d['players']],
              'team_season_rosters': d['roster'], 'matches': [dict(m, forfeited_by_team_id=None, notes=None) for m in d['matches']],
              'match_events': [dict(e, minute=None, created_at='2026-10-01T00:00:00+00:00') for e in d['events']], 'match_appearances': d['apps'],
              'page_views': [], 'season_awards': [], 'suspensions': [], 'player_notes_log': [], 'player_rating_log': [], 'admins': [{'user_id': 'a'}], 'auction_unsold': [], 'auction_state': [], 'tiebreak_shootout_order': [],
              '__views': views}
        s = Site(pw, db)
        # ---- Ranking page
        p = s.page('stats.html#ranking', 1500)
        if p.errs: fail(seed, 'js errors', p.errs)
        rows = p.evaluate("""()=>[...document.querySelectorAll('#rk-body tbody tr:not(.det)')].map(tr=>{const td=[...tr.children].map(x=>x.innerText.trim());const c=tr.children[0];td[0]=c.lastChild?c.lastChild.textContent.trim():'';return td})""")
        exp = oracle(d); agg = {}
        for (pid, team), r in exp.items():
            a = agg.setdefault(pid, {k: 0 for k in r})
            for k, v in r.items(): a[k] += v
        got = {}
        for r in rows:
            if len(r) < 17: continue
            got[r[1]] = r
        if len(got) != len(agg): fail(seed, 'ranking row count', len(got), 'expected', len(agg))
        cols = ['points', 'games_played', 'won', 'drawn', 'lost', 'goals', 'assists', 'potm_awards', 'yellow_cards', 'red_cards', 'fouls', 'own_goals', 'rested', 'absent']
        ordered = []
        for pid, a in agg.items():
            a['points'] = points(a); r = got.get(Pn[pid])
            if not r: fail(seed, 'missing from ranking', Pn[pid]); continue
            for i, c in enumerate(cols):
                if int(r[3 + i]) != a[c]: fail(seed, Pn[pid], c, 'site', r[3 + i], 'expected', a[c])
            key = (0 if a['games_played'] else 1, -a['points'], 1 if a['yellow_cards'] + a['red_cards'] else 0, -a['goals'], -a['assists'], -a['potm_awards'], -a['won'], -a['drawn'], a['lost'], -a['games_played'], a['yellow_cards'], a['red_cards'], -a['rested'], a['absent'])
            ordered.append((key, Pn[pid]))
        ordered.sort(); rk = {}; n = 0; prev = None
        for key, name in ordered:
            if key != prev: n += 1; prev = key
            rk[name] = n
        for name, r in got.items():
            if name in rk:
                site_rank = int(r[0].replace('=', '') or 0)
                if site_rank != rk[name]: fail(seed, name, 'rank site', r[0], 'expected', rk[name])
        pos = [r[1] for r in rows if len(r) >= 17]
        if pos != [n for _, n in ordered if n in got]: fail(seed, 'ranking ORDER differs')
        # ---- Records engine on the same data
        rec = p.evaluate("""()=>{const o=recBuild(%s,%s,%s,%s);return o.players.map(x=>({id:x.id,played:x.played,won:x.won,drawn:x.drawn,lost:x.lost,rested:x.rested,absent:x.absent,goals:x.goals,assists:x.assists,potm:x.potm,yellow:x.yellow,red:x.red,fouls:x.fouls,og:x.og}))}""" % tuple(json.dumps(db[k]) for k in ('matches', 'team_season_rosters', 'match_appearances', 'match_events')))
        # records.js sees every event in a season's matches, incl. matches not yet completed; flag any difference to the oracle
        for x in rec:
            a = agg.get(x['id'])
            if not a: continue
            for k, c in (('played', 'games_played'), ('won', 'won'), ('drawn', 'drawn'), ('lost', 'lost'), ('rested', 'rested'), ('absent', 'absent'), ('goals', 'goals'), ('assists', 'assists'), ('potm', 'potm_awards'), ('yellow', 'yellow_cards'), ('red', 'red_cards'), ('fouls', 'fouls'), ('og', 'own_goals')):
                if x[k] != a[c]: fail(seed, 'RECORDS', Pn[x['id']], k, 'records', x[k], 'expected', a[c])
        # ---- Standings page
        q = s.page('index.html', 1500)
        st = q.evaluate("""()=>[...document.querySelectorAll('#standings-body tr')].map(tr=>[...tr.children].map(x=>x.innerText.trim()))""")
        es = standings(d); byname = {T[t]: e for t, e in es.items()}
        for r in st:
            if len(r) < 10: continue
            nm = r[1].split('\n')[0].strip(); e = byname.get(nm)
            if not e: continue
            site = dict(points=r[2], played=r[3], wins=r[4], draws=r[5], losses=r[6], goal_difference=r[7], goals_for=r[8], goals_against=r[9])
            for k, v in site.items():
                if int(v.replace('+', '').replace('−', '-')) != e[k]: fail(seed, 'STANDINGS', nm, k, 'site', v, 'expected', e[k])
        s.br.close()
print('SITE audit: %d seeds, %d mismatches' % (N, bad)); sys.exit(1 if bad else 0)
