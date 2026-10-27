# Public side of live scoring: match page, Matches page, landing page, and the on/off switch.
import datetime
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
UTC=datetime.timezone.utc
def iso(dt): return dt.astimezone(UTC).isoformat()
def scen(phase='h1',ago=150,rem=600,running=True,at=None):
    b=base();m=b['m'];T=b['T'];P=b['P']
    m(1,1,'Muggles FC','Desi Steelers FC','completed',1,0)          # m0 finished (gives standings something)
    m(1,2,'Scouts FC','Renegades')                                  # m1 = the live one
    m(2,1,'Scouts FC','Desi Steelers FC');m(2,2,'Muggles FC','Renegades')
    d=finish(b)
    now=datetime.datetime.now(UTC)
    mm=d['matches'][1];mm.update({'live_phase':phase,'clock_rem':rem,'clock_running':running,'clock_at':at or iso(now-datetime.timedelta(seconds=ago)),'toss_winner_team_id':T['Scouts FC'],'toss_choice':'kickoff','kickoff_at':iso(now-datetime.timedelta(minutes=3))})
    def ev(i,t,pl,ty,half,rem_,rel=None,pen=False):
        el=(0 if half==1 else 600)+(600-rem_)
        return {'id':'v%d'%i,'match_id':'m1','team_id':T[t],'player_id':P[pl],'event_type':ty,'half':half,'time_remaining':rem_,'minute':el//60,'second':el%60,'related_player_id':P[rel] if rel else None,'is_penalty':pen,'created_at':'2026-10-27T01:00:%02d+00:00'%i}
    d['match_events']=[{'id':'v0','match_id':'m0','team_id':T['Muggles FC'],'player_id':P['Amritpal Singh'],'event_type':'goal','half':1,'minute':3,'second':None,'related_player_id':None,'is_penalty':False,'created_at':'2026-10-06T01:00:00+00:00'},
        ev(1,'Scouts FC','Bhagyesh Rane','goal',1,440,'Ajinkya P'),ev(2,'Scouts FC','Ajinkya P','assist',1,440,'Bhagyesh Rane'),ev(3,'Renegades','Varun','yellow_card',1,300)]
    d['match_appearances']=[{'id':'a1','match_id':'m1','team_id':T['Renegades'],'player_id':P['Rishabh Devgon'],'status':'rested','started':False,'is_captain':False,'captain_stand_in':False,'absent_reason':None},
        {'id':'a2','match_id':'m1','team_id':T['Scouts FC'],'player_id':P['Bhagyesh Rane'],'status':'played','started':True,'is_captain':True,'captain_stand_in':False,'absent_reason':None}]
    return d,T,P
def page(s,path,wait=1200,errs=True):
    p=s.ctx.new_page();p.errs=[];p.on('pageerror',lambda e:p.errs.append(str(e)));p.on('dialog',lambda x:x.accept());p.goto('http://127.0.0.1:8137/'+path);p.wait_for_timeout(wait);return p
def dbx(p,expr): return p.evaluate('()=>'+expr)
with sync_playwright() as pw:
    d,T,P=scen();s=Site(pw,d);p=page(s,'match.html?id=m1')
    hero=p.inner_text('.m-hero')
    ok('match page: LIVE pill (not "SCHEDULED")','LIVE' in p.inner_text('.m-ft') and 'SCHEDULED' not in hero.upper(),p.inner_text('.m-ft'))
    ok('match page: live score 1 – 0',p.inner_text('.m-score .big').replace('\n',' ').strip()=='1 – 0',p.inner_text('.m-score .big'))
    ck=p.inner_text('#live-clock');ok('match page: "1st half · 2:3x" clock (time PLAYED, counts up)',ck.startswith('1st half · 2:') ,ck)
    tl=p.inner_text('.m-wrap');ok('timeline: goal shown at 2:40 played (7:20 left), 1st half, assist named','FIRST HALF' in tl and '2:40' in tl and 'Ajinkya' in tl,tl[:400])
    ok('timeline never shows the remaining time (7:20)','7:20' not in tl)
    ok('toss shown','Toss' in hero and 'kick' in hero.lower())
    ok('who played: rested player listed','RESTED' in tl.upper() and 'Rishabh' in tl,'')
    ok('live stats panel present (goals bar)','Match stats' in tl or 'MATCH STATS' in tl.upper())
    ok('no JS errors (match page live)',not p.errs,p.errs)
    # --- update arrives without reload (poll every 5 s)
    dbx(p,"(window.__DB.match_events.push({id:'v9',match_id:'m1',team_id:'%s',player_id:'%s',event_type:'goal',half:1,time_remaining:200,minute:6,second:40,related_player_id:null,is_penalty:false,created_at:'2026-10-27T01:10:00+00:00'}),1)"%(T['Renegades'],P['Varun']))
    p.wait_for_timeout(6500)
    ok('score updates by itself to 1 – 1 (no reload)',p.inner_text('.m-score .big').replace('\n',' ').strip()=='1 – 1',p.inner_text('.m-score .big'))
    ok('new goal on the timeline at 6:40','6:40' in p.inner_text('.m-wrap'))
    # --- half-time
    dbx(p,"Object.assign(window.__DB.matches[1],{live_phase:'ht',clock_rem:0,clock_running:false,clock_at:new Date().toISOString()})")
    p.wait_for_timeout(6000);ok('half-time shown',p.inner_text('#live-clock')=='Half-time' or 'Half-time' in p.inner_text('.m-score'),p.inner_text('.m-score'))
    # --- second half goal: 4:50 left -> 15:10 played, in the SECOND HALF block
    dbx(p,"(Object.assign(window.__DB.matches[1],{live_phase:'h2',clock_rem:600,clock_running:true,clock_at:new Date(Date.now()-300000).toISOString()}),window.__DB.match_events.push({id:'v10',match_id:'m1',team_id:'%s',player_id:'%s',event_type:'goal',half:2,time_remaining:290,minute:15,second:10,related_player_id:null,is_penalty:false,created_at:'2026-10-27T01:20:00+00:00'}),1)"%(T['Scouts FC'],P['Ajinkya P']))
    p.wait_for_timeout(6000);t=p.inner_text('.m-wrap')
    ok('2nd half goal shows 15:10 under SECOND HALF',('SECOND HALF' in t) and '15:10' in t and t.index('FIRST HALF')<t.index('SECOND HALF'),t[:500])
    ok('score 2 – 1',p.inner_text('.m-score .big').replace('\n',' ').strip()=='2 – 1')
    ok('clock reads 2nd half · 5:0x played (10:00 + 5:00 played)',p.inner_text('#live-clock').startswith('2nd half · 15:0') or p.inner_text('#live-clock').startswith('2nd half · 14:5') or p.inner_text('#live-clock').startswith('2nd half · 15:'),p.inner_text('#live-clock'))
    # --- final
    dbx(p,"Object.assign(window.__DB.matches[1],{status:'completed',live_phase:null,clock_running:false,home_score:2,away_score:1})")
    p.wait_for_timeout(6500)
    ok('after confirm: FULL TIME pill, final score, no live clock','FULL TIME' in p.inner_text('.m-ft') and p.inner_text('.m-score .big').replace('\n',' ').strip()=='2 – 1' and not p.query_selector('#live-clock'),p.inner_text('.m-ft'))
    ok('no JS errors (live transitions)',not p.errs,p.errs);s.br.close()

    # --- the on/off switch
    d,T,P=scen();s=Site(pw,d)
    s.ctx.route('**/js/config.js',lambda r:r.fulfill(body=open('/home/claude/s1fall2026/public/js/config.js').read().replace('LIVE_DESK_ENABLED: true','LIVE_DESK_ENABLED: false'),content_type='application/javascript'))
    p=page(s,'match.html?id=m1');ok('switch off: match page behaves as before (SCHEDULED, vs)','SCHEDULED' in p.inner_text('.m-ft').upper() and not p.query_selector('#live-clock') and 'vs' in p.inner_text('.m-score .big'),p.inner_text('.m-score'))
    p2=page(s,'matches.html');ok('switch off: no LIVE badge on Matches',not p2.query_selector('.pill.live'));p3=page(s,'index.html');ok('switch off: no LIVE tag on landing page',not p3.query_selector('.up-livetag'))
    ok('no JS errors (switch off)',not(p.errs or p2.errs or p3.errs),(p.errs,p2.errs,p3.errs));s.br.close()

    # --- matches page
    d,T,P=scen();s=Site(pw,d);p=page(s,'matches.html')
    ok('Matches: Upcoming tab is first/default while a match is live','Upcoming' in p.locator('#mt-tabs button.on').inner_text(),p.locator('#mt-tabs').inner_text())
    row=p.locator('.match-row',has_text='Scouts FC').first;rt=row.inner_text()
    ok('Matches: LIVE badge, 1 – 0 and phase on the row','LIVE' in rt and '1 – 0' in rt and '1ST HALF' in rt.upper(),rt)
    ok('Matches: "Live now" banner instead of a countdown','LIVE NOW' in p.inner_text('.mt-next').upper(),p.inner_text('.mt-next'))
    ok('Matches: scorer shown on the live row','Bhagyesh' in rt,rt)
    dbx(p,"window.__DB.match_events.push({id:'v9',match_id:'m1',team_id:'%s',player_id:'%s',event_type:'goal',half:1,time_remaining:200,minute:6,second:40,related_player_id:null,is_penalty:false,created_at:'2026-10-27T01:10:00+00:00'})"%(T['Renegades'],P['Varun']))
    p.wait_for_timeout(7500);ok('Matches: score refreshes to 1 – 1 by itself','1 – 1' in p.locator('.match-row',has_text='Scouts FC').first.inner_text(),p.locator('.match-row',has_text='Scouts FC').first.inner_text())
    dbx(p,"Object.assign(window.__DB.matches[1],{status:'completed',live_phase:null,clock_running:false,home_score:1,away_score:1})")
    p.wait_for_timeout(7500)
    ok('Matches: after confirm the match leaves Upcoming (no LIVE badge left)',not p.query_selector('.pill.live'))
    p.click('#mt-tabs button[data-mt-tab=recent]');p.wait_for_timeout(300);rt=p.locator('.match-row',has_text='Renegades').first.inner_text()
    ok('Matches: Recent shows it with the final score and Full time','1 – 1' in rt and 'FULL TIME' in rt.upper(),rt)
    ok('no JS errors (matches)',not p.errs,p.errs);s.br.close()
    # weekly rule is overridden by a live match (Wednesday would normally default to Recent)
    d,T,P=scen(at='2026-10-28T12:57:30+00:00',ago=0);d['matches'][1]['kickoff_at']='2026-10-28T12:57:00+00:00';s=Site(pw,d)
    p=s.ctx.new_page();p.errs=[];p.on('pageerror',lambda e:p.errs.append(str(e)));p.clock.set_fixed_time('2026-10-28T13:00:00Z');p.goto('http://127.0.0.1:8137/matches.html');p.wait_for_timeout(1200)
    ok('Wednesday + live match: Upcoming first (normally Recent)','Upcoming' in p.locator('#mt-tabs button.on').inner_text() and p.locator('#mt-tabs button').first.inner_text().startswith('Upcoming'),p.locator('#mt-tabs').inner_text());s.br.close()

    # --- landing page
    d,T,P=scen();s=Site(pw,d);p=page(s,'index.html',1500)
    up=p.inner_text('#upcoming-list');ok('Landing: LIVE tag + score + phase in Upcoming','LIVE' in up and '1 – 0' in up and '1st half' in up,up)
    st=p.inner_text('#standings-body')
    ok('Landing: standings ignore the live match until confirmed (Muggles 2 pts, Scouts 0 played)','Muggles' in st and '\n2\n' in ('\n'+st.replace('\t','\n')+'\n'),st[:300])
    dbx(p,"Object.assign(window.__DB.matches[1],{status:'completed',live_phase:null,clock_running:false,home_score:1,away_score:0})")
    p.wait_for_timeout(9500);st2=p.inner_text('#standings-body')
    ok('Landing: standings update by themselves once the result is confirmed',st2!=st and 'Scouts' in st2,st2[:300])
    ok('Landing: LIVE tag gone after confirm','LIVE' not in p.inner_text('#upcoming-list').upper().replace('DELIVER',''))
    ok('no JS errors (landing)',not p.errs,p.errs);s.br.close()
print('== %d passed, %d failed'%(sum(R),len(R)-sum(R)))
