# Random league generator for the stats audit. Produces a python dict of tables (uuid strings) + SQL to load into Postgres.
import random, uuid
def U(rng): return str(uuid.UUID(int=rng.getrandbits(128), version=4))
def gen(seed):
    rng = random.Random(seed)
    sid = U(rng)
    season = {'id': sid, 'name': 'Audit', 'points_win': 2, 'points_draw': 1, 'points_loss': 0, 'is_current': True}
    teams = [{'id': U(rng), 'name': 'T%d' % i} for i in range(6)]
    players, roster = [], []
    for ti, t in enumerate(teams):
        for k in range(5):
            p = {'id': U(rng), 'full_name': 'P%d_%d' % (ti, k)}
            players.append(p); roster.append({'id': U(rng), 'season_id': sid, 'team_id': t['id'], 'player_id': p['id']})
    home = {r['player_id']: r['team_id'] for r in roster}
    bytm = {t['id']: [r['player_id'] for r in roster if r['team_id'] == t['id']] for t in teams}
    matches, apps, events = [], [], []
    for day in range(1, 6):
        order = teams[:]; rng.shuffle(order)
        pairs = [(order[0], order[1]), (order[2], order[3]), (order[4], order[5])]
        day_matches = []
        for n, (h, a) in enumerate(pairs, 1):
            r = rng.random()
            status = 'completed' if (day <= 3 or r < .35) else 'scheduled'
            m = {'id': U(rng), 'season_id': sid, 'match_day': day, 'match_number': n, 'home_team_id': h['id'], 'away_team_id': a['id'],
                 'status': status, 'home_score': None, 'away_score': None, 'kickoff_at': '2026-10-%02dT1%d:00:00+00:00' % (day, n), 'live_phase': None}
            matches.append(m); day_matches.append(m)
        # loans: a player plays this day for another team's match
        loaned = {}  # (player) -> (match, team)
        for _ in range(rng.choice([0, 0, 1, 2])):
            cands = [m for m in day_matches if m['status'] == 'completed']
            if not cands: break
            m = rng.choice(cands); host = rng.choice([m['home_team_id'], m['away_team_id']])
            other = [t['id'] for t in teams if t['id'] not in (m['home_team_id'], m['away_team_id'])]
            if not other: continue
            ot = rng.choice(other); pl = rng.choice(bytm[ot])
            if pl in loaned: continue
            # the loanee's own team must have a match today (they all do)
            loaned[pl] = (m, host)
        for m in day_matches:
            pending = m['status'] == 'completed' and rng.random() < .15
            lineups = {}
            if m['status'] == 'completed' and not pending:
                for tid in (m['home_team_id'], m['away_team_id']):
                    for pl in bytm[tid]:
                        if pl in loaned: continue   # away on loan today
                        st = rng.choices(['played', 'rested', 'absent'], [70, 15, 15])[0]
                        apps.append({'id': U(rng), 'match_id': m['id'], 'player_id': pl, 'team_id': tid, 'status': st,
                                     'started': st == 'played', 'is_captain': False, 'captain_stand_in': False, 'absent_reason': 'injury' if st != 'played' and rng.random() < .3 else None})
                        lineups.setdefault(tid, []).append((pl, st))
                for pl, (lm, host) in loaned.items():
                    if lm['id'] == m['id']:
                        apps.append({'id': U(rng), 'match_id': m['id'], 'player_id': pl, 'team_id': host, 'status': 'played', 'started': True, 'is_captain': False, 'captain_stand_in': False, 'absent_reason': None})
                        lineups.setdefault(host, []).append((pl, 'played'))
            # events
            live = m['status'] == 'scheduled' and rng.random() < .3
            if live: m['live_phase'] = 'h1'
            sc = {m['home_team_id']: 0, m['away_team_id']: 0}
            if (m['status'] == 'completed' and not pending) or live:
                for tid in (m['home_team_id'], m['away_team_id']):
                    ps = [pl for pl, st in lineups.get(tid, []) if st == 'played'] or ([] if live else [])
                    if live and not ps: ps = bytm[tid]
                    if not ps: continue
                    opp = m['away_team_id'] if tid == m['home_team_id'] else m['home_team_id']
                    for _ in range(rng.choice([0, 0, 1, 1, 2, 3, 4])):
                        sc_pl = rng.choice(ps); half = rng.choice([1, 2]); rem = rng.randint(0, 600)
                        pen = rng.random() < .1
                        events.append({'id': U(rng), 'match_id': m['id'], 'team_id': tid, 'player_id': sc_pl, 'event_type': 'goal', 'half': half, 'time_remaining': rem, 'is_penalty': pen, 'related_player_id': None})
                        sc[tid] += 1
                        mates = [x for x in ps if x != sc_pl]
                        if mates and not pen and rng.random() < .6:
                            events.append({'id': U(rng), 'match_id': m['id'], 'team_id': tid, 'player_id': rng.choice(mates), 'event_type': 'assist', 'half': half, 'time_remaining': rem, 'is_penalty': False, 'related_player_id': sc_pl})
                    if rng.random() < .15:
                        events.append({'id': U(rng), 'match_id': m['id'], 'team_id': tid, 'player_id': rng.choice(ps), 'event_type': 'own_goal', 'half': 1, 'time_remaining': 100, 'is_penalty': False, 'related_player_id': None}); sc[opp] += 1
                    for typ, pr in (('yellow_card', .3), ('red_card', .08), ('foul', .4), ('save', .3), ('player_of_match', .35)):
                        if rng.random() < pr:
                            events.append({'id': U(rng), 'match_id': m['id'], 'team_id': tid, 'player_id': rng.choice(ps), 'event_type': typ, 'half': 1, 'time_remaining': 200, 'is_penalty': False, 'related_player_id': None})
            if m['status'] == 'completed':
                if pending:
                    m['home_score'], m['away_score'] = rng.randint(0, 4), rng.randint(0, 4)
                else:
                    m['home_score'], m['away_score'] = sc[m['home_team_id']], sc[m['away_team_id']]
    # player-of-match: at most one per match is irrelevant to the audit; keep as generated
    return {'season': season, 'teams': teams, 'players': players, 'roster': roster, 'matches': matches, 'apps': apps, 'events': events}

def q(v):
    if v is None: return 'null'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, (int, float)): return str(v)
    return "'" + str(v).replace("'", "''") + "'"
def ins(table, rows, cols):
    if not rows: return ''
    return 'insert into %s (%s) values\n%s;\n' % (table, ','.join(cols), ',\n'.join('(' + ','.join(q(r.get(c)) for c in cols) + ')' for r in rows))
def load_sql(d):
    s = 'truncate match_events, match_appearances, matches, team_season_rosters, players, teams, seasons cascade;\n'
    s += ins('seasons', [d['season']], ['id', 'name', 'points_win', 'points_draw', 'points_loss', 'is_current'])
    s += ins('teams', d['teams'], ['id', 'name'])
    s += ins('players', d['players'], ['id', 'full_name'])
    s += ins('team_season_rosters', d['roster'], ['id', 'season_id', 'team_id', 'player_id'])
    s += ins('matches', d['matches'], ['id', 'season_id', 'match_day', 'match_number', 'home_team_id', 'away_team_id', 'status', 'home_score', 'away_score', 'kickoff_at', 'live_phase'])
    s += ins('match_appearances', d['apps'], ['id', 'match_id', 'player_id', 'team_id', 'status', 'started', 'is_captain', 'captain_stand_in', 'absent_reason'])
    s += ins('match_events', d['events'], ['id', 'match_id', 'team_id', 'player_id', 'event_type', 'half', 'time_remaining', 'is_penalty', 'related_player_id'])
    return s
