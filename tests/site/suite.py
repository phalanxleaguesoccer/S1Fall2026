import re, json
from harness import *; from fixtures import *
serve()
R=[]
def ok(name,cond,detail=''):
    R.append((name,bool(cond)));print(('PASS ' if cond else 'FAIL ')+name+('' if cond else '  -> '+str(detail)))
PH=re.compile(r'\bTeam [A-D]\b')
with sync_playwright() as pw:
    # ---------- general: every public page ----------
    s=Site(pw,scenario_played())
    pages={'index.html':'Standings','teams.html':'Teams','players.html':'Players','matches.html':'Matches','team.html?id=t4':'Desi','player.html?id=p0':'Nasiq','match.html?id=m0':'Match'}
    for path in pages:
        p=s.page(path)
        ok(f'{path}: no JS errors',not p.errs,p.errs)
        ok(f'{path}: breadcrumbs present',p.locator('nav.breadcrumbs a').count()>=1 or path=='index.html', 'none')
        ok(f'{path}: header nav + footer',p.locator('header, .site-header, nav').count()>=1 and 'Phalanx League Soccer |' in p.inner_text('body'))
        ok(f'{path}: page view counter shown',re.search(r'viewed \d+ view',p.inner_text('body')) is not None)
        p.close()
    # ---------- standings ----------
    p=s.page('index.html');rows=p.locator('#standings-body tr')
    names=[rows.nth(i).locator('td').nth(1).inner_text() for i in range(rows.count())]
    ok('standings: only the 4 real teams',sorted(names)==sorted(['Desi Steelers FC','Muggles FC','Scouts FC','Renegades']),names)
    ok('standings: no Team A-D placeholders',not PH.search(p.locator('#standings-body').inner_text()))
    ok('standings: season is default (not All)',p.locator('#standings-season-filter').input_value()=='season1')
    ok('standings: rank column 1..4 unique',[rows.nth(i).locator('td').first.inner_text() for i in range(4)]==['1','2','3','4'])
    ok('standings: tie-break order text',re.search(r'goal difference.*goals scored.*goals conceded.*head-to-head.*penalty shoot-out',p.inner_text('body'),re.S) is not None)
    ok('standings: rules text 2/1/0','Win = 2 pts' in p.inner_text('body'))
    p.select_option('#standings-season-filter','all');p.wait_for_timeout(500)
    ok('standings: All Seasons filter works, no errors',not p.errs and p.locator('#standings-body tr').count()==4,p.errs)
    # ---------- teams ----------
    p=s.page('teams.html');cards=p.locator('#teams-grid .player-card')
    ok('teams: exactly 4 real teams',cards.count()==4,cards.count())
    ok('teams: no placeholders',not PH.search(p.inner_text('#teams-grid')))
    ok('teams: owner shown under name with player link',p.locator('#teams-grid a[href^="player.html?id="]').count()==4)
    ok('teams: team links to team page',p.locator('#teams-grid a[href^="team.html?id="]').count()==4)
    # ---------- players ----------
    p=s.page('players.html')
    opts=p.locator('#team-filter option').all_inner_texts()
    ok('players: team dropdown = All/Unassigned + 4 real only',sorted(opts)==sorted(['All teams','Unassigned','Desi Steelers FC','Muggles FC','Renegades','Scouts FC']),opts)
    so=p.locator('#season-filter option').all_inner_texts()
    ok('players: season dropdown has no "All"',not any(o.strip().lower().startswith('all') for o in so) and len(so)>=1,so)
    ok('players: count matches',p.locator('#players-grid .player-card').count()==9)
    p.select_option('#team-filter',label='Renegades');p.wait_for_timeout(400)
    ok('players: team filter -> Renegades has 2',p.locator('#players-grid .player-card').count()==2,p.locator('#players-grid .player-card').count())
    p.select_option('#team-filter',label='Unassigned');p.wait_for_timeout(400)
    ok('players: Unassigned filter has 0 (all rostered)',p.locator('#players-grid .player-card').count()==0,p.locator('#players-grid .player-card').count())
    p.select_option('#team-filter',label='All teams');p.fill('#search-box','bil');p.wait_for_timeout(400)
    ok('players: search works',p.locator('#players-grid .player-card').count()==1)
    # ---------- team page ----------
    p=s.page('team.html?id=t4')
    ok('team: name + owner link -> owner profile',p.inner_text('#team-name').lower().startswith('desi') and p.get_attribute('#owner-link','href')=='player.html?id=p0')
    totals=[t.strip() for t in p.locator('#squad-totals-body td').all_inner_texts()]
    ok('team: cumulative squad totals G/A/Saves/Y/R/POTM/POT = 3,1,1,0,0,1,1',totals==['3','1','1','0','0','1','1'],totals)
    cards=p.locator('#roster-grid .player-card').all_inner_texts()
    ok('team: squad grid lists owner FIRST (labelled Owner) then the players',p.locator('#roster-grid a[href^="player.html?id="]').count()==3 and 'Owner' in cards[0] and all('Owner' not in c for c in cards[1:]),cards)
    ok('team: season filter + squad season filter present',p.locator('#season-filter option').count()>=2 and p.locator('#squad-season-filter option').count()>=2)
    ok('team: top scorer & POTM at season and all-time level','Nasiq (2)' in p.inner_text('#top-scorer-season') and 'Nasiq (2)' in p.inner_text('#top-scorer-alltime') and 'Nasiq (1)' in p.inner_text('#top-potm-season') and 'Nasiq (1)' in p.inner_text('#top-potm-alltime'))
    p.select_option('#season-filter','all');p.wait_for_timeout(500)
    ok('team: All seasons switch no errors',not p.errs,p.errs)
    # ---------- player ----------
    p=s.page('player.html?id=p0');body=p.inner_text('body')
    for lab in ['GP','GOALS','ASSISTS','SAVES','YELLOW','RED','POTM','POT']:
        ok(f'player: stats column {lab}',lab in body)
    ok('player: stat values goals=2 potm=1 pot=1',re.search(r'\t0\t2\t0\t0\t0\t0\t1\t1',body) is not None,body[body.find('GP'):body.find('GP')+80])
    ok('player: team link',p.locator('#player-team a[href^="team.html"]').count()==1 or 'Desi Steelers FC' in body)
    # ---------- matches / match ----------
    p=s.page('matches.html')
    ok('matches: date and EDT time shown','9:00 PM EDT' in p.inner_text('body') and 'Oct 6, 2026' in p.inner_text('body'))
    ok('matches: rows link to match page',p.locator('a[href^="match.html?id="]').count()>=2 or p.locator('[data-href^="match.html"]').count()>=2)
    p=s.page('match.html?id=m0');b=p.inner_text('body')
    ok('match: score + events',('3 – 1' in b) and 'Player of the Match' in b and 'goal saved' in b.lower())
    # ---------- timezone independence ----------
    ctx=s.br.new_context(timezone_id='Asia/Kolkata');db=json.dumps(scenario_played()|{'__admin':False});ctx.add_init_script('window.__DB='+db+';')
    ctx.route('**/*supabase*.js',lambda r:r.fulfill(body=FAKE,content_type='application/javascript') if 'cdn.jsdelivr' in r.request.url else r.continue_())
    p=ctx.new_page();p.goto('http://127.0.0.1:8137/matches.html');p.wait_for_timeout(700)
    ok('timezone: viewer in India still sees 9:00 PM EDT on Oct 6','Oct 6, 2026, 9:00 PM EDT' in p.inner_text('body'),p.inner_text('body')[-200:])
    p=ctx.new_page();p.goto('http://127.0.0.1:8137/team.html?id=t0');p.wait_for_timeout(700)
    ok('timezone: team schedule date is Oct 6 for India viewer','Oct 6, 2026' in p.inner_text('#schedule-body'),p.inner_text('#schedule-body'))
    # ---------- page views increment ----------
    ctx=s.br.new_context();ctx.add_init_script('window.__DB='+json.dumps(scenario_played()|{'__admin':False})+';');ctx.route('**/*supabase*.js',lambda r:r.fulfill(body=FAKE,content_type='application/javascript') if 'cdn.jsdelivr' in r.request.url else r.continue_())
    p=ctx.new_page();p.goto('http://127.0.0.1:8137/teams.html');p.wait_for_timeout(600)
    ok('page views: counted per key (site + teams)','1 view' in p.inner_text('body'))
    # ---------- post-draw tie scenario ----------
    s2=Site(pw,scenario_post_tie());p=s2.page('index.html')
    b=p.inner_text('#standings-body');note=p.inner_text('#tie-note') if p.is_visible('#tie-note') else ''
    rk=[p.locator('#standings-body tr').nth(i).locator('td').first.inner_text() for i in range(4)]
    ok('tie: Desi is clear #1',p.locator('#standings-body tr').first.locator('td').nth(1).inner_text()=='Desi Steelers FC' and rk[0]=='1',rk)
    ok('tie: 3 tied teams flagged with = and banner asks for shoot-out',rk[1:]==['2=','2=','2='] and 'shoot-out needed' in note,(rk,note))
    db=scenario_post_tie();db['tiebreak_shootout_order']=[{'season_id':'season1','team_id':db['_ids']['T']['Renegades'],'position':1},{'season_id':'season1','team_id':db['_ids']['T']['Scouts FC'],'position':2},{'season_id':'season1','team_id':db['_ids']['T']['Muggles FC'],'position':3}]
    s3=Site(pw,db);p=s3.page('index.html')
    order=[p.locator('#standings-body tr').nth(i).locator('td').nth(1).inner_text() for i in range(4)];rk=[p.locator('#standings-body tr').nth(i).locator('td').first.inner_text() for i in range(4)]
    ok('tie: shoot-out order gives unique ranks 1-4',order==['Desi Steelers FC','Renegades','Scouts FC','Muggles FC'] and rk==['1','2','3','4'] and not p.is_visible('#tie-note'),(order,rk))
    db=scenario_post_tie();db['matches'].append({'id':'mx','season_id':'season1','match_day':4,'match_number':1,'home_team_id':'t4','away_team_id':'t5','status':'scheduled','home_score':None,'away_score':None,'forfeited_by_team_id':None,'kickoff_at':None})
    db['tiebreak_shootout_order']=[{'season_id':'season1','team_id':db['_ids']['T']['Renegades'],'position':1}]
    s4=Site(pw,db);p=s4.page('index.html')
    ok('tie: shoot-out ignored while tournament incomplete (shared rank, "only after all matches" note)',p.is_visible('#tie-note') and 'shoot-out needed' not in p.inner_text('#tie-note') and 'after all matches' in p.inner_text('#tie-note') and p.locator('#standings-body tr').nth(1).locator('td').first.inner_text()=='2=')
    # ---------- Day 1 reality: ranks 1,2,2,4 ----------
    b=base();m=b['m']
    m(1,1,'Muggles FC','Desi Steelers FC','completed',0,0);m(1,2,'Renegades','Scouts FC','completed',0,0)
    m(1,3,'Renegades','Desi Steelers FC','completed',0,0);m(1,4,'Muggles FC','Scouts FC','completed',1,2)
    m(2,1,'Scouts FC','Desi Steelers FC');m(2,2,'Muggles FC','Renegades')
    sd=Site(pw,finish(b));p=sd.page('index.html')
    rows=[[c for c in p.locator('#standings-body tr').nth(i).locator('td').all_inner_texts()] for i in range(4)]
    ok('day1: ranks read 1, 2=, 2=, 4',[r[0] for r in rows]==['1','2=','2=','4'],rows)
    hdr=p.locator('table thead th').all_inner_texts()
    ok('standings headers: # Team Pts P W D L GD GF GA',[h.strip().upper() for h in hdr[:10]]==['#','TEAM','PTS','P','W','D','L','GD','GF','GA'],hdr)
    exp={'Scouts FC':['3','2','1','1','0','1','2','1'],'Desi Steelers FC':['2','2','0','2','0','0','0','0'],'Renegades':['2','2','0','2','0','0','0','0'],'Muggles FC':['1','2','0','1','1','-1','1','2']}
    got={r[1]:[c.strip() for c in r[2:]] for r in rows}
    ok('day1: every standings value correct (Pts P W D L GD GF GA)',got==exp,got)
    tid=sd.page('team.html?id=%s'%finish(b)['_ids']['T']['Scouts FC'],1500)
    th=[h.strip().upper() for h in tid.locator('table thead').first.locator('th').all_inner_texts()]
    tv=[c.strip() for c in tid.locator('#team-totals-body td').all_inner_texts()]
    ok('team page: same column order and Scouts values',th==['PTS','P','W','D','L','GD','GF','GA'] and tv==exp['Scouts FC'],(th,tv))
    sc=sd.page('team.html?id=%s'%finish(b)['_ids']['T']['Scouts FC'],1500)
    ok('team page: single top scorer/POTM unaffected when no events','—' in sc.inner_text('#top-scorer-season'),sc.inner_text('#top-scorer-season'))
    b2=base();m2=b2['m'];m2(1,1,'Muggles FC','Scouts FC','completed',1,2);d2=finish(b2);T2=d2['_ids']['T'];P2=d2['_ids']['P']
    d2['team_season_rosters']+=[{'id':'rr%d'%i,'season_id':'season1','team_id':T2['Scouts FC'],'player_id':P2[n],'is_owner':False,'jersey_number':None} for i,n in enumerate(['Ajinkya P','Rishabh Devgon','Vignesh'])]
    d2['match_events']=[{'id':'q%d'%i,'match_id':'m0','team_id':T2['Scouts FC'],'player_id':P2[n],'event_type':t,'half':1,'minute':None,'related_player_id':None} for i,(n,t) in enumerate([('Ajinkya P','goal'),('Rishabh Devgon','goal'),('Vignesh','goal'),('Vignesh','goal'),('Ajinkya P','player_of_match'),('Rishabh Devgon','player_of_match')])]
    tp=Site(pw,d2).page('team.html?id=%s'%T2['Scouts FC'],1500)
    ts=tp.inner_text('#top-scorer-season');tpm=tp.inner_text('#top-potm-season')
    ok('team page: tie for top POTM lists both names',('Ajinkya P' in tpm and 'Rishabh Devgon' in tpm and '(1 each)' in tpm),tpm)
    ok('team page: single top scorer shows one name',ts.startswith('Vignesh') and 'Ajinkya' not in ts and '(2)' in ts,ts)
    ok('day1: Scouts 3pts first; Desi+Renegades level (2pts, GD0, GF0); Muggles last',rows[0][1]=='Scouts FC' and rows[0][2]=='3' and {rows[1][1],rows[2][1]}=={'Desi Steelers FC','Renegades'} and rows[3][1]=='Muggles FC' and rows[3][2]=='1',rows)
    # ---------- admin ----------
    sa=Site(pw,scenario_played(),admin=True);p=sa.page('admin/dashboard.html',1200)
    ok('admin: dashboard loads, no errors',not p.errs,p.errs);p.click('button[data-tab=matches]')
    ok('admin: shoot-out card present',p.locator('#shootout-form').count()==1 and p.locator('#shootout-teams input').count()==4,p.locator('#shootout-teams input').count())
    # shoot-out blocked while matches open
    p.locator('#shootout-teams input').first.fill('1');p.locator('#shootout-form button[type=submit]').click();p.wait_for_timeout(500)
    ok('admin: shoot-out save blocked while season incomplete','Not allowed yet' in p.inner_text('#shootout-msg') and len(p.evaluate("__DB.tiebreak_shootout_order"))==0,p.inner_text('#shootout-msg'))
    # completed without scores must be blocked
    f=p.locator('.result-form').nth(1);f.locator('select[name=status]').select_option('completed');f.locator('button[type=submit]').click();p.wait_for_timeout(500)
    ok('admin: completed match without scores is blocked',any('Enter both scores' in e for e in p.errs) and p.evaluate("__DB.matches[1].status")=='scheduled',(p.errs,p.evaluate("__DB.matches[1].status")))
    f.locator('input[name=home_score]').fill('2');f.locator('input[name=away_score]').fill('2');f.locator('button[type=submit]').click();p.wait_for_timeout(600)
    ok('admin: saving scores completes match',p.evaluate("__DB.matches[1].status")=='completed' and p.evaluate("__DB.matches[1].home_score")==2)
    ok('admin: no per-match shoot-out dropdown',p.locator('select[name=shootout]').count()==0)
    # complete-season admin: duplicate positions rejected, unique saved
    dbc=scenario_post_tie();sb=Site(pw,dbc,admin=True);p=sb.page('admin/dashboard.html',1200);p.click('button[data-tab=matches]')
    ins=p.locator('#shootout-teams input')
    for k in range(3):ins.nth(k).fill('1')
    p.locator('#shootout-form button[type=submit]').click();p.wait_for_timeout(500)
    ok('admin: duplicate shoot-out positions rejected','unique' in p.inner_text('#shootout-msg').lower(),p.inner_text('#shootout-msg'))
    for k in range(3):ins.nth(k).fill(str(k+1))
    p.locator('#shootout-form button[type=submit]').click();p.wait_for_timeout(600)
    ok('admin: unique shoot-out order saved on complete season',p.inner_text('#shootout-msg')=='Saved.' and len(p.evaluate("__DB.tiebreak_shootout_order"))==3,p.inner_text('#shootout-msg'))
    # non-admin redirected
    sn=Site(pw,scenario_played(),admin=False);p=sn.page('admin/dashboard.html',1200)
    ok('admin: non-admin is redirected to login','login' in p.url,p.url)
print(f"\n{sum(1 for _,c in R if c)} passed, {sum(1 for _,c in R if not c)} failed")
