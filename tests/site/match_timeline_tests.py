from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
m(1,1,'Muggles FC','Scouts FC','completed',1,2);m(1,2,'Renegades','Desi Steelers FC','completed',0,0);m(1,3,'Renegades','Scouts FC','scheduled')
d=finish(b);ev=[]
def e(match,team,pl,typ,rel=None,half=None,minute=None):
    ev.append({'id':'e%02d'%len(ev),'match_id':match,'team_id':T[team],'player_id':P[pl],'event_type':typ,'half':half,'minute':minute,'related_player_id':P[rel] if rel else None,'created_at':'2026-10-07T01:00:%02d+00:00'%len(ev)})
e('m0','Muggles FC','Vignesh','goal',None,1)
e('m0','Scouts FC','Bhagyesh Rane','goal',None,2);e('m0','Scouts FC','Rishabh Devgon','assist',None,2)
e('m0','Scouts FC','Bilal Yaser','goal',None,2);e('m0','Scouts FC','Ayush','assist',None,2)
e('m0','Muggles FC','Amritpal Singh','yellow_card',None,1);e('m0','Scouts FC','Bhagyesh Rane','player_of_match',None,2)
e('m1','Renegades','Varun','yellow_card')
d['match_events']=ev
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('match.html?id=m0',1500)
    t=p.inner_text('#events-list');ok('no JS errors',not p.errs,p.errs)
    ok('First half then Second half sections in order',0<=t.find('FIRST HALF')<t.find('SECOND HALF') or 0<=t.lower().find('first half')<t.lower().find('second half'),t)
    ok('goals carry assists and running score',t.count('Assist:')==2 and 'Muggles FC 1 – 0 Scouts FC' in t and 'Muggles FC 1 – 2 Scouts FC' in t,t)
    ok('half-time and full-time lines','Half-time: Muggles FC 1 – 0 Scouts FC' in t and 'Full-time: Muggles FC 1 – 2 Scouts FC' in t,t)
    ok('yellow card in first half, before the half-time line',t.find('Yellow card')<t.find('Half-time'),t)
    ok('POTM shown',('Player of the Match' in t) and 'Bhagyesh Rane' in t.split('Player of the Match')[-1],t)
    p.screenshot(path='/var/tmp/site/timeline.png',full_page=True)
    q=s.page('match.html?id=m1',1200);tt=q.inner_text('#events-list');ok('events without half go under "Half not recorded"','Half not recorded' in tt.lower() or 'HALF NOT RECORDED' in tt,tt)
    q2=s.page('match.html?id=m2',1200);ok('no events: friendly text','No events logged' in q2.inner_text('#events-list') and not q2.errs)
    mp=Site(pw,d).page('match.html?id=m0',1200);mp.set_viewport_size({'width':390,'height':800});mp.wait_for_timeout(300)
    ok('phone: no sideways scroll',mp.evaluate('document.documentElement.scrollWidth')<=390)
print(sum(R),'passed',len(R)-sum(R),'failed')
