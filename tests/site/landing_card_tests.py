# Landing page card: weekly rule (Eastern) switches between Latest Results and Upcoming Matches.
from harness import *; from fixtures import *
serve();R=[];Site.real_week=True
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
def scen(day4=False):
    b=base();m=b['m'];T=b['T'];P=b['P']
    m(1,1,'Muggles FC','Scouts FC','completed',1,2);m(1,2,'Renegades','Desi Steelers FC','completed',0,0)
    m(2,1,'Scouts FC','Muggles FC','completed',2,0);m(2,2,'Desi Steelers FC','Renegades','completed',0,0)
    m(3,1,'Muggles FC','Desi Steelers FC','completed',1,0);m(3,2,'Renegades','Scouts FC','completed',1,0)
    if day4: m(4,1,'Renegades','Scouts FC','completed',0,1);m(4,2,'Muggles FC','Desi Steelers FC','completed',2,2)
    else: m(4,1,'Renegades','Scouts FC');m(4,2,'Muggles FC','Desi Steelers FC')
    d=finish(b)
    def ev(i,mt,t,pl,ty,minute=3,rel=None): return {'id':'v%d'%i,'match_id':mt,'team_id':T[t],'player_id':P[pl],'event_type':ty,'half':1,'minute':minute,'second':None,'related_player_id':P[rel] if rel else None,'is_penalty':False,'created_at':'2026-10-07T01:00:%02d+00:00'%i}
    d['match_events']=[ev(1,'m0','Muggles FC','Amritpal Singh','goal',2),ev(2,'m0','Scouts FC','Bhagyesh Rane','goal',5),ev(3,'m0','Scouts FC','Ajinkya P','assist',5),ev(4,'m0','Scouts FC','Bilal Yaser','goal',9),
      ev(5,'m2','Scouts FC','Bhagyesh Rane','goal',4),ev(6,'m2','Muggles FC','Bilal Yaser','own_goal',8)]
    d['match_appearances']=[{'id':'a1','match_id':'m0','team_id':T['Muggles FC'],'player_id':P['Ayush'],'status':'rested','started':False,'is_captain':False,'captain_stand_in':False,'absent_reason':None}]
    return d,T

with sync_playwright() as pw:
    d,T=scen();s=Site(pw,d)
    def at(site,iso,wait=1200):
        p=site.ctx.new_page();errs=[];p.on('pageerror',lambda e:errs.append(str(e)))
        p.clock.set_fixed_time(iso);p.goto('http://127.0.0.1:8137/index.html');p.wait_for_timeout(wait);p.errs=errs;return p
    title=lambda p:p.locator('#up-title').text_content().strip()
    cases=[('Mon Oct 26 22:00 EDT','2026-10-27T02:00:00Z','Upcoming Matches'),('Tue Oct 27 20:30 EDT','2026-10-28T00:30:00Z','Upcoming Matches'),('Tue Oct 27 20:31 EDT','2026-10-28T00:31:00Z','Latest Results'),
           ('Wed Oct 28 03:12 EDT (the reported bug)','2026-10-28T07:12:00Z','Latest Results'),('Thu Oct 29 23:59 EDT','2026-10-30T03:59:00Z','Latest Results'),('Fri Oct 30 00:00 EDT','2026-10-30T04:00:00Z','Upcoming Matches'),
           ('Sun Nov 1 12:00','2026-11-01T17:00:00Z','Upcoming Matches'),('Tue Nov 3 20:30 EST','2026-11-04T01:30:00Z','Upcoming Matches'),('Tue Nov 3 20:31 EST','2026-11-04T01:31:00Z','Latest Results'),('Thu Nov 5 23:59 EST','2026-11-06T04:59:00Z','Latest Results'),('Fri Nov 6 00:00 EST','2026-11-06T05:00:00Z','Upcoming Matches')]
    for lab,iso,want in cases:
        p=at(s,iso);ok(lab+' -> '+want,title(p)==want and not p.errs,(title(p),p.errs));p.close()
    p=at(s,'2026-10-28T13:00:00Z')
    t=p.inner_text('#upcoming-list')
    ok('results window shows the latest match day (Day 3) with scores','Day 3' in t and '1 – 0' in t and '1 – 0' in t and 'Day 4' not in t,t)
    ok('no Win % bars or note in results mode',p.locator('.up-bar').count()==0 and not p.is_visible('#up-note'))
    ok('each score links to its match page',p.eval_on_selector_all('#upcoming-list a[href^="match.html"]','els=>els.length>=2'))
    p.close()
    p=at(s,'2026-10-30T04:00:00Z');t=p.inner_text('#upcoming-list')
    ok('Friday: upcoming Day 4 rows, with Win % bars','Day 4' in t and p.locator('.up-bar').count()>=1 and 'Day 3' not in t,t)
    p.close()
    # scorers + assists on Day 1? use day with events: m0 is Day 1 -> make Day 1 the latest by scenario with only Day 1 done
    b=base();m=b['m'];T2=b['T'];P2=b['P']
    m(1,1,'Muggles FC','Scouts FC','completed',1,2);m(1,2,'Renegades','Desi Steelers FC');m(2,1,'Scouts FC','Muggles FC');m(2,2,'Desi Steelers FC','Renegades')
    d2=finish(b)
    def ev(i,mt,t,pl,ty,rel=None): return {'id':'v%d'%i,'match_id':mt,'team_id':T2[t],'player_id':P2[pl],'event_type':ty,'half':1,'minute':3,'second':None,'related_player_id':P2[rel] if rel else None,'created_at':'2026-10-07T01:00:%02d+00:00'%i}
    d2['match_events']=[ev(1,'m0','Muggles FC','Amritpal Singh','goal'),ev(2,'m0','Scouts FC','Bhagyesh Rane','goal'),ev(3,'m0','Scouts FC','Ajinkya P','assist','Bhagyesh Rane'),ev(4,'m0','Scouts FC','Bilal Yaser','own_goal')]
    s2=Site(pw,d2);p=at(s2,'2026-10-28T13:00:00Z');t=p.inner_text('#upcoming-list')
    ok('results rows list scorers, assists and own goals','Amritpal Singh' in t and 'Bhagyesh Rane (assist Ajinkya P)' in t and 'Bilal Yaser (OG)' in t,t)
    ok('unplayed matches of that day show "Awaiting result"','Awaiting result' in t,t)
    p.close()
    # fallbacks
    d3,_=scen(day4=True);s3=Site(pw,d3);p=at(s3,'2026-10-26T22:00:00Z')
    ok('nothing left to play -> results even in the upcoming window',title(p)=='Latest Results' and 'Day 4' in p.inner_text('#upcoming-list'),title(p));p.close()
    s4=Site(pw,scenario_pre());p=at(s4,'2026-10-28T13:00:00Z')
    ok('nothing played yet -> upcoming even on Wednesday',title(p)=='Upcoming Matches' and 'Day 1' in p.inner_text('#upcoming-list'),title(p));p.close()
    # live match is ignored by the weekly rule
    d5,_=scen();ms=d5['matches'];lv=[x for x in ms if x['match_day']==4][0];lv['live_phase']='h1';lv['clock_rem']=420;lv['clock_running']=True;lv['clock_at']='2026-10-28T12:59:00+00:00'
    s5=Site(pw,d5);p=at(s5,'2026-10-28T13:00:00Z')
    ok('a live match does not change the card (results window stays results)',title(p)=='Latest Results' and 'LIVE' not in p.inner_text('#upcoming-list'),p.inner_text('#upcoming-list'));p.close()
print('== %d passed, %d failed'%(sum(R),len(R)-sum(R)))
