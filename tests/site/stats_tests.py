from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
m(1,1,'Muggles FC','Desi Steelers FC','completed',0,0);m(1,2,'Renegades','Scouts FC','completed',0,0)
m(1,3,'Renegades','Desi Steelers FC','completed',0,0);m(1,4,'Muggles FC','Scouts FC','completed',1,2)
m(2,1,'Desi Steelers FC','Renegades','completed',1,0);m(2,2,'Team A','Team B')
d=finish(b);ev=[]
def e(match,team,pl,typ,rel=None,half=None,minute=None,k=None):
    ev.append({'id':'e%02d'%len(ev),'match_id':match,'team_id':T[team],'player_id':P[pl],'event_type':typ,'half':half,'minute':minute,'related_player_id':P[rel] if rel else None,'created_at':'2026-10-07T01:00:%02d+00:00'%len(ev)})
# Day 1 / match 4 entered in order Vishnu(Vignesh), Bhagyesh(Ajinkya), Bilal; ids deliberately not alphabetical in time order
e('m3','Muggles FC','Vignesh','goal');e('m3','Scouts FC','Ajinkya P','goal','Rishabh Devgon');e('m3','Scouts FC','Rishabh Devgon','assist')
e('m3','Scouts FC','Bilal Yaser','goal','Ayush');e('m3','Scouts FC','Ayush','assist')
e('m2','Renegades','Varun','yellow_card');e('m3','Scouts FC','Ayush','red_card',None,2,14)
e('m4','Desi Steelers FC','Nasiq','goal',None,1,4)   # tournament goal #4 but Desi's #1
d['match_events']=ev
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#milestones',1500)
    ok('no JS errors',not p.errs,p.errs)
    ok('Stats link in nav',p.locator('nav.main-nav a',has_text='Stats').count()==1)
    rows=lambda:[r.replace('\t',' | ') for r in p.locator('#ms-body tbody tr:not(.det)').all_inner_texts()]
    ok('goals tournament order = entry order, with team',[r.split(' | ')[:3] for r in rows()]==[['1','Vignesh','Muggles FC'],['2','Ajinkya P','Scouts FC'],['3','Bilal Yaser','Scouts FC'],['4','Nasiq','Desi Steelers FC']],rows())
    ok('view dropdown: Tournament default + only real teams',p.locator('#f-view option').all_inner_texts()==['Tournament / Season (default)','Desi Steelers FC','Muggles FC','Renegades','Scouts FC'],p.locator('#f-view option').all_inner_texts())
    ok('season dropdown default = current season',p.locator('#f-season option:checked').inner_text()=='Season 1 Fall 2026')
    p.select_option('#f-view',T['Scouts FC']);ok('Scouts view: Ajinkya 1st, Bilal 2nd',[r.split(' | ')[:2] for r in rows()]==[['1','Ajinkya P'],['2','Bilal Yaser']],rows())
    p.select_option('#f-view',T['Desi Steelers FC']);ok('Desi view: Nasiq is team goal #1 (tournament #4)',[r.split(' | ')[:2] for r in rows()]==[['1','Nasiq']],rows())
    p.locator('[data-det]').first.click();det=p.inner_text('tr.det:visible')
    ok('details: season, match, opponent, score, half, ordinals',all(x in det for x in ['Season 1 Fall 2026','Day 2','Opponent','Renegades','Desi Steelers FC 1 – 0 Renegades','First half','4'+"'",'4th','1st']),det)
    p.select_option('#f-view','all');p.locator('[data-det]').nth(1).click();det=p.inner_text('tr.det:visible')
    ok('details of 2nd goal: assist by Rishabh, half not recorded, final score 1-2, tournament 2nd / team 1st',all(x in det for x in ['Rishabh Devgon','Not recorded','Muggles FC 1 – 2 Scouts FC','2nd','1st','Muggles FC']),det)
    p.click('[data-tab=assists]');ok('assists tab order',[r.split(' | ')[:3] for r in rows()]==[['1','Rishabh Devgon','Scouts FC'],['2','Ayush','Scouts FC']],rows())
    p.locator('[data-det]').first.click();ok('assist details: goal scored by Ajinkya','Ajinkya P' in p.inner_text('tr.det:visible'),p.inner_text('tr.det:visible'))
    p.click('[data-tab=yellow]');ok('yellow tab: Varun / Renegades',[r.split(' | ')[:3] for r in rows()]==[['1','Varun','Renegades']],rows())
    p.click('[data-tab=red]');ok('red tab: Ayush with second half 14th minute',[r.split(' | ')[:3] for r in rows()]==[['1','Ayush','Scouts FC']],rows())
    p.locator('[data-det]').first.click();ok('red details: Second half + minute',all(x in p.inner_text('tr.det:visible') for x in ['Second half',"14'"]),p.inner_text('tr.det:visible'))
    p.select_option('#f-view',T['Muggles FC']);ok('red tab, team with none: empty message','No red cards' in p.inner_text('#ms-body'),p.inner_text('#ms-body'))
    # empty season
    d2=scenario_pre();q=Site(pw,d2).page('stats.html#milestones',1200);ok('no events: friendly empty text, no errors','No goals recorded yet' in q.inner_text('#ms-body') and not q.errs,(q.inner_text('#ms-body'),q.errs))
    # mobile
    mm=Site(pw,d);mp=mm.page('stats.html#milestones',1200);mp.set_viewport_size({'width':390,'height':800});mp.wait_for_timeout(300)
    ok('phone width: no sideways page scroll',mp.evaluate('document.documentElement.scrollWidth')<=390,mp.evaluate('document.documentElement.scrollWidth'))
print(sum(R),'passed',len(R)-sum(R),'failed')
