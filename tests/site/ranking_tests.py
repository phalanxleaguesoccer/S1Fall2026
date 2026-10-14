from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
m(1,1,'Muggles FC','Desi Steelers FC','completed',0,0);m(1,2,'Renegades','Scouts FC','completed',1,0)
m(1,3,'Renegades','Desi Steelers FC','completed',0,0);m(2,1,'Scouts FC','Muggles FC')
d=finish(b);ap=[]
def a(mt,team,pl,st): ap.append({'id':'a%02d'%len(ap),'match_id':mt,'team_id':T[team],'player_id':P[pl],'status':st,'started':st=='played'})
a('m0','Muggles FC','Amritpal Singh','played');a('m0','Muggles FC','Bilal Yaser','rested')
a('m0','Desi Steelers FC','Nasiq','played');a('m0','Desi Steelers FC','Ayush','absent');a('m0','Desi Steelers FC','Vignesh','played')
a('m1','Renegades','Varun','played');a('m1','Renegades','Rishabh Devgon','played');a('m1','Scouts FC','Bhagyesh Rane','played');a('m1','Scouts FC','Ajinkya P','rested')
d['match_appearances']=ap
ev=[]
def e(match,team,pl,typ):
    ev.append({'id':'e%02d'%len(ev),'match_id':match,'team_id':T[team],'player_id':P[pl],'event_type':typ,'half':1,'minute':None,'related_player_id':None,'created_at':'2026-10-07T01:00:%02d+00:00'%len(ev)})
e('m0','Desi Steelers FC','Nasiq','goal');e('m2','Desi Steelers FC','Nasiq','goal');e('m2','Desi Steelers FC','Nasiq','player_of_match')
e('m2','Desi Steelers FC','Ayush','goal');e('m2','Desi Steelers FC','Ayush','goal');e('m2','Desi Steelers FC','Ayush','assist')
e('m1','Renegades','Varun','goal');e('m1','Renegades','Varun','goal');e('m1','Renegades','Rishabh Devgon','assist')
e('m1','Renegades','Varun','yellow_card');e('m1','Scouts FC','Bhagyesh Rane','red_card')
e('m0','Muggles FC','Bilal Yaser','yellow_card')
d['match_events']=ev
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#ranking',1500)
    ok('no JS errors',not p.errs,p.errs)
    ok('third sub-nav item labelled Ranking (In QA)',p.locator('#sub-nav button').all_inner_texts()[-1].strip()=='Ranking (In QA)' and p.locator('#sub-nav button').count()==3)
    ok('modal visible with text and button',p.is_visible('#qa-modal') and "don't take it seriously yet" in p.inner_text('#qa-modal').lower() and p.inner_text('#qa-accept').strip()=='I accept',p.inner_text('#qa-modal'))
    blocked=True
    try:
        p.locator('#sub-nav button[data-sec="season"]').click(timeout=1500,trial=True);blocked=False
    except Exception: pass
    ok('other controls are blocked while modal is open',blocked)
    p.keyboard.press('Escape');ok('Esc does not close',p.is_visible('#qa-modal'))
    p.mouse.click(5,5);ok('backdrop click does not close',p.is_visible('#qa-modal'))
    p.click('#qa-accept');ok('I accept closes it',not p.is_visible('#qa-modal'))
    p.click('#sub-nav button[data-sec="season"]');p.click('#sub-nav button[data-sec="ranking"]')
    ok('not repeated within same visit',not p.is_visible('#qa-modal'))
    hdr=[h.strip().lower() for h in p.locator('#rk-body thead th').all_inner_texts()]
    ok('Points column after Team, then season columns',hdr[:5]==['#','player','team','points','p'] and 'absent' in hdr,hdr)
    rows=lambda:[r.split('\t') for r in p.locator('#rk-body tbody tr:not(.det)').all_inner_texts()]
    R0=rows();pc=hdr.index('points')
    pts={r[1].strip():r[pc].strip() for r in R0}
    ok('points values',pts.get('Ayush')=='9' and pts.get('Nasiq')=='9' and pts.get('Varun')=='7' and pts.get('Rishabh Devgon')=='5' and pts.get('Bhagyesh Rane')=='-5' and pts.get('Bilal Yaser')=='-2',pts)
    nm=[r[1].strip() for r in R0]
    ok('order: points desc, tie by season chain (Ayush before Nasiq)',nm[:4]==['Ayush','Nasiq','Varun','Rishabh Devgon'] and nm.index('Bhagyesh Rane')==len(nm)-3,nm)
    ok('0-match players below negative-points player',nm.index('Bhagyesh Rane')<nm.index('Bilal Yaser'),nm)
    ok('last row has 0 matches',R0[-1][hdr.index('p')].strip()=='0',R0[-1])
    ok('ranks 1..',[r[0].strip() for r in R0[:3]]==['1','2','3'],[r[0] for r in R0[:3]])
    p.locator('button[data-pdet]:visible').first.click()
    t=p.inner_text('tr.det:visible')
    ok('details breakdown shows total and rules',('Total points' in t) and ('Goals' in t) and ('Fouls' in t),t)
    p.locator('button[data-pdet]:visible').first.click()
    ok('details hides again',p.locator('tr.det:visible').count()==0)
    p.select_option('#r-team',label='Renegades');n=[r[1].strip() for r in rows()]
    ok('team filter',set(n)=={'Varun','Rishabh Devgon'} or 'Varun' in n and 'Ayush' not in n,n)
    p.select_option('#r-team','all');p.fill('#r-search','bhag');n=[r[1].strip() for r in rows()]
    ok('search',n==['Bhagyesh Rane'],n);p.fill('#r-search','')
    p.click('#rk-body th[data-sort="goals"]');ok('header sort works',rows()[0][1].strip() in ('Ayush','Nasiq','Varun'))
    p.select_option('#r-rest','rested');n=[r[1].strip() for r in rows()]
    ok('rested filter',set(n)=={'Bilal Yaser','Ajinkya P'},n)
    # Season Stats unchanged and has no Points
    p.click('#sub-nav button[data-sec="season"]')
    ok('Season Stats has no Points column','points' not in [h.strip().lower() for h in p.locator('#ss-body thead th').all_inner_texts()])
    p.close() if hasattr(p,'close') else None
    # fresh load of plain stats page: no modal
    p2=s.page('stats.html',1200);ok('no modal when Ranking not opened',not p2.is_visible('#qa-modal'))
    p2.click('#sub-nav button[data-sec="ranking"]');ok('modal when tab opened by click',p2.is_visible('#qa-modal'))
    # phone width
    p3=s.page('stats.html#ranking',1200)
    p3.set_viewport_size({'width':375,'height':800});p3.click('#qa-accept')
    ok('phone: no page sideways scroll',p3.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'))
    for w in (320,375,414,768,1024,1280):
        p3.set_viewport_size({'width':w,'height':900});p3.wait_for_timeout(150)
        r=p3.evaluate("(()=>{const t=document.querySelector('#rk-body .table-scroll');return [t.scrollWidth,t.clientWidth,document.documentElement.scrollWidth,window.innerWidth]})()")
        ok('no sideways scroll at %dpx'%w,r[0]<=r[1] and r[2]<=r[3]+1,r)
    ok('no JS errors (all pages)',not p2.errs and not p3.errs,[p2.errs,p3.errs])
print(sum(R),'/',len(R))
