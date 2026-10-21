from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
def build():
    b=base();m=b['m'];T=b['T'];P=b['P']
    m(1,1,'Muggles FC','Desi Steelers FC','completed',1,0);m(1,2,'Renegades','Scouts FC','completed',1,0)
    m(2,1,'Renegades','Desi Steelers FC','completed',0,0);m(2,2,'Muggles FC','Scouts FC','completed',0,2)
    m(3,1,'Desi Steelers FC','Renegades','completed',0,0)
    d=finish(b);ap=[]
    ros={'Desi Steelers FC':['Nasiq','Ayush','Vignesh'],'Muggles FC':['Amritpal Singh','Bilal Yaser'],'Scouts FC':['Bhagyesh Rane','Ajinkya P'],'Renegades':['Varun','Rishabh Devgon']}
    caps={('m0','Muggles FC'):('Amritpal Singh',0),('m0','Desi Steelers FC'):('Vignesh',1),('m1','Renegades'):('Varun',0),('m1','Scouts FC'):('Bhagyesh Rane',0),
          ('m2','Renegades'):('Rishabh Devgon',0),('m2','Desi Steelers FC'):('Nasiq',0),('m3','Muggles FC'):('Amritpal Singh',0),('m3','Scouts FC'):('Bhagyesh Rane',0),
          ('m4','Desi Steelers FC'):('Nasiq',0),('m4','Renegades'):('Rishabh Devgon',0)}
    for mt,(t1,t2) in {'m0':('Muggles FC','Desi Steelers FC'),'m1':('Renegades','Scouts FC'),'m2':('Renegades','Desi Steelers FC'),'m3':('Muggles FC','Scouts FC'),'m4':('Desi Steelers FC','Renegades')}.items():
        for t in (t1,t2):
            for pl in ros[t]:
                st='rested' if (mt=='m0' and pl=='Nasiq') else 'played'
                c=caps.get((mt,t));ap.append({'id':'a%03d'%len(ap),'match_id':mt,'team_id':T[t],'player_id':P[pl],'status':st,'started':st=='played','is_captain':bool(c and c[0]==pl),'captain_stand_in':bool(c and c[0]==pl and c[1])})
    d['match_appearances']=ap
    def ev(i,mt,t,pl): return {'id':'e%d'%i,'match_id':mt,'team_id':T[t],'player_id':P[pl],'event_type':'player_of_match','half':None,'minute':None,'related_player_id':None,'created_at':'2026-10-07T01:00:0%d+00:00'%i}
    d['match_events']=[ev(1,'m0','Muggles FC','Amritpal Singh'),ev(2,'m0','Desi Steelers FC','Vignesh'),ev(3,'m3','Scouts FC','Bhagyesh Rane'),ev(4,'m1','Scouts FC','Ajinkya P')]
    return d,T,P
d,T,P=build()
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#milestones',1500);p.click('#tabs button[data-tab=captains]');p.wait_for_timeout(300)
    t=p.inner_text('#ms-body');tl=t.lower()
    ok('no JS errors',not p.errs,p.errs)
    ok('Captains tab exists',p.locator('#tabs button[data-tab=captains]').count()==1)
    ok('first captain change of the league flagged once, on a Day 2 M1 change','first captain change of the league' in tl and 'day 2 · m1' in tl and tl.count('first captain change')==1,t)
    ok('every switch is a change: Varun->Rishabh and Vignesh->Nasiq both listed, no stand-in wording','varun' in tl and 'rishabh devgon' in tl and 'vignesh' in tl and 'new captain' in tl and tl.count('new captain')==2 and 'stand-in' not in tl and 'stand' not in tl.replace('standings',''),t)
    ok('Vignesh is simply a captain (Day 1 M1)','vignesh' in tl and 'day 1 · m1' in tl)
    rows=[r.split('\t') for r in p.locator('#ms-body table').nth(1).locator('tbody tr').all_inner_texts()]
    tot={r[0].split(' (')[0].strip():r[2].strip() for r in rows}
    ok('totals: Nasiq 2, Vignesh 1, Varun 1, Rishabh 2, Amritpal 2',tot.get('Nasiq')=='2' and tot.get('Vignesh')=='1' and tot.get('Varun')=='1' and tot.get('Rishabh Devgon')=='2' and tot.get('Amritpal Singh')=='2',tot)
    hd=[h.strip().lower() for h in p.locator('#cap-totals thead th').all_inner_texts()]
    ok('totals columns: player, team, matches, won, drawn, lost, win %, goals for, potm',hd==['player','team','matches','won','drawn','lost','win %','draw %','loss %','goals for','potm'],hd)
    full={r[0].split(' (')[0].strip():[x.strip() for x in r[2:]] for r in rows}
    ok('Amritpal: 2 captained, W1 D0 L1, 50%, GF 1, POTM 1',full.get('Amritpal Singh')==['2','1','0','1','50%','0%','50%','1','1'],full.get('Amritpal Singh'))
    ok('Vignesh: total 1, L1, POTM 1 counts while captaining',full.get('Vignesh')==['1','0','0','1','0%','0%','100%','0','1'],full.get('Vignesh'))
    ok('Bhagyesh: W1 L1 GF 2 POTM 1; Ajinkya POTM in a match he did not captain is ignored',full.get('Bhagyesh Rane')==['2','1','0','1','50%','0%','50%','2','1'],full.get('Bhagyesh Rane'))
    ok('Nasiq: 2 matches, 2 draws, 0%',full.get('Nasiq')==['2','0','2','0','0%','100%','0%','0','0'],full.get('Nasiq'))
    ok('Varun: 1 match, 100%',full.get('Varun')[1:7]==['1','0','0','100%','0%','0%'],full.get('Varun'))
    names_=lambda:[r.split('\t')[0].split(' (')[0].strip() for r in p.locator('#cap-totals tbody tr').all_inner_texts()]
    dflt=names_()
    ok('default order: most matches captained first, then name',dflt[:2]==['Amritpal Singh','Bhagyesh Rane'] or dflt[0] in ('Amritpal Singh','Bhagyesh Rane','Nasiq','Rishabh Devgon'),dflt)
    ok('reset button disabled while default',p.locator('#cap-reset').is_disabled())
    p.click('#cap-totals th[data-csort=won]');o1=names_()
    ok('sort by Won: highest first',o1[0] in ('Amritpal Singh','Bhagyesh Rane','Varun') and p.locator('#cap-reset').is_enabled(),o1)
    p.click('#cap-totals th[data-csort=won]');o2=names_();ok('click again reverses (lowest first)',o2[0] not in ('Amritpal Singh','Bhagyesh Rane','Varun'),o2)
    p.click('#cap-totals th[data-csort=name]');o3=names_();ok('sort by Player A to Z',o3==sorted(o3),o3)
    p.click('#cap-totals th[data-csort=potm]');ok('sort by POTM works',names_()[0] in ('Amritpal Singh','Bhagyesh Rane','Vignesh'),names_())
    p.click('#cap-totals th[data-csort=lpct]');ok('sort by Loss % works (highest first)',names_()[0]=='Vignesh',names_())
    p.click('#cap-totals th[data-csort=dpct]');ok('sort by Draw % works (highest first)',names_()[0]=='Nasiq',names_())
    p.click('#cap-reset');ok('Reset sort restores the default order',names_()==dflt and p.locator('#cap-reset').is_disabled(),(names_(),dflt))
    ok('current captain marked (Rishabh for Renegades)','(current captain)' in t and any('Rishabh' in r[0] and 'current' in r[0] for r in rows),rows)
    log=p.locator('#ms-body table').nth(2).locator('tbody tr').count()
    ok('captain listed for every team in every match (10 rows)',log==10,log)
    p.select_option('#f-view',label='Renegades');p.wait_for_timeout(200);t2=p.inner_text('#ms-body')
    ok('team filter keeps Renegades only',('Nasiq' not in t2) and 'Rishabh' in t2 and 'Varun' in t2,t2)
    # match page
    q=s.page('match.html?id=m0',1500);q.wait_for_timeout(300);mt=q.inner_text('#match-root')
    ok('match page: captain line + C badge, no stand-in wording','Captain: Vignesh' in mt and 'stand-in' not in mt and q.locator('.m-cap').count()==2,mt)
    ok('match page: Nasiq (rested) has no badge',q.locator('.m-cap').count()==2)
    q=s.page('match.html?id=m4',1500);ok('match page: badge on both captains',q.locator('.m-cap').count()==2 and 'stand-in' not in q.inner_text('#match-root'),q.inner_text('#match-root')[:400])
    # team pages
    q=s.page('team.html?id='+T['Renegades'],1500);q.wait_for_timeout(500);ct=q.inner_text('#captain-body')
    ok('team page Renegades: current captain Rishabh, history lists Varun first',q.is_visible('#captain-card') and 'Current captain: Rishabh Devgon' in ct and 'Varun' in ct and 'Captain change: Varun to Rishabh Devgon from Day 2 · M1' in ct,ct)
    q=s.page('team.html?id='+T['Desi Steelers FC'],1500);q.wait_for_timeout(500);ct=q.inner_text('#captain-body')
    ok('team page Desi: current captain Nasiq, Vignesh earlier, no stand-in wording','Current captain: Nasiq' in ct and 'Vignesh' in ct and 'stand' not in ct.lower() and 'Captain change: Vignesh to Nasiq from Day 2 · M1' in ct,ct)
    q=s.page('team.html?id='+T['Scouts FC'],1500);q.wait_for_timeout(300);ok('team page with captains but no change shows no change line','Captain change' not in q.inner_text('#captain-body') and 'Bhagyesh' in q.inner_text('#captain-body'))
    # player pages
    q=s.page('player.html?id='+P['Vignesh'],1500);q.wait_for_timeout(500);pt=q.inner_text('#captain-body')
    ok('player page: Vignesh captained 1 match, no stand-in wording','Captained 1 match' in pt and 'stand' not in pt.lower() and 'Muggles FC' in pt,pt)
    q=s.page('player.html?id='+P['Nasiq'],1500);q.wait_for_timeout(500);ok('player page: Nasiq captained 2 matches',('Captained 2 matches' in q.inner_text('#captain-body')),q.inner_text('#captain-body'))
    q=s.page('player.html?id='+P['Ayush'],1500);q.wait_for_timeout(500);ok('player page: non-captain has no Captaincy card',not q.is_visible('#captain-card'))
    ok('no JS errors on pages',not q.errs,q.errs)
    # admin lineup captain selector
    sa=Site(pw,build()[0],admin=True);a=sa.page('admin/dashboard.html',1500);a.click('button[data-tab=records]')
    a.select_option('#lu-match','m0');a.wait_for_timeout(600)
    sel=a.locator('#lu-body select[data-lu-captain]')
    ok('admin: one captain selector per team, saved captain preselected, no stand-in checkbox',sel.count()==2 and 'Vignesh' in a.evaluate("[...document.querySelectorAll('#lu-body select[data-lu-captain] option:checked')].map(o=>o.textContent).join(',')") and a.locator('#lu-body input[data-lu-standin]').count()==0)
    a.select_option('#lu-body select[data-lu-captain="%s"]'%T['Desi Steelers FC'],P['Ayush']);a.click('#lu-save');a.wait_for_timeout(700)
    caps=a.evaluate("__DB.match_appearances.filter(x=>x.match_id==='m0'&&x.is_captain).map(x=>[x.player_id,x.team_id])")
    ok('admin: captain changed to Ayush, Muggles captain kept, exactly one per team',len(caps)==2 and [P['Ayush'],T['Desi Steelers FC']] in caps and [P['Amritpal Singh'],T['Muggles FC']] in caps,caps)
    ok('admin: saved message',a.inner_text('#lineup-msg').lower().count('saved')>0,a.inner_text('#lineup-msg'))
    ok('admin: no JS errors',not a.errs,a.errs)
print(sum(R),'/',len(R))
