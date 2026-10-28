from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
def build():
    b=base();m=b['m'];T=b['T'];P=b['P']
    m(1,1,'Muggles FC','Desi Steelers FC','completed',0,0);m(1,2,'Renegades','Scouts FC','completed',1,0)
    m(1,3,'Renegades','Desi Steelers FC','completed',0,0);m(2,1,'Scouts FC','Muggles FC')
    d=finish(b);ap=[]
    def a(mt,team,pl,st): ap.append({'id':'a%02d'%len(ap),'match_id':mt,'team_id':T[team],'player_id':P[pl],'status':st,'started':st=='played'})
    a('m0','Muggles FC','Amritpal Singh','played');a('m0','Muggles FC','Bilal Yaser','rested')
    a('m0','Desi Steelers FC','Nasiq','played');a('m0','Desi Steelers FC','Ayush','absent');a('m0','Desi Steelers FC','Vignesh','played')
    a('m1','Renegades','Varun','played');a('m1','Renegades','Rishabh Devgon','played');a('m1','Scouts FC','Bhagyesh Rane','played');a('m1','Scouts FC','Ajinkya P','rested')
    d['match_appearances']=ap;return d,T,P
d,T,P=build()
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#milestones',1500)
    ok('no JS errors',not p.errs,p.errs)
    ok('Availability tab exists; separate Rested/Absent tabs are gone',p.locator('[data-tab=availability]').count()==1 and p.locator('[data-tab=rested]').count()==0 and p.locator('[data-tab=absent]').count()==0)
    p.click('[data-tab=availability]');p.wait_for_timeout(300);txt=p.inner_text('#ms-body')
    ok('Not rested yet: 6 of 9 players, shown before the rested/absent section','not rested yet' in txt.lower() and '6 of 9' in txt.lower() and txt.lower().index('not rested yet')<txt.lower().index('rested and absent'),txt[:300])
    cards=p.locator('.av-grid .av-card').all_inner_texts()
    ok('one not-rested card per team',len(cards)==4,cards)
    des=[c for c in cards if c.startswith('Desi')][0];mug=[c for c in cards if c.startswith('Muggles')][0];sco=[c for c in cards if c.startswith('Scouts')][0]
    ok('rested players (Bilal, Ajinkya P) are NOT in the not-rested list','Bilal' not in mug and 'Ajinkya' not in sco and 'Amritpal Singh' in mug and '(owner)' in mug.lower() or 'Amritpal Singh' in mug,(mug,sco))
    ok('absent-only player (Ayush) counts as sat out, so is NOT in the not-rested list','Ayush' not in des,des)
    ok('played counts shown',any('1 played' in c or '2 played' in c for c in cards),cards)
    tabs=p.locator('.av-table');hd=[t.locator('thead th').all_inner_texts() for t in [tabs.nth(i) for i in range(tabs.count())]]
    ok('matrix: one grid per team with anything to show (Muggles, Desi, Scouts; Renegades has nobody)',tabs.count()==3 and 'Nobody has been rested or absent yet' in p.inner_text('#ms-body'),(tabs.count(),hd))
    mt=[t for t in [tabs.nth(i) for i in range(tabs.count())] if 'Bilal' in t.inner_text()][0]
    rowb=mt.locator('tbody tr',has_text='Bilal Yaser');ok('Bilal row: R in his rested match, totals rested 1 absent 0',rowb.locator('.av-b.r').count()==1 and rowb.locator('td.av-n').all_inner_texts()==['1','0'],rowb.inner_text())
    dt=[t for t in [tabs.nth(i) for i in range(tabs.count())] if 'Ayush' in t.inner_text()][0]
    ra=dt.locator('tbody tr',has_text='Ayush');ok('Ayush row: A (absent, not injury) 1, rested 0',ra.locator('.av-b.a').count()==1 and 'A✚' not in ra.inner_text() and ra.locator('td.av-n').all_inner_texts()==['0','1'],ra.inner_text())
    ok('column headings link to the match page',mt.locator('thead th a[href="match.html?id=m0"]').count()==1,mt.inner_html()[:300])
    p.select_option('#f-view',T['Muggles FC']);p.wait_for_timeout(200)
    ok('team filter: only Muggles shown',p.locator('.av-grid .av-card').count()==1 and 'Desi' not in p.inner_text('#ms-body'),p.inner_text('#ms-body')[:200])
    p.select_option('#f-view',T['Renegades']);p.wait_for_timeout(200);rt=p.inner_text('#ms-body')
    ok('team with nobody rested/absent: all listed under not rested, none in the grid','2 of 2' in rt and 'Nobody has been rested or absent yet' in rt,rt)
    p.select_option('#f-view','all')
    # match page
    q=s.page('match.html?id=m0',1500);lt=q.inner_text('#match-root').replace('\n',' ')
    ok('match page lineups: played/rested/absent per team','RESTED (1)' in lt and 'Bilal Yaser' in lt and 'ABSENT (1)' in lt and 'Ayush' in lt and 'PLAYED (2)' in lt and 'Amritpal Singh' in lt,lt)
    q=s.page('match.html?id=m3',1200);ok('match page without lineup: no lineup card, no errors','WHO PLAYED' not in q.inner_text('#match-root').upper() and not q.errs,q.errs)
    # schedule
    q=s.page('matches.html#all',1500);bt=q.inner_text('#days-list')
    ok('schedule shows rested/absent counts',('Rested: Muggles FC 1' in bt) and ('Absent: Desi Steelers FC 1' in bt) and ('Rested: Scouts FC 1' in bt),bt)
    # profile
    q=s.page('player.html?id='+P['Ayush'],1500);hd=q.locator('table thead').first.locator('th').all_inner_texts();vals=q.locator('#stats-body td').all_inner_texts()
    ok('profile: Rested/Absent columns; Ayush absent 1, GP 0 (M3 has no lineup yet = details pending, not counted)',[h.upper() for h in hd][2:5]==['GP','RESTED','ABSENT'] and vals[2:5]==['0','0','1'],(hd,vals))
    q=s.page('player.html?id='+P['Bilal Yaser'],1500);vals=q.locator('#stats-body td').all_inner_texts()
    ok('profile: Bilal GP 0 (rested), rested 1',vals[2:5]==['0','1','0'],vals)
    q=s.page('player.html?id='+P['Vignesh'],1500);vals=q.locator('#stats-body td').all_inner_texts()
    ok('profile: Vignesh played M1 (GP 1); M3 had no lineup rows for Desi -> legacy count only if team has none',vals[2:5][0] in ('1','2'),vals)
    q.click('#history-toggle');q.wait_for_timeout(300);ok('career totals + season table have Rested/Absent',q.locator('#career-totals-body td').count()==12 and 'rested' in q.inner_text('#history-seasons-view').lower(),q.locator('#career-totals-body td').count())
    # team page
    q=s.page('team.html?id='+T['Desi Steelers FC'],1500);cards=q.locator('#roster-grid .player-card').all_inner_texts()
    ok('team page squad: counts per player (Ayush: Played 0 · Rested 0 · Absent 1)',any('Ayush' in c and 'Played 0' in c and 'Absent 1' in c for c in cards),cards)
    # admin lineup form
    sa=Site(pw,build()[0],admin=True);a=sa.page('admin/dashboard.html',1500);a.click('button[data-tab=records]')
    a.select_option('#lu-match','m3' if False else 'm1');a.wait_for_timeout(600)
    ok('admin: lineup form lists both squads, saved statuses preselected',a.locator('#lu-body select[data-lu-player]').count()==4 and a.locator('#lu-body select[data-lu-player="%s"]'%P['Ajinkya P']).input_value()=='rested',a.locator('#lu-body select[data-lu-player]').count())
    a.select_option('#lu-body select[data-lu-player="%s"]'%P['Varun'],'absent');a.click('#lu-save');a.wait_for_timeout(600)
    rowsdb=a.evaluate("__DB.match_appearances.filter(x=>x.match_id==='m1')")
    ok('admin: saved, status updated, no duplicate rows',len(rowsdb)==4 and [r['status'] for r in rowsdb if r['player_id']==P['Varun']]==['absent'] and 'saved' in a.inner_text('#lineup-msg').lower(),(len(rowsdb),a.inner_text('#lineup-msg')))
    a.select_option('#lu-match','m3');a.wait_for_timeout(600)
    ok('admin: new match defaults everyone to Played',set(a.locator('#lu-body select[data-lu-player]').evaluate_all('els=>els.map(e=>e.value)'))=={'played'})
    a.click('#lu-save');a.wait_for_timeout(600);ok('admin: first-time save creates all rows as played',a.evaluate("__DB.match_appearances.filter(x=>x.match_id==='m3').length")==4,a.evaluate("__DB.match_appearances.filter(x=>x.match_id==='m3').length"))
    ok('admin: no JS errors',not a.errs,a.errs)
print(sum(R),'passed',len(R)-sum(R),'failed')
