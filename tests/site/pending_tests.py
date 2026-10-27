# Score-only matches ("details pending") and automatic refresh when a match ends / details are added later.
import json
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
m(1,1,'Muggles FC','Desi Steelers FC','completed',2,0)     # m0: full lineup + goals
m(1,2,'Renegades','Scouts FC','completed',1,0)             # m1: score only, details pending
m(2,1,'Scouts FC','Muggles FC')                            # m2: still to play
d=finish(b);ap=[]
def a(mt,team,pl,st): ap.append({'id':'a%02d'%len(ap),'match_id':mt,'team_id':T[team],'player_id':P[pl],'status':st,'started':st=='played'})
a('m0','Muggles FC','Amritpal Singh','played');a('m0','Muggles FC','Bilal Yaser','rested');a('m0','Desi Steelers FC','Nasiq','played');a('m0','Desi Steelers FC','Ayush','played')
d['match_appearances']=ap
d['match_events']=[{'id':'e0','match_id':'m0','team_id':T['Muggles FC'],'player_id':P['Amritpal Singh'],'event_type':'goal','half':1,'minute':3,'related_player_id':None,'created_at':'2026-10-07T01:00:00+00:00'}]
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('match.html?id=m1',1200)
    t=p.inner_text('#match-root')
    ok('score-only match page shows the final score and "Details pending"','DETAILS PENDING' in t.upper() and p.locator('#details-pending').count()==1 and '1' in p.inner_text('.m-score'),t[:300])
    p2=s.page('match.html?id=m0',1200)
    ok('match with a lineup has no pending note',p2.locator('#details-pending').count()==0)
    p3=s.page('stats.html#season',1500)
    rows=lambda:[r.split('\t') for r in p3.locator('#ss-body tbody tr').all_inner_texts()]
    H=[h.strip().lower() for h in p3.locator('#ss-body thead th').all_inner_texts()]
    byname={r[1].strip():r for r in rows()}
    pc=H.index('p')
    ok('players of the score-only match have 0 played (Varun, Bhagyesh)',byname['Varun'][pc].strip()=='0' and byname['Bhagyesh Rane'][pc].strip()=='0',(byname.get('Varun'),byname.get('Bhagyesh Rane')))
    ok('players with a lineup count (Amritpal 1 played, Nasiq 1)',byname['Amritpal Singh'][pc].strip()=='1' and byname['Nasiq'][pc].strip()=='1',byname['Amritpal Singh'])
    ok('no JS errors',not p3.errs and not p.errs,(p3.errs,p.errs))
    # ---- details added later: page refreshes by itself (no reload) within ~12 s
    p3.evaluate("""()=>{const D=window.__DB;
      D.match_appearances.push({id:'zz1',match_id:'m1',team_id:D._ids.T['Renegades'],player_id:D._ids.P['Varun'],status:'played',started:true});
      D.match_appearances.push({id:'zz2',match_id:'m1',team_id:D._ids.T['Scouts FC'],player_id:D._ids.P['Bhagyesh Rane'],status:'played',started:true});}""")
    p3.wait_for_timeout(16000)
    byname={r[1].strip():r for r in rows()}
    ok('lineup added later: Varun now 1 played, 1 won, without reloading the page',byname['Varun'][pc].strip()=='1' and byname['Varun'][H.index('w')].strip()=='1',byname['Varun'])
    # ---- a match ends: standings on the landing page update by themselves
    h=s.page('index.html',1500)
    before=h.inner_text('body')
    h.evaluate("()=>{const mm=window.__DB.matches.find(x=>x.id==='m2');mm.status='completed';mm.home_score=3;mm.away_score=1;}")
    h.wait_for_timeout(16000)
    after=h.inner_text('body')
    ok('landing page refreshed by itself after a match was completed',before!=after,'unchanged')
    ok('no JS errors on landing',not h.errs,h.errs)
print('==',sum(R),'passed,',len(R)-sum(R),'failed')
