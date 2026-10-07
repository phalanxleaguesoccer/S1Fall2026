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
d['match_events']=ev
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html',1500)
    ok('no JS errors',not p.errs,p.errs)
    ok('Season Stats opens first, Milestones hidden',p.is_visible('#sec-season') and not p.is_visible('#sec-milestones'))
    hdr=lambda:[h.strip().lower() for h in p.locator('#ss-body thead th').all_inner_texts()]
    rows=lambda:[r.split('\t') for r in p.locator('#ss-body tbody tr').all_inner_texts()]
    H=hdr();ok('column headers present',H[3:]==['p','w','d','l','goals','assists','potm','yellow','red','rested','absent'],H)
    M={'played':'p','won':'w','drawn':'d','lost':'l','goals':'goals','assists':'assists','potm':'potm','yellow':'yellow','red':'red','rested':'rested','absent':'absent'}
    def col(name): return H.index(M[name])
    R0=rows()
    names=lambda: [r[1].strip() for r in rows()]
    ok('default: goals→assists→potm (Ayush, Nasiq, Varun first)',names()[:3]==['Ayush','Nasiq','Varun'],names())
    ok('ranks 1,2,3,4 at top',[r[0].strip() for r in rows()[:4]]==['1','2','3','4'],[r[0] for r in rows()[:4]])
    def rec(n): return [r for r in rows() if r[1].strip()==n][0]
    v=rec('Varun');ok('Varun P2 W1 D1 L0 G2',[v[col('played')].strip(),v[col('won')].strip(),v[col('drawn')].strip(),v[col('lost')].strip(),v[col('goals')].strip()]==['2','1','1','0','2'],v)
    y=rec('Ayush');ok('Ayush absent 1, played 1 (absent excluded)',y[col('absent')].strip()=='1' and y[col('played')].strip()=='1',y)
    bl=rec('Bilal Yaser');ok('Bilal rested 1, played 0',bl[col('rested')].strip()=='1' and bl[col('played')].strip()=='0',bl)
    vv=rec('Varun');ok('Varun yellow 1',vv[col('yellow')].strip()=='1',vv)
    # header click re-sorts and renumbers
    p.locator('#ss-body thead th',has_text='Assists').first.click();p.wait_for_timeout(200)
    ok('sort by assists: Ayush/Rishabh first, ranks renumber with shared tie',names()[:2] in (['Ayush','Rishabh Devgon'],['Rishabh Devgon','Ayush']) and [r[0].strip() for r in rows()[:3]][:2]==['1','1'],(names()[:3],[r[0] for r in rows()[:3]]))
    p.locator('#ss-body thead th',has_text='Red').first.click();p.wait_for_timeout(200)
    ok('sort by red cards: Bhagyesh first',names()[0]=='Bhagyesh Rane',names()[:3])
    # filters
    p.select_option('#s-team',T['Desi Steelers FC']);p.wait_for_timeout(200)
    ok('team filter: only Desi squad',set(names())=={'Nasiq','Ayush','Vignesh'},names())
    ok('team filter: ranks restart at 1',rows()[0][0].strip()=='1')
    p.select_option('#s-team','all');p.fill('#s-search','rish');p.wait_for_timeout(200)
    ok('search narrows to Rishabh',names()==['Rishabh Devgon'],names())
    p.fill('#s-search','');p.wait_for_timeout(100)
    opts=p.locator('#s-season option').all_inner_texts()
    ok('season dropdown has season + All seasons (career)',any('Season 1' in o for o in opts) and any('All seasons' in o for o in opts),opts)
    p.select_option('#s-season','all');p.wait_for_timeout(400)
    ok('all seasons: same totals, no errors',not p.errs and rec('Varun')[col('goals')].strip()=='2',p.errs)
    # sub nav
    p.click('#sub-nav button[data-sec=milestones]');p.wait_for_timeout(200)
    ok('Milestones section shows with its tabs',p.is_visible('#sec-milestones') and not p.is_visible('#sec-season') and p.locator('[data-tab]').count()>=6)
    p.click('[data-tab=rested]');ok('Milestones tabs still work',p.locator('#ms-body').inner_text().strip()!='')
    p.click('#sub-nav button[data-sec=season]');ok('back to Season Stats',p.is_visible('#sec-season'))
    mp=Site(pw,d).page('stats.html',1200);mp.set_viewport_size({'width':390,'height':800});mp.wait_for_timeout(300)
    ok('phone: no sideways page scroll',mp.evaluate('document.documentElement.scrollWidth')<=390,mp.evaluate('document.documentElement.scrollWidth'))
    q=Site(pw,finish(base())).page('stats.html',1200);ok('empty season: no errors',not q.errs,q.errs)
print(sum(R),'passed',len(R)-sum(R),'failed')
