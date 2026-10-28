# Independent calculation of what the numbers SHOULD be, written from the rules (not from the SQL / JS).
def oracle(d):
    M = {m['id']: m for m in d['matches']}
    home = {r['player_id']: r['team_id'] for r in d['roster']}
    appby = {}
    for a in d['apps']: appby[(a['match_id'], a['player_id'])] = a
    # a "transfer" = appearance for a team other than the roster team
    loans = {}
    for a in d['apps']:
        if a['team_id'] != home.get(a['player_id']): loans.setdefault(a['player_id'], set()).add(a['team_id'])
    day_other = {}   # (player, match_day) -> team played for that day when not home
    for a in d['apps']:
        if a['team_id'] != home.get(a['player_id']): day_other[(a['player_id'], M[a['match_id']]['match_day'])] = True
    out = {}
    for pl in d['players']:
        pid = pl['id']
        stints = [(home[pid], False)] + [(t, True) for t in sorted(loans.get(pid, []))]
        for team, loan in stints:
            row = dict(games_played=0, rested=0, absent=0, goals=0, assists=0, yellow_cards=0, red_cards=0, potm_awards=0, saves=0, own_goals=0, fouls=0, won=0, drawn=0, lost=0)
            for m in d['matches']:
                if team not in (m['home_team_id'], m['away_team_id']): continue
                if loan:
                    if (m['id'], pid) not in appby or appby[(m['id'], pid)]['team_id'] != team: continue
                elif day_other.get((pid, m['match_day'])): continue
                if m['status'] != 'completed': continue
                a = appby.get((m['id'], pid))
                if a:
                    st = a['status']
                    if st == 'played':
                        row['games_played'] += 1
                        if m['home_score'] is not None:
                            mine, th = (m['home_score'], m['away_score']) if m['home_team_id'] == team else (m['away_score'], m['home_score'])
                            row['won' if mine > th else 'lost' if mine < th else 'drawn'] += 1
                    elif st == 'rested': row['rested'] += 1
                    elif st == 'absent': row['absent'] += 1
                for e in d['events']:
                    if e['match_id'] == m['id'] and e['player_id'] == pid:
                        k = {'goal': 'goals', 'assist': 'assists', 'yellow_card': 'yellow_cards', 'red_card': 'red_cards', 'player_of_match': 'potm_awards', 'save': 'saves', 'own_goal': 'own_goals', 'foul': 'fouls'}.get(e['event_type'])
                        if k: row[k] += 1
            out[(pid, team)] = row
    return out
def standings(d):
    S = {}
    for m in d['matches']:
        if m['status'] != 'completed' or m['home_score'] is None: continue
        for t, f, a in ((m['home_team_id'], m['home_score'], m['away_score']), (m['away_team_id'], m['away_score'], m['home_score'])):
            r = S.setdefault(t, dict(played=0, wins=0, draws=0, losses=0, goals_for=0, goals_against=0))
            r['played'] += 1; r['goals_for'] += f; r['goals_against'] += a
            r['wins' if f > a else 'losses' if f < a else 'draws'] += 1
    for r in S.values():
        r['goal_difference'] = r['goals_for'] - r['goals_against']; r['points'] = 2 * r['wins'] + r['draws']
    return S
