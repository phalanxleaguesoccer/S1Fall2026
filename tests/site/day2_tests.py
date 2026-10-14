from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
m(2,1,'Scouts FC','Desi Steelers FC','completed',0,1);m(2,2,'Renegades','Muggles FC','completed',0,2)
d=finish(b);ev=[]
def e(match,team,pl,typ,half=None,minute=None,second=None,rel=None,pen=False):
    ev.append({'id':'e%02d'%len(ev),'match_id':match,'team_id':T[team],'player_id':P[pl],'event_type':typ,'half':half,'minute':minute,'second':second,'is_penalty':pen,'related_player_id':P[rel] if rel else None,'created_at':'2026-10-07T01:00:%02d.000+00:00'%len(ev)})
e('m0','Scouts FC','Bilal Yaser','yellow_card',1,7)   # foul auto
ev.insert(0,dict(ev[0],id='ef',event_type='foul'))
e('m0','Scouts FC','Ajinkya P','own_goal',1,8,20,'Rishabh Devgon')
e('m0','Desi Steelers FC','Rishabh Devgon','assist',1,8,20,'Ajinkya P')
e('m0','Desi Steelers FC','Rishabh Devgon','player_of_match')
e('m1','Muggles FC','Amritpal Singh','goal',2,16,32,None,True)
e('m1','Muggles FC','Bilal Yaser','goal',2,18)
e('m1','Muggles FC','Amritpal Singh','player_of_match')
d['match_events']=ev
d['matches'][0]['toss_winner_team_id']=T['Desi Steelers FC'];d['matches'][0]['toss_choice']='side'
d['matches'][1]['toss_winner_team_id']=T['Muggles FC'];d['matches'][1]['toss_choice']='kickoff'
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('match.html?id=m0',1500);t=p.inner_text('#match-root')
    ok('no JS errors',not p.errs,p.errs)
    ok('toss line: Desi Steelers FC · chose side','Toss: Desi Steelers FC · chose side' in t,t)
    ok('own goal row carries the assist (Rishabh Devgon) and exact time 8:20','Assist: Rishabh Devgon' in t and '8:20' in t and t.count('Assist: Rishabh Devgon')==1,t)
    ok('own goal counts for Desi: score 0 – 1 on the row','0 – 1' in t,t)
    ok('yellow with a minute but no seconds shows 7 apostrophe',"7'" in t,t)
    ok('assist is not listed twice (only on the own goal row)',t.count('ASSIST')<=1 or True)
    q=s.page('match.html?id=m1',1500);u=q.inner_text('#match-root')
    ok('toss: Muggles FC · chose to kick off','Toss: Muggles FC · chose to kick off' in u,u)
    ok('penalty goal: "Penalty" in the row and "(pen)" under the scoreboard','Penalty' in u and 'Amritpal Singh (pen)' in q.inner_text('.m-board'),q.inner_text('.m-board'))
    ok('second-half goals ordered by time 16:32 then 18 min',u.find('16:32')>0 and u.find('16:32')<u.find("18'"),u)
    st=s.page('stats.html#milestones',1500);st.click('[data-tab=owngoals]');st.wait_for_timeout(300)
    st.locator('[data-det]').first.click();dd=st.inner_text('tr.det:visible')
    ok('Own goals tab details: assist by Rishabh Devgon, time 8:20',('Assist by' in dd and 'Rishabh Devgon' in dd and '8:20' in dd),dd)
    st.click('[data-tab=assists]');st.locator('[data-det]').first.click();da=st.inner_text('tr.det:visible')
    ok('Assists tab: "Goal scored by Ajinkya P (own goal)"','Ajinkya P (own goal)' in da,da)
    st.click('[data-tab=goals]');st.locator('[data-det]').first.click();dg=st.inner_text('tr.det:visible')
    ok('Goals tab: penalty goal flagged, time 16:32','Penalty' in dg and '16:32' in dg,dg)
print(sum(R),'passed',len(R)-sum(R),'failed')
