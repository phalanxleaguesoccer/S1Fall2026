# One-week transfer ("loan"): Vivek is a Renegades player who played Day 4 for Desi Steelers.
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
b['players'].append({'id':'pViv','full_name':'Vivek','age':36,'preferred_position':'Flex','is_active':True,'photo_url':None})
b['rosters'].append({'id':'rViv','season_id':'season1','team_id':T['Renegades'],'player_id':'pViv','is_owner':False})
m(1,1,'Renegades','Desi Steelers FC','completed',1,0)      # m0 Day 1: Vivek played for Renegades
m(4,1,'Scouts FC','Renegades','completed',3,0)             # m1 Day 4: Vivek did not play (transferred)
m(4,2,'Muggles FC','Desi Steelers FC','completed',3,1)     # m2 Day 4: Vivek plays for Desi
m(4,3,'Desi Steelers FC','Renegades','completed',0,1)      # m3 Day 4: Vivek plays for Desi (own goal)
d=finish(b);ap=[]
def a(mt,team,pl,st='played'): ap.append({'id':'a%02d'%len(ap),'match_id':mt,'team_id':T[team] if team in T else team,'player_id':pl if pl=='pViv' else P[pl],'status':st,'started':st=='played'})
a('m0','Renegades','pViv');a('m0','Renegades','Varun');a('m0','Desi Steelers FC','Nasiq')
a('m1','Renegades','Varun');a('m1','Scouts FC','Bhagyesh Rane')          # no row for Vivek: his team has a lineup but he is not counted absent
a('m2','Desi Steelers FC','pViv');a('m2','Desi Steelers FC','Nasiq');a('m2','Muggles FC','Amritpal Singh')
a('m3','Desi Steelers FC','pViv');a('m3','Desi Steelers FC','Nasiq');a('m3','Renegades','Varun')
d['match_appearances']=ap
d['match_events']=[{'id':'e0','match_id':'m3','team_id':T['Desi Steelers FC'],'player_id':'pViv','event_type':'own_goal','half':1,'minute':3,'related_player_id':None,'is_penalty':False,'created_at':'2026-10-28T01:00:00+00:00'}]
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#season',1800)
    rows=lambda:[r.split('\t') for r in p.locator('#ss-body tbody tr').all_inner_texts()]
    H=[h.strip().lower() for h in p.locator('#ss-body thead th').all_inner_texts()]
    by={r[1].strip():r for r in rows()}
    v=by.get('Vivek');ok('Season Stats: Vivek listed once with both teams',v is not None and 'Desi Steelers FC' in v[2] and 'Renegades' in v[2] and sum(1 for r in rows() if r[1].strip()=='Vivek')==1,v)
    ok('Vivek: 3 played (Day 1 for Renegades + 2 for Desi), 0 absent, 1 own goal',v[H.index('p')].strip()=='3' and v[H.index('absent')].strip()=='0' and v[H.index('og')].strip()=='1',(H,v))
    ok('Vivek: W/D/L = Renegades won Day 1; Desi lost M2, lost M3',v[H.index('w')].strip()=='1' and v[H.index('l')].strip()=='2',v)
    ok('no JS errors on stats',not p.errs,p.errs)
    p.click('[data-sec=milestones]');p.wait_for_timeout(400);p.click('[data-tab=availability]');p.wait_for_timeout(500)
    t=p.inner_text('#ms-body')
    ok('Availability: the skipped Renegades Day 4 match is not an absence for Vivek','Vivek' not in t.split('Rested and absent')[-1] if 'Rested and absent' in t else True,t[:400])
    pl=s.page('player.html?id=pViv',1800);tx=pl.inner_text('body')
    ok('profile: plays for Renegades, also played for Desi Steelers this season','Renegades' in tx and 'Also played for' in tx and 'Desi Steelers FC' in tx,tx[:500])
    ok('profile: season totals add up (3 games)',pl.locator('#stats-body td').all_inner_texts()[:1]==['3'] or '3' in pl.locator('#stats-body').inner_text(),pl.locator('#stats-body').inner_text())
    ok('no JS errors on profile',not pl.errs,pl.errs)
    tm=s.page('team.html?id='+T['Desi Steelers FC'],1800);tt=tm.inner_text('#roster-grid')
    ok('Desi squad shows Vivek as transferred in','Vivek' in tt and 'Transferred in' in tt,tt[:400])
    tr=s.page('team.html?id='+T['Renegades'],1800)
    ok('Renegades squad still lists Vivek (his roster team)','Vivek' in tr.inner_text('#roster-grid'))
    mt=s.page('match.html?id=m2',1800);ok('Day 4 match page lists Vivek under Desi Steelers lineup','Vivek' in mt.inner_text('#match-root'))
    rc=s.page('stats.html#records',2200);rc.wait_for_timeout(800)
    ok('Records page loads without errors',not rc.errs,rc.errs)
    vv=rc.evaluate("(()=>{const o=REC.data.players.find(x=>x.id==='pViv');return o&&{p:o.played,a:o.absent,w:o.won,l:o.lost,og:o.og,team:o.team_id}})()")
    ok('Records engine: Vivek 3 played, 0 absent, home team stays Renegades',vv and vv['p']==3 and vv['a']==0 and vv['w']==1 and vv['l']==2 and vv['og']==1 and vv['team']==T['Renegades'],vv)
print('==',sum(R),'passed,',len(R)-sum(R),'failed')
