from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
def build():
    b=base();m=b['m'];T=b['T'];P=b['P']
    m(1,1,'Muggles FC','Desi Steelers FC','completed',1,0);m(1,2,'Renegades','Scouts FC','completed',1,0)
    m(2,1,'Renegades','Desi Steelers FC','completed',0,0);m(2,2,'Muggles FC','Scouts FC','completed',0,2);m(3,1,'Desi Steelers FC','Renegades')
    d=finish(b);ap=[]
    ros={'Desi Steelers FC':['Nasiq','Ayush','Vignesh'],'Muggles FC':['Amritpal Singh','Bilal Yaser'],'Scouts FC':['Bhagyesh Rane','Ajinkya P'],'Renegades':['Varun','Rishabh Devgon']}
    teams={'m0':('Muggles FC','Desi Steelers FC'),'m1':('Renegades','Scouts FC'),'m2':('Renegades','Desi Steelers FC'),'m3':('Muggles FC','Scouts FC'),'m4':('Desi Steelers FC','Renegades')}
    for mt,ts in teams.items():
        for t in ts:
            for pl in ros[t]:
                st='played';rs=None
                if pl=='Ayush': st={'m0':'rested','m2':'absent','m4':'absent'}[mt] ; rs='injury' if mt in('m0','m2','m4') else None
                if pl=='Bilal Yaser' and mt=='m0': st='absent'       # absent but NOT injury
                ap.append({'id':'a%03d'%len(ap),'match_id':mt,'team_id':T[t],'player_id':P[pl],'status':st,'started':st=='played','absent_reason':rs})
    d['match_appearances']=ap;d['match_events']=[]
    # a second, older season with one injury
    d['seasons'].append({'id':'season0','name':'Season 0 Spring 2026','is_current':False,'points_win':2,'points_draw':1,'points_loss':0,'created_at':'2025-12-01'})
    d['matches'].append({'id':'mx','season_id':'season0','match_day':1,'match_number':1,'home_team_id':T['Scouts FC'],'away_team_id':T['Muggles FC'],'status':'completed','home_score':1,'away_score':1,'kickoff_at':'2026-03-01T21:00:00-04:00'})
    d['match_appearances'].append({'id':'ax','match_id':'mx','team_id':T['Scouts FC'],'player_id':P['Ajinkya P'],'status':'absent','started':False,'absent_reason':'injury'})
    return d,T,P
d,T,P=build()
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#milestones',1500);p.click('#tabs button[data-tab=injury]');p.wait_for_timeout(500)
    ok('no JS errors',not p.errs,p.errs)
    ok('Injury tab exists',p.locator('#tabs button[data-tab=injury]').count()==1)
    sel=p.locator('#inj-season');opts=sel.locator('option').all_inner_texts()
    ok('season filter: each season + All seasons, current preselected',opts==['Season 1 Fall 2026','Season 0 Spring 2026','All seasons'] and sel.input_value()=='season1',opts)
    t1=lambda:[r.split('\t') for r in p.locator('#ms-body table').nth(0).locator('tbody tr').all_inner_texts()]
    t2=lambda:[r.split('\t') for r in p.locator('#ms-body table').nth(1).locator('tbody tr').all_inner_texts()]
    ok('current season: Ayush missed 2 (1 rested + 1 absent, both marked injury; Bilal absent but not injured not counted; scheduled Day 3 not counted)',[(r[0],r[2].strip(),r[3].strip(),r[4].strip()) for r in t1()]==[('Ayush','2','1','1')],t1())
    ok('every match missed lists 2 rows with status, opponent and result',len(t2())==2 and 'Rested' in ' '.join(t2()[0]) and 'Absent' in ' '.join(t2()[1]) and 'Renegades' in ' '.join(t2()[1]) and 'Drew 0–0' in ' '.join(t2()[1]),t2())
    p.select_option('#inj-season','season0');p.wait_for_timeout(300)
    ok('Season 0: Ajinkya P 1 match',[(r[0],r[2].strip()) for r in t1()]==[('Ajinkya P','1')],t1())
    p.select_option('#inj-season','all');p.wait_for_timeout(300)
    ok('All seasons: Ayush 2 + Ajinkya P 1, 3 matches listed',sorted((r[0],r[2].strip()) for r in t1())==[('Ajinkya P','1'),('Ayush','2')] and len(t2())==3,(t1(),t2()))
    ok('scheduled (not played yet) match not counted',all('Day 3' not in r for r in [' '.join(x) for x in t2()]))
    # other tabs still work after visiting Injury
    p.click('#tabs button[data-tab=availability]');p.wait_for_timeout(300);ok('Availability tab works; injury absence shown as A✚',p.locator('.av-table').count()>=1 and 'Ayush' in p.inner_text('#ms-body') and p.locator('.av-b.a',has_text='✚').count()>=1,p.inner_text('#ms-body')[:300])
    ok('Availability grid: rested+injury shown as R✚',p.locator('.av-b.r',has_text='✚').count()>=1,p.inner_text('#ms-body')[:300])
    # match page
    q=s.page('match.html?id=m2',1500);mt=q.inner_text('#match-root');ok('match page: absent injured player tagged (injury)','Ayush' in mt and '(injury)' in mt,mt)
    q=s.page('match.html?id=m0',1500);ok('match page: rested injured player tagged, absent non-injury player (Bilal) not tagged','Ayush (injury)' in q.inner_text('#match-root').replace('\n',' ') and 'Bilal Yaser (injury)' not in q.inner_text('#match-root'),q.inner_text('#match-root'))
    # admin
    sa=Site(pw,build()[0],admin=True);a=sa.page('admin/dashboard.html',1500);a.click('button[data-tab=records]')
    a.select_option('#lu-match','m2');a.wait_for_timeout(600)
    ok('admin: injury box ticked for Ayush, not for others',a.locator('#lu-body input[data-lu-injury]:checked').count()==1 and a.locator('#lu-body input[data-lu-injury="%s"]'%P['Ayush']).is_checked())
    a.select_option('#lu-body select[data-lu-player="%s"]'%P['Varun'],'absent');a.check('#lu-body input[data-lu-injury="%s"]'%P['Varun']);a.uncheck('#lu-body input[data-lu-injury="%s"]'%P['Ayush']);a.click('#lu-save');a.wait_for_timeout(700)
    rs=a.evaluate("__DB.match_appearances.filter(x=>x.match_id==='m2').map(x=>[x.player_id,x.status,x.absent_reason])")
    ok('admin: Varun absent+injury saved, Ayush injury cleared, others null',[P['Varun'],'absent','injury'] in rs and [P['Ayush'],'absent',None] in rs and all(r[2] is None for r in rs if r[0] not in (P['Varun'],)),rs)
    # injury tick on a Played player is ignored
    a.check('#lu-body input[data-lu-injury="%s"]'%P['Rishabh Devgon']);a.click('#lu-save');a.wait_for_timeout(700)
    ok('admin: injury tick ignored unless Absent',a.evaluate("__DB.match_appearances.find(x=>x.match_id==='m2'&&x.player_id==='%s').absent_reason"%P['Rishabh Devgon']) is None)
    a.select_option('#lu-match','m0');a.wait_for_timeout(600)
    ok('admin: rested player with injury ticked is preloaded',a.locator('#lu-body input[data-lu-injury="%s"]'%P['Ayush']).is_checked())
    a.check('#lu-body input[data-lu-injury="%s"]'%P['Bilal Yaser']);a.select_option('#lu-body select[data-lu-player="%s"]'%P['Bilal Yaser'],'rested');a.click('#lu-save');a.wait_for_timeout(700)
    ok('admin: injury tick saved for a Rested player too',a.evaluate("__DB.match_appearances.find(x=>x.match_id==='m0'&&x.player_id==='%s').absent_reason"%P['Bilal Yaser'])=='injury')
    ok('admin: no JS errors',not a.errs,a.errs)
print(sum(R),'/',len(R))
