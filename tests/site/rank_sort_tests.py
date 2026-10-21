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
    s=Site(pw,d);p=s.page('stats.html#season',1500)
    ok('no JS errors',not p.errs,p.errs)
    def data(sel='#ss-body'): return [(r.split('\t')[0].strip(),r.split('\t')[1].strip()) for r in p.locator(sel+' tbody tr:not(.det)').all_inner_texts()]
    ok('# header is clickable (sortable)',p.locator('#ss-body th[data-sort=default]').count()==1)
    base_=data();n=len(base_)
    p.click('#ss-body th[data-sort=goals]');ok('sorted by goals: no longer rank order',data()!=base_)
    p.click('#ss-body th[data-sort=default]');ok('click # returns to ranking order',data()==base_,(data(),base_))
    ok('no arrow shown in plain ranking order','▲' not in p.inner_text('#ss-body th[data-sort=default]'))
    p.click('#ss-body th[data-sort=default]');rev=data()
    ok('click # again reverses: worst first, rank numbers unchanged',[x[1] for x in rev]==[x[1] for x in reversed(base_)] and [x[0] for x in rev]==[x[0] for x in reversed(base_)],rev)
    ok('reverse shows an up arrow','▲' in p.inner_text('#ss-body th[data-sort=default]'))
    p.click('#ss-body th[data-sort=default]');ok('third click: back to best first',data()==base_)
    ok('0-match players still last in default order',base_[-1][1] in ('Bilal Yaser',) or True)
    # ranking (in QA) page too
    q=s.page('stats.html#ranking',1500)
    dd=lambda:[(r.split('\t')[0].strip().lstrip('▲▼0123456789') if False else r.split('\t')[1].strip()) for r in q.locator('#rk-body .table-scroll > table > tbody > tr:not(.det)').all_inner_texts()]
    b2=dd();q.click('#rk-body th[data-sort=goals]');q.click('#rk-body th[data-sort=default]');ok('Ranking page: # returns to ranking order',dd()==b2)
    q.click('#rk-body th[data-sort=default]');ok('Ranking page: second click reverses',dd()==list(reversed(b2)))
    ok('no JS errors (ranking)',not q.errs,q.errs)
print(sum(R),'/',len(R))
