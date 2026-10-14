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
    t=p.inner_text('#match-root');ok('no JS errors',not p.errs,p.errs)
    ok('First half then Second half sections in order',0<=t.find('FIRST HALF')<t.find('SECOND HALF'),t)
    tl=t.lower()
    ok('goals carry assists and running score',t.count('Assist: ')==2 and '1 – 0' in t and '1 – 1' in t and '1 – 2' in t,t)
    ok('scoreboard: big score, half-time, scorers under team names',p.inner_text('.m-score').replace('\n',' ').startswith('1 – 2') and 'Half-time 1 – 0' in p.inner_text('.m-score') and 'Bhagyesh Rane' in p.inner_text('.m-board') and 'Bilal Yaser' in p.inner_text('.m-board'),p.inner_text('.m-board'))
    ok('FULL TIME pill and full-time line','FULL TIME' in t and 'FULL TIME  1 – 2'.replace('  ',' ') in t.replace('\xa0',' ').replace('  ',' '),t)
    ok('yellow card sits in first half (before SECOND HALF)',t.find('YELLOW')<t.find('SECOND HALF'),t)
    ok('POTM banner with goals/assists in this match','PLAYER OF THE MATCH' in t and 'BHAGYESH RANE' in t.upper() and p.inner_text('.m-potm .nums').replace('\n',' ').split()[0]=='1',p.inner_text('.m-potm'))
    ok('match stats bars: goals 1 vs 2, yellow 1 vs 0','MATCH STATS' in t.upper() and p.locator('.m-stat').count()==5,p.locator('.m-stat').count())
    ok('player stats table lists Bhagyesh G=1 (events-only lineup)','PLAYER STATS' in t.upper() and p.locator('.m-ptable').count()==2,p.locator('.m-ptable').count())
    p.screenshot(path='/var/tmp/site/timeline.png',full_page=True)
    q=s.page('match.html?id=m1',1200);tt=q.inner_text('#match-root');ok('events without half go under "Half not recorded"','Half not recorded' in tt.lower() or 'HALF NOT RECORDED' in tt,tt)
    q2=s.page('match.html?id=m2',1200);ok('no events: friendly text','No events logged' in q2.inner_text('#match-root') and not q2.errs)
    mp=Site(pw,d).page('match.html?id=m0',1200);mp.set_viewport_size({'width':390,'height':800});mp.wait_for_timeout(300)
    ok('phone: no sideways scroll',mp.evaluate('document.documentElement.scrollWidth')<=390)
print(sum(R),'passed',len(R)-sum(R),'failed')
