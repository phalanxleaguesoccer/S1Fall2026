from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
# Muggles 1-2 Scouts: Scouts' 2nd goal is an OWN GOAL by Amritpal (Muggles)
m(1,1,'Muggles FC','Scouts FC','completed',1,2);m(1,2,'Renegades','Desi Steelers FC','completed',0,0)
d=finish(b);ev=[]
def e(match,team,pl,typ,rel=None,half=None,minute=None):
    ev.append({'id':'e%02d'%len(ev),'match_id':match,'team_id':T[team],'player_id':P[pl],'event_type':typ,'half':half,'minute':minute,'related_player_id':P[rel] if rel else None,'created_at':'2026-10-07T01:00:%02d+00:00'%len(ev)})
e('m0','Muggles FC','Vignesh','goal',None,1)
e('m0','Scouts FC','Bhagyesh Rane','goal',None,2);e('m0','Muggles FC','Amritpal Singh','own_goal',None,2)
e('m1','Renegades','Varun','own_goal',None,1)
d['match_events']=ev
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('match.html?id=m0',1500);t=p.inner_text('#match-root')
    ok('no JS errors',not p.errs,p.errs)
    ok('OWN GOAL chip, counts for opposing team, running score 1–2','OWN GOAL' in t and 'Counts for Scouts FC' in t and '1 – 2' in t,t)
    ok('scoreboard lists the own goal under the team it counts for',p.locator('.m-side.away .m-scorers').inner_text().replace('\n',' ').find('Amritpal Singh own goal')>=0 and 'own goal' not in p.locator('.m-side.home .m-scorers').inner_text().lower(),(p.locator('.m-side.away .m-scorers').inner_text(),p.locator('.m-side.home .m-scorers').inner_text()))
    ok('own goal is not a goal for the player: Amritpal G=0, OG=1 in stats table','OG' in t and p.locator('.m-ptable').first.inner_text().replace('\n',' ').find('Amritpal Singh')>=0,p.locator('.m-ptable').first.inner_text())
    row=[r for r in p.locator('.m-ptable tbody tr').all_inner_texts() if 'Amritpal' in r][0].split('\t')
    ok('Amritpal row: G 0, A 0, OG 1',row[2:5]==['0','0','1'],row)
    ok('stats bars include Own goals row','Own goals' in t,t)
    q=s.page('match.html?id=m1',1200);ok('0-0 match with an own goal: still lists it (shows chip)', 'OWN GOAL' in q.inner_text('#match-root'),q.inner_text('#match-root')[:200])
    st=s.page('stats.html#milestones',1500);ok('Own goals tab exists',st.locator('[data-tab=owngoals]').count()==1)
    st.click('[data-tab=owngoals]');st.wait_for_timeout(300)
    rows=[r.split('\t') for r in st.locator('#ms-body tbody tr:not(.det)').all_inner_texts()]
    ok('own goals tab lists both, in order, with the player team',[r[1:3] for r in rows]==[['Amritpal Singh','Muggles FC'],['Varun','Renegades']] or [r[1:3] for r in rows]==[['Varun','Renegades'],['Amritpal Singh','Muggles FC']],rows)
    st.locator('[data-det]').first.click();det=st.inner_text('tr.det:visible')
    ok('details: team represented, "counts as a goal for" the opponent, Own goal number',all(x in det for x in ['Counts as a goal for','Scouts FC','Own goal number in tournament']) ,det)
    st.click('[data-tab=goals]');gl=st.locator('#ms-body tbody tr:not(.det)').all_inner_texts()
    ok('Goals tab unchanged: own goals not included (2 real goals)',len(gl)==2,gl)
    pp=s.page('player.html?id='+P['Amritpal Singh'],1200);pp.click('#history-toggle');pp.wait_for_timeout(600)
    h=[x.strip() for x in pp.locator('#history-body thead').first.inner_text().split()]
    ct=pp.locator('#career-totals-body td').all_inner_texts()
    ok('profile: OG column, career totals goals 0 / OG 1 (no JS errors)','OG' in pp.inner_text('#history-body') and ct[3]=='0' and ct[5]=='1' and not pp.errs,(ct,pp.errs))
    cur=pp.locator('#stats-body td').all_inner_texts()
    ok('profile current season row has OG=1',cur[7]=='1' if len(cur)>7 else False,cur)
    pm=s.page('player.html?id='+P['Amritpal Singh'],1200);pm.select_option('#history-mode','matches') if False else None
    mp=Site(pw,d).page('match.html?id=m0',1200);mp.set_viewport_size({'width':390,'height':800});mp.wait_for_timeout(300)
    ok('phone: no sideways scroll',mp.evaluate('document.documentElement.scrollWidth')<=390)
print(sum(R),'passed',len(R)-sum(R),'failed')
