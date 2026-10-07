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
    ok('Rested + Absent tabs exist',p.locator('[data-tab=rested]').count()==1 and p.locator('[data-tab=absent]').count()==1)
    rows=lambda:[r.replace('\t',' | ') for r in p.locator('#ms-body table').first.locator('tbody tr:not(.det)').all_inner_texts()]
    p.click('[data-tab=rested]');ok('Rested tab: Bilal (Muggles M1), Ajinkya P (Scouts M2) in match order',[r.split(' | ')[:4] for r in rows()]==[['1','Bilal Yaser','Muggles FC','Day 1 · M1'],['2','Ajinkya P','Scouts FC','Day 1 · M2']],rows())
    p.select_option('#f-view',T['Muggles FC']);body=p.inner_text('#ms-body').lower()
    heads=p.locator('#ms-body h3').all_inner_texts()
    ok('Rested per team: "Never rested" first (Amritpal, owner), then "Rested at least once" (Bilal x1)',[h.lower() for h in heads]==['never rested (1)','rested at least once (1)'] and body.index('amritpal')<body.index('rested at least once') and body.index('bilal')>body.index('rested at least once') and '(owner)' in body,(heads,body))
    p.locator('#ms-body table').nth(1).locator('[data-det]').first.click()
    link=p.locator('tr.det:visible a[href^="match.html"]')
    ok('Bilal details: played/rested/absent counts + rested match linking to match page',link.count()==1 and link.first.get_attribute('href')=='match.html?id=m0' and 'Day 1 · Match 1' in link.first.inner_text() and 'Desi Steelers FC' in link.first.inner_text(),p.inner_text('tr.det:visible'))
    link.first.click();p.wait_for_timeout(1200);ok('click on match opens that match page',p.url.endswith('match.html?id=m0') and 'muggles fc' in p.inner_text('#match-title').lower(),(p.url,p.inner_text('#match-title'),p.errs))
    p.go_back();p.wait_for_timeout(1200);p.click('[data-tab=rested]');p.select_option('#f-view',T['Muggles FC'])
    p.locator('#ms-body table').first.locator('[data-det]').first.click()
    ok('never-rested player details list matches played (Amritpal played Day1 M1)','Matches played' in p.inner_text('tr.det:visible') and p.locator('tr.det:visible a[href="match.html?id=m0"]').count()==1,p.inner_text('tr.det:visible'))
    p.select_option('#f-view','all')
    ok('Rested totals-per-player table present','total per player' in p.inner_text('#ms-body').lower() and 'Ajinkya P' in p.inner_text('#ms-body'))
    p.select_option('#f-view','all');p.click('[data-tab=absent]');ok('Absent tab: Ayush / Desi Steelers',[r.split(' | ')[:3] for r in rows()]==[['1','Ayush','Desi Steelers FC']],rows())
    p.select_option('#f-view',T['Desi Steelers FC']);hh=[h.lower() for h in p.locator('#ms-body h3').all_inner_texts()]
    ok('Absent per team (Desi): never absent 2 (Nasiq owner, Vignesh), absent at least once 1 (Ayush)',hh==['never absent (2)','absent at least once (1)'] and 'ayush' in p.inner_text('#ms-body').lower().split('absent at least once')[1],hh)
    p.select_option('#f-view',T['Renegades']);ok('Absent tab, team with nobody absent: everyone listed under never absent',p.inner_text('#ms-body').lower().count('never absent (2)')==1 and 'absent at least once (0)' in p.inner_text('#ms-body').lower(),p.inner_text('#ms-body'))
    # match page
    q=s.page('match.html?id=m0',1500);lt=q.inner_text('#lineups')
    ok('match page lineups: played/rested/absent per team',q.is_visible('#lineups-card') and 'Rested (1): Bilal Yaser' in lt and 'Absent (1): Ayush' in lt and 'Played (2): Amritpal Singh' in lt.replace('\n',' ') or ('Played (2)' in lt and 'Nasiq' in lt),lt)
    q=s.page('match.html?id=m3',1200);ok('match page without lineup: no lineup card, no errors',not q.is_visible('#lineups-card') and not q.errs,q.errs)
    # schedule
    q=s.page('matches.html',1500);bt=q.inner_text('#days-list')
    ok('schedule shows rested/absent counts',('Rested: Muggles FC 1' in bt) and ('Absent: Desi Steelers FC 1' in bt) and ('Rested: Scouts FC 1' in bt),bt)
    # profile
    q=s.page('player.html?id='+P['Ayush'],1500);hd=q.locator('table thead').first.locator('th').all_inner_texts();vals=q.locator('#stats-body td').all_inner_texts()
    ok('profile: Rested/Absent columns; Ayush absent 1, GP 1 (only M3, which has no lineup)',[h.upper() for h in hd][2:5]==['GP','RESTED','ABSENT'] and vals[2:5]==['1','0','1'],(hd,vals))   # GP 1 = match 3 had no lineup entered (legacy: counts as played)
    q=s.page('player.html?id='+P['Bilal Yaser'],1500);vals=q.locator('#stats-body td').all_inner_texts()
    ok('profile: Bilal GP 0 (rested), rested 1',vals[2:5]==['0','1','0'],vals)
    q=s.page('player.html?id='+P['Vignesh'],1500);vals=q.locator('#stats-body td').all_inner_texts()
    ok('profile: Vignesh played M1 (GP 1); M3 had no lineup rows for Desi -> legacy count only if team has none',vals[2:5][0] in ('1','2'),vals)
    q.click('#history-toggle');q.wait_for_timeout(300);ok('career totals + season table have Rested/Absent',q.locator('#career-totals-body td').count()==10 and 'rested' in q.inner_text('#history-seasons-view').lower(),q.locator('#career-totals-body td').count())
    # team page
    q=s.page('team.html?id='+T['Desi Steelers FC'],1500);cards=q.locator('#roster-grid .player-card').all_inner_texts()
    ok('team page squad: counts per player (Ayush: Played 1 · Rested 0 · Absent 1)',any('Ayush' in c and 'Played 1' in c and 'Absent 1' in c for c in cards),cards)
    # admin lineup form
    sa=Site(pw,build()[0],admin=True);a=sa.page('admin/dashboard.html',1500);a.click('button[data-tab=records]')
    a.select_option('#lu-match','m3' if False else 'm1');a.wait_for_timeout(600)
    ok('admin: lineup form lists both squads, saved statuses preselected',a.locator('#lu-body select').count()==4 and a.locator('#lu-body select[data-lu-player="%s"]'%P['Ajinkya P']).input_value()=='rested',a.locator('#lu-body select').count())
    a.select_option('#lu-body select[data-lu-player="%s"]'%P['Varun'],'absent');a.click('#lu-save');a.wait_for_timeout(600)
    rowsdb=a.evaluate("__DB.match_appearances.filter(x=>x.match_id==='m1')")
    ok('admin: saved, status updated, no duplicate rows',len(rowsdb)==4 and [r['status'] for r in rowsdb if r['player_id']==P['Varun']]==['absent'] and 'saved' in a.inner_text('#lineup-msg').lower(),(len(rowsdb),a.inner_text('#lineup-msg')))
    a.select_option('#lu-match','m3');a.wait_for_timeout(600)
    ok('admin: new match defaults everyone to Played',set(a.locator('#lu-body select').evaluate_all('els=>els.map(e=>e.value)'))=={'played'})
    a.click('#lu-save');a.wait_for_timeout(600);ok('admin: first-time save creates all rows as played',a.evaluate("__DB.match_appearances.filter(x=>x.match_id==='m3').length")==4,a.evaluate("__DB.match_appearances.filter(x=>x.match_id==='m3').length"))
    ok('admin: no JS errors',not a.errs,a.errs)
print(sum(R),'passed',len(R)-sum(R),'failed')
