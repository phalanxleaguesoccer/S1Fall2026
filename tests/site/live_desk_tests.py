# Live desk (admin/live.html): sign-in, co-admin access, pre-match, clock, events, time conversion, edits, lock, audit, confirm.
import json, time
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
def scen():
    b=base();m=b['m'];T=b['T']
    m(1,1,'Scouts FC','Renegades')   # m0
    m(1,2,'Muggles FC','Desi Steelers FC')
    d=finish(b)
    for team,pre in (('Scouts FC','S'),('Renegades','R')):
        for k in range(8):
            pid='x%s%d'%(pre,k); d['players'].append({'id':pid,'full_name':'%s Player %d'%(pre,k),'age':30,'preferred_position':'Mid','is_active':True,'photo_url':None})
            d['team_season_rosters'].append({'id':'rx'+pid,'season_id':'season1','team_id':T[team],'player_id':pid,'is_owner':False})
    d['__audit']=True; d['__who']='Preet'
    return d,T
def mkpage(s,path='admin/live.html?match=m0',replies=None):
    p=s.ctx.new_page();p.errs=[];p.dlg=[];p.reply=replies or {}
    p.on('pageerror',lambda e:p.errs.append(str(e)))
    def dh(d):
        p.dlg.append((d.type,d.message))
        if d.type=='prompt': d.accept(p.reply.get('prompt','typo, wrong player'))
        else: d.accept()
    p.on('dialog',dh)
    p.goto('http://127.0.0.1:8137/'+path);p.wait_for_timeout(900);return p
def db(p,expr): return p.evaluate('()=>'+expr)
def M(p): return db(p,"window.__DB.matches.find(m=>m.id==='m0')")
def EVS(p): return db(p,"window.__DB.match_events.filter(e=>e.match_id==='m0')")
def pick(p,sel,txt): p.click(sel);p.wait_for_timeout(120)
with sync_playwright() as pw:
    # ---------------- access control ----------------
    d,T=scen();d['__admin']=False
    s=Site(pw,d);p=mkpage(s)
    ok('signed out: sign-in form shown, desk hidden',p.is_visible('#gate') and not p.is_visible('#desk'))
    p.click('#g-up');ok('request-access tab',p.is_visible('#signup-form'))
    p.fill('#su-name','Sunny Co');p.fill('#su-email','sunny@x.com');p.fill('#su-pass','longenough1');p.click('#signup-form button');p.wait_for_timeout(700)
    ok('sign-up without email confirmation: lands on "waiting for approval"',p.is_visible('#pending') and 'WAITING' in p.inner_text('#pending').upper(),p.inner_text('body')[:200])
    co=db(p,"window.__DB.coadmins")
    ok('a pending request row was filed with the name',len(co)==1 and co[0]['status']=='pending' and co[0]['display_name']=='Sunny Co',co)
    db(p,"(window.__DB.coadmins[0].status='revoked',1)");p.click('#pending-refresh');p.wait_for_timeout(500)
    ok('revoked co-admin sees access is off','turned off' in p.inner_text('#pending'))
    db(p,"(window.__DB.coadmins[0].status='approved',1)");p.click('#pending-refresh');p.wait_for_timeout(1200)
    ok('after approval the desk opens as Co-admin','Co-admin' in p.inner_text('#whoami') and p.is_visible('#desk') and p.is_visible('#p-pre'),p.inner_text('#whoami'))
    ok('no JS errors (access flow)',not p.errs,p.errs);s.br.close()
    d,T=scen();d['__admin']=False;d['__confirm_email']=True;s=Site(pw,d);p=mkpage(s);p.click('#g-up')
    p.fill('#su-name','A');p.fill('#su-email','a@x.com');p.fill('#su-pass','longenough1');p.click('#signup-form button');p.wait_for_timeout(500)
    ok('sign-up needing email confirmation: tells the person to confirm and then wait for approval','confirmation' in p.inner_text('#su-msg').lower() and 'approve' in p.inner_text('#su-msg').lower(),p.inner_text('#su-msg'));s.br.close()
    d,T=scen();d['__admin']=False;d['__badlogin']=True;s=Site(pw,d);p=mkpage(s)
    p.fill('#si-email','x@y.com');p.fill('#si-pass','nope');p.click('#signin-form button');p.wait_for_timeout(400)
    ok('wrong password shows an error',('Invalid' in p.inner_text('#si-msg')),p.inner_text('#si-msg'));s.br.close()
    d,T=scen();d['__nolive']=True;s=Site(pw,d,True);p=mkpage(s)
    ok('SQL not run yet: friendly "run the migration" message',p.is_visible('#nodb') and not p.is_visible('#desk'));s.br.close()

    # ---------------- admin runs a whole match ----------------
    d,T=scen();s=Site(pw,d,True);p=mkpage(s)
    ok('admin lands on the desk, pre-match step',p.is_visible('#p-pre') and 'Admin' in p.inner_text('#whoami'),p.inner_text('#whoami'))
    ok('start disabled until toss + choice',p.is_disabled('#btn-start'))
    p.click('#toss-teams button >> nth=0');p.wait_for_timeout(300);p.click('#toss-choice button >> nth=1');p.wait_for_timeout(300)
    mm=M(p);ok('toss saved to the match',mm['toss_winner_team_id']==T['Scouts FC'] and mm['toss_choice']=='kickoff',mm)
    # rested / absent
    p.click('#ros-H [data-act=st][data-s=rested] >> nth=0');p.wait_for_timeout(250)
    p.click('#ros-H [data-act=st][data-s=absent] >> nth=1');p.wait_for_timeout(250)
    p.click('#ros-A [data-act=st][data-s=rested] >> nth=0');p.wait_for_timeout(250)
    ap=db(p,"window.__DB.match_appearances")
    ok('rested + absent saved as lineup rows',sorted(a['status'] for a in ap)==['absent','rested','rested'],ap)
    ok('both statuses have their own buttons (Playing / Rested / Absent)',p.locator('#ros-H .seg').first.inner_text().replace('\n',' ').upper().split()==['PLAYING','RESTED','ABSENT'])
    ok('counts show playing/rested/absent','8 playing · 1 rested · 1 absent'.upper() in p.inner_text('#ros-H').upper() and '9 playing'.upper() in p.inner_text('#ros-A').upper(),p.inner_text('#ros-H')[:80])
    p.select_option('#ros-H select[data-act=cap]',index=2);p.wait_for_timeout(300)
    caps=[a for a in db(p,"window.__DB.match_appearances") if a.get('is_captain')]
    ok('captain saved (one)',len(caps)==1,caps)
    for k in (2,3,4,5,6,7): p.click('#ros-A [data-act=st][data-s=absent] >> nth=%d'%k);p.wait_for_timeout(200)
    ok('too few players blocks kick-off',p.is_disabled('#btn-start') and 'at least 4' in p.inner_text('#pre-chk'),p.inner_text('#pre-chk'))
    for k in (2,3,4,5,6,7): p.click('#ros-A [data-act=st][data-s=played] >> nth=%d'%k);p.wait_for_timeout(150)
    ok('enough players: start enabled',not p.is_disabled('#btn-start'),p.inner_text('#pre-chk'))
    p.click('#btn-start');p.wait_for_timeout(700)
    mm=M(p);ok('kick-off: match is live h1, clock running from 10:00',mm.get('live_phase')=='h1' and mm.get('clock_running') is True and mm.get('clock_rem')==600,mm)
    ok('live pane shown, LIVE pill',p.is_visible('#p-live') and p.is_visible('#lv'))
    p.click('#ros-H') if False else None
    # fake an elapsed 2:00 on the clock (clock_at 120 s ago)
    db(p,"(window.__DB.matches.find(m=>m.id==='m0').clock_at=new Date(Date.now()-300000).toISOString(),1)");p.evaluate("refresh()");p.wait_for_timeout(900)
    clk=p.inner_text('#clk');ok('countdown shows ~05:00 left',clk.startswith('04:5') or clk=='05:00',clk)
    # ---- goal 1: 07:20 left, 1st half -> 2:40 played
    p.click('[data-add="goal|H"]');p.wait_for_timeout(200)
    names=p.locator('#sheet [data-s-player]').all_inner_texts()
    rested=[a for a in db(p,"window.__DB.match_appearances") if a['status']!='played']
    resnames=[next(x['full_name'] for x in db(p,"window.__DB.players") if x['id']==a['player_id']) for a in rested if a['team_id']==T['Scouts FC']]
    ok('rested/absent Scouts players are not in the scorer list',not set(resnames)&set(names),(resnames,names))
    ok('time pre-filled from the clock (~05:00)',p.input_value('#s-rt').startswith('04:5') or p.input_value('#s-rt')=='05:00',p.input_value('#s-rt'))
    p.click('#sheet [data-s-player] >> nth=0');p.wait_for_timeout(150)
    ok('assist step appears; "No assist" present','No assist' in p.inner_text('#sheet'))
    p.click('#sheet [data-s-assist] >> nth=0');p.wait_for_timeout(150)
    p.fill('#s-rt','07:20');p.dispatch_event('#s-rt','input')
    ok('preview: 1st half · 2:40 played','1st half · 2:40' in p.inner_text('#s-conv'),p.inner_text('#s-conv'))
    p.fill('#s-rt','12:00');p.dispatch_event('#s-rt','input');p.click('#s-save');p.wait_for_timeout(300)
    ok('12:00 is blocked with a message and nothing is saved',len(EVS(p))==0 and p.is_visible('#sheet') and ('Fix the time' in p.inner_text('#s-err')),p.inner_text('#s-err'))
    p.fill('#s-rt','7:2');p.dispatch_event('#s-rt','input');ok('malformed 7:2 flagged','between 00:00 and 10:00' in p.inner_text('#s-conv'))
    p.fill('#s-rt','03:00');p.dispatch_event('#s-rt','input');p.click('#s-save');p.wait_for_timeout(300)
    ok('a time that has not happened yet is blocked','not happened yet' in p.inner_text('#s-err') and len(EVS(p))==0,p.inner_text('#s-err'))
    p.fill('#s-rt','07:20');p.dispatch_event('#s-rt','input');p.click('#s-save');p.wait_for_timeout(700)
    ev=EVS(p);g=[e for e in ev if e['event_type']=='goal'];a=[e for e in ev if e['event_type']=='assist']
    ok('goal + linked assist saved atomically',len(g)==1 and len(a)==1 and g[0]['related_player_id']==a[0]['player_id'] and a[0]['related_player_id']==g[0]['player_id'],ev)
    ok('every saved event row has is_penalty set (false, never null) - bulk-insert regression',all(e.get('is_penalty') is False for e in ev),[(e['event_type'],e.get('is_penalty')) for e in ev])
    ok('stored half 1, time_remaining 440, minute 2 second 40',g[0]['half']==1 and g[0]['time_remaining']==440 and g[0]['minute']==2 and g[0]['second']==40,g[0])
    ok('scoreboard 1–0',p.inner_text('#hs')=='1' and p.inner_text('#as')=='0')
    tl=p.inner_text('#tl-live');ok('timeline shows 2:40 with 1H tag and running score','2:40' in tl and '1H' in tl and '1–0' in tl and 'FIRST HALF' in tl.upper(),tl)
    # ---- red card removes player from later pickers
    p.click('[data-add="red_card|?"]');p.click('#sheet [data-s-team] >> nth=1');p.wait_for_timeout(150);red_name=p.locator('#sheet [data-s-player]').first.inner_text()
    p.click('#sheet [data-s-player] >> nth=0');p.click('#s-save');p.wait_for_timeout(600)
    p.click('[data-add="foul|?"]');p.click('#sheet [data-s-team] >> nth=1');p.wait_for_timeout(150)
    ok('red-carded player is not offered again',red_name not in p.locator('#sheet [data-s-player]').all_inner_texts());p.click('[data-s-cancel]')
    # ---- second yellow = automatic red
    for k in range(2):
        p.click('[data-add="yellow_card|?"]');p.click('#sheet [data-s-team] >> nth=0');p.wait_for_timeout(150)
        yname=p.locator('#sheet [data-s-player]').first.inner_text();p.click('#sheet [data-s-player] >> nth=0')
        p.fill('#s-rt','0%d:00'%(9-k));p.dispatch_event('#s-rt','input');p.click('#s-save');p.wait_for_timeout(600)
        if k==0: ok('first yellow adds no red',len([e for e in EVS(p) if e['event_type']=='yellow_card'])==1 and len([e for e in EVS(p) if e['event_type']=='red_card'])==1,[e['event_type'] for e in EVS(p)])
    ev2=EVS(p);yc=[e for e in ev2 if e['event_type']=='yellow_card'];rc=[e for e in ev2 if e['event_type']=='red_card']
    ok('second yellow to the same player adds an automatic red card',len(yc)==2 and len(rc)==2 and rc[-1]['player_id']==yc[0]['player_id'] and yc[0]['player_id']==yc[1]['player_id'],[(e['event_type'],e['player_id']) for e in ev2])
    ok('automatic red row also has is_penalty false',all(e.get('is_penalty') is False for e in ev2),[(e['event_type'],e.get('is_penalty')) for e in ev2])
    # ---- own goal: Scouts get the goal, an AWAY player is the offender
    p.click('[data-add="goal|H"]');p.check('[data-s-og]');p.wait_for_timeout(150)
    opts=p.locator('#sheet [data-s-player]').all_inner_texts();ok('own goal lists the OTHER team\'s players',not any(o.startswith('S Player') or o in('Bhagyesh Rane','Ajinkya P') for o in opts) and len(opts)>=4,opts)
    p.click('#sheet [data-s-player] >> nth=1');p.fill('#s-rt','06:00');p.dispatch_event('#s-rt','input');p.click('#s-save');p.wait_for_timeout(600)
    og=[e for e in EVS(p) if e['event_type']=='own_goal'];ok('own goal stored on the offender\'s team',len(og)==1 and og[0]['team_id']==T['Renegades'],og)
    ok('score 2–0 (own goal counts for Scouts)',p.inner_text('#hs')=='2' and p.inner_text('#as')=='0',(p.inner_text('#hs'),p.inner_text('#as')))
    # ---- edit goal time
    p.locator('#tl-live [data-act=edit]').nth(0).click();p.wait_for_timeout(200)
    p.fill('#s-rt','05:30');p.dispatch_event('#s-rt','input');p.click('#s-save');p.wait_for_timeout(600)
    ok('edit saved (time_remaining changed)',any(e['time_remaining']==330 for e in EVS(p)),[e['time_remaining'] for e in EVS(p)])
    # ---- remove with required reason
    n0=len(EVS(p));p.reply['prompt']='';p.locator('#tl-live [data-act=rm]').nth(0).click();p.wait_for_timeout(500)
    ok('removing without a reason does nothing',len(EVS(p))==n0)
    p.reply['prompt']='entered against wrong team';p.locator('#tl-live [data-act=rm]').nth(0).click();p.wait_for_timeout(700)
    ok('removing with a reason deletes it',len(EVS(p))==n0-1,len(EVS(p)))
    notes=[a for a in db(p,"window.__DB.audit_log") if a['table_name']=='live_note']
    ok('reason is stored as a note',any('entered against wrong team' in (a['new_data'] or {}).get('note','') for a in notes),notes)
    # ---- pause / resume
    p.click('#btn-pause');p.wait_for_timeout(500);ok('pause: clock stopped in DB',M(p)['clock_running'] is False and 'Resume' in p.inner_text('#btn-pause'))
    p.click('#btn-pause');p.wait_for_timeout(500);ok('resume: clock running',M(p)['clock_running'] is True)
    # ---- end half early, half-time
    p.click('#btn-endhalf');p.wait_for_timeout(700)
    ok('half-time pane + live_phase ht',p.is_visible('#p-ht') and M(p)['live_phase']=='ht')
    ok('early end noted in the audit trail',any('ended early' in (a['new_data'] or {}).get('note','') for a in db(p,"window.__DB.audit_log") if a['table_name']=='live_note'))
    # late first-half entry at half-time
    p.click('#ht-gA');p.wait_for_timeout(200)
    ok('at half-time only the 1st half is offered',not p.is_visible('[data-s-half]'))
    p.click('#sheet [data-s-player] >> nth=0');p.click('#sheet [data-s-assist=""]');p.fill('#s-rt','09:00');p.dispatch_event('#s-rt','input');p.click('#s-save');p.wait_for_timeout(700)
    ok('half-time entry stored as 1st half (0–? score updates)',p.inner_text('#hta')=='1',p.inner_text('#hta'))
    # ---- second half
    p.click('#btn-start2');p.wait_for_timeout(700);ok('second half live',M(p)['live_phase']=='h2' and M(p)['clock_rem']==600)
    db(p,"(window.__DB.matches.find(m=>m.id==='m0').clock_at=new Date(Date.now()-360000).toISOString(),1)");p.evaluate("refresh()");p.wait_for_timeout(900)
    p.click('[data-add="goal|A"]');p.wait_for_timeout(150)
    ok('2nd half: half switch offers 1st or 2nd (default 2nd)',p.is_visible('[data-s-half="1"]') and 'sel' in (p.get_attribute('[data-s-half="2"]','class') or ''))
    p.click('#sheet [data-s-player] >> nth=2');p.click('#sheet [data-s-assist] >> nth=0');p.fill('#s-rt','04:50');p.dispatch_event('#s-rt','input')
    ok('preview: 2nd half · 15:10 (10:00 + 5:10)','2nd half · 15:10' in p.inner_text('#s-conv') and '10:00 + 5:10' in p.inner_text('#s-conv'),p.inner_text('#s-conv'))
    p.click('#s-save');p.wait_for_timeout(700)
    g2=[e for e in EVS(p) if e['half']==2 and e['event_type']=='goal'];ok('2nd-half goal stored as half 2, minute 15 second 10',len(g2)==1 and g2[0]['minute']==15 and g2[0]['second']==10,g2)
    tl=p.inner_text('#tl-live');ok('timeline: SECOND HALF banner above FIRST HALF with HALF-TIME divider','SECOND HALF' in tl.upper() and tl.upper().index('SECOND HALF')<tl.upper().index('FIRST HALF') and 'HALF-TIME' in tl.upper() and '15:10' in tl and '2H' in tl,tl)
    # late first-half entry during 2nd half
    p.click('[data-add="goal|H"]');p.click('[data-s-half="1"]');p.wait_for_timeout(150)
    ok('switching to 1st half leaves time blank-able and shows 1st half label','1st half' in p.inner_text('#sheet'))
    p.click('#sheet [data-s-player] >> nth=0');p.click('#sheet [data-s-assist=""]');p.fill('#s-rt','02:00');p.dispatch_event('#s-rt','input');p.click('#s-save');p.wait_for_timeout(700)
    ok('late first-half entry accepted and flagged in the audit trail',any('Late entry' in (a['new_data'] or {}).get('note','') for a in db(p,"window.__DB.audit_log") if a['table_name']=='live_note'))
    p.click('#btn-endhalf');p.wait_for_timeout(700)
    ok('full-time pane',p.is_visible('#p-ft') and M(p)['live_phase']=='ft')
    ok('final score preview 4–3? (computed from events)',p.inner_text('#fh').isdigit() and p.inner_text('#fa').isdigit())
    fh,fa=int(p.inner_text('#fh')),int(p.inner_text('#fa'))
    p.select_option('#potm',index=1);p.click('#btn-confirm');p.wait_for_timeout(900)
    mm=M(p);ok('confirmed: status completed, live_phase cleared, scores from events',mm['status']=='completed' and mm['live_phase'] is None and mm['home_score']==fh and mm['away_score']==fa,mm)
    ok('POTM event saved',len([e for e in EVS(p) if e['event_type']=='player_of_match'])==1)
    ok('final pane shown, result locked message','final'.upper() in p.inner_text('#p-final').upper() and p.is_visible('#p-final') and 'admin' in p.inner_text('#p-final').lower())
    st=db(p,"window.__DB.matches.filter(m=>m.status==='completed').length");ok('match counted as completed (standings pick it up)',st==1)
    # ---- audit tab
    p.click('#t-audit');p.wait_for_timeout(800);at=p.inner_text('#audit-body')
    ok('audit lists who (Preet)','Preet' in at)
    ok('audit times are Eastern (EDT/EST)','EDT' in at or 'EST' in at,at[:150])
    ok('audit has ADDED / REMOVED / EDITED / toss / half / result lines',all(k in at for k in ['ADDED','REMOVED','EDITED','Toss won by','FIRST HALF started','SECOND HALF started','RESULT CONFIRMED']),at[:600])
    ok('audit includes the typed removal reason','entered against wrong team' in at)
    ok('lineup changes logged ("set to rested")','set to rested' in at and 'set to absent' in at)
    ok('no JS errors (full match)',not p.errs,p.errs)
    # ---- visitor view while on a 'finished' match is the existing page (smoke)
    s.br.close()

    # ---------------- edit lock ----------------
    d,T=scen();d['live_locks']=[{'match_id':'m0','user_id':'someone-else','label':'Sunny (co-admin)','beat_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}]
    s=Site(pw,d,True);p=mkpage(s,'admin/live.html?match=m0')
    ok('someone else is scoring: banner names them',p.is_visible('#lockbar .lock') and 'Sunny' in p.inner_text('#lockbar'),p.inner_text('#lockbar'))
    ok('start is disabled while locked by someone else',p.is_disabled('#btn-start'))
    p.click('#toss-teams button >> nth=0');p.wait_for_timeout(400);ok('edits refused while locked',M(p).get('toss_winner_team_id') is None)
    p.click('[data-act=takeover]');p.wait_for_timeout(600)
    lk=db(p,"window.__DB.live_locks");ok('take over: lock now belongs to me',lk[0]['user_id']=='admin-1',lk)
    p.click('#toss-teams button >> nth=0');p.wait_for_timeout(500);ok('after take over edits work',M(p).get('toss_winner_team_id')==T['Scouts FC'])
    ok('no JS errors (lock)',not p.errs,p.errs);s.br.close()
    d,T=scen();d['live_locks']=[{'match_id':'m0','user_id':'someone-else','label':'Old','beat_at':'2020-01-01T00:00:00Z'}]
    s=Site(pw,d,True);p=mkpage(s);ok('a stale lock (no heartbeat) does not block',not p.is_visible('#lockbar .lock'));s.br.close()

    # ---------------- phone layout ----------------
    d,T=scen();s=Site(pw,d,True);p=s.ctx.new_page();p.set_viewport_size({'width':375,'height':800});p.errs=[]
    p.on('pageerror',lambda e:p.errs.append(str(e)));p.on('dialog',lambda x:x.accept());p.goto('http://127.0.0.1:8137/admin/live.html?match=m0');p.wait_for_timeout(1000)
    ok('375px: no horizontal scroll (pre-match)',p.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'),p.evaluate('document.documentElement.scrollWidth'))
    p.click('#toss-teams button >> nth=0');p.wait_for_timeout(300);p.click('#toss-choice button >> nth=0');p.wait_for_timeout(300);p.click('#btn-start');p.wait_for_timeout(600)
    p.click('[data-add="goal|H"]');p.wait_for_timeout(200);p.click('#sheet [data-s-player] >> nth=0');p.wait_for_timeout(100)
    ok('375px: no horizontal scroll (event sheet)',p.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'))
    ok('no JS errors (phone)',not p.errs,p.errs);s.br.close()
print('== %d passed, %d failed'%(sum(R),len(R)-sum(R)))
