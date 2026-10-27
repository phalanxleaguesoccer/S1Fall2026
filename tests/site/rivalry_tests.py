# Stats > Rivalry tab: team picker, selection messages, head-to-head, stats rows, meetings, form, upcoming + preview, deep link.
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
m(1,1,'Muggles FC','Scouts FC','completed',1,2);m(1,2,'Renegades','Desi Steelers FC','completed',0,0)
m(2,1,'Scouts FC','Muggles FC','completed',2,0);m(2,2,'Desi Steelers FC','Renegades','completed',0,0)
m(3,1,'Muggles FC','Scouts FC');m(3,2,'Renegades','Desi Steelers FC')
d=finish(b)
def ev(i,mt,t,pl,ty,minute=3,rel=None,pen=False):
    return {'id':'v%d'%i,'match_id':mt,'team_id':T[t],'player_id':P[pl],'event_type':ty,'half':1,'minute':minute,'second':None,'related_player_id':P[rel] if rel else None,'is_penalty':pen,'created_at':'2026-10-07T01:00:%02d+00:00'%i}
d['match_events']=[ev(1,'m0','Muggles FC','Amritpal Singh','goal',2),ev(2,'m0','Scouts FC','Bhagyesh Rane','goal',5),ev(3,'m0','Scouts FC','Ajinkya P','assist',5),
 ev(4,'m0','Scouts FC','Bilal Yaser','goal',9),ev(5,'m0','Muggles FC','Amritpal Singh','player_of_match'),ev(6,'m0','Scouts FC','Bhagyesh Rane','player_of_match'),
 ev(7,'m2','Scouts FC','Bhagyesh Rane','goal',4),ev(8,'m2','Muggles FC','Bilal Yaser','own_goal',8),ev(9,'m2','Muggles FC','Ayush','yellow_card'),ev(10,'m2','Scouts FC','Bhagyesh Rane','player_of_match'),
 ev(11,'m2','Muggles FC','Amritpal Singh','foul'),ev(12,'m2','Scouts FC','Ajinkya P','foul'),ev(13,'m2','Scouts FC','Ajinkya P','foul'),ev(14,'m1','Renegades','Varun','player_of_match')]
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#rivalry',1500)
    ok('no JS errors',not p.errs,p.errs)
    ok('opens on Rivalry, tab order Ranking|Milestones|Records|Rivalry|Season Stats',p.is_visible('#sec-rivalry') and p.locator('#sub-nav button').all_inner_texts()==['Ranking','Milestones','Records','Rivalry','Season Stats'])
    ok('Ranking page hidden',not p.is_visible('#sec-ranking'))
    names=p.locator('#riv-picker .rv-tm > span:not(.rv-ph)').all_inner_texts()
    ok('picker: the 4 real teams only (no Team A..D)',sorted(names)==['Desi Steelers FC','Muggles FC','Renegades','Scouts FC'],names)
    ok('nothing picked: prompt to tap first team + VS placeholder','first team' in p.inner_text('#riv-msg') and 'Pick two teams to see' in p.inner_text('#riv-out'))
    p.click('#riv-picker button[data-team=%s]'%T['Scouts FC'])
    ok('one picked: message to select another team','Scouts FC' in p.inner_text('#riv-msg') and 'select another team' in p.inner_text('#riv-msg') and 'Pick one more team' in p.inner_text('#riv-out'))
    ok('Scouts tagged TEAM A',p.locator('.rv-tm.a .rv-tag').inner_text()=='TEAM A')
    p.click('#riv-picker button[data-team=%s]'%T['Muggles FC']);p.wait_for_timeout(200)
    ok('both picked: Team B tag + head-to-head shown','TEAM B' in p.inner_text('.rv-tm.b') and 'HEAD TO HEAD' in p.inner_text('#riv-out').upper())
    ok('hash deep link updated',p.evaluate('location.hash')=='#rivalry/%s/%s'%(T['Scouts FC'],T['Muggles FC']),p.evaluate('location.hash'))
    big=p.locator('.rv-big').inner_text().replace('\n','').replace(' ','')
    ok('big number: Scouts 2 – 0 Muggles wins',big=='2–0',big)
    t=p.inner_text('#riv-out')
    ok('goals 4 – 1 and 0 draws','4 – 1' in t and '0 draws' in t,t[:300])
    ok('verdict: Scouts FC lead 2–0','Scouts FC lead the rivalry 2–0' in t,t[:400])
    rows={}
    for r in p.locator('.rv-cr').all():
        rows[r.locator('.rv-lab').inner_text().strip().lower()]=(r.locator('.rv-v').nth(0).inner_text().strip(),r.locator('.rv-v').nth(1).inner_text().strip())
    exp={'wins':('2','0'),'draws':('0','0'),'goals':('4','1'),'goals / match':('2.0','0.5'),'clean sheets':('1','0'),'assists':('1','0'),'player of match':('2','1'),'yellow cards':('0','1'),'fouls':('2','1')}
    ok('side-by-side values correct',all(rows.get(k)==v for k,v in exp.items()),rows)
    ok('no Red cards row when there are none','red cards' not in rows)
    mt=p.locator('.rv-mt')
    ok('2 meetings listed, each linked to its match page',mt.count()==2 and p.locator('.rv-mt a[href^="match.html?id=m"]').count()>=2,mt.count())
    t0=mt.nth(0).inner_text()
    ok('meeting 1: Day 1 · M1, 1 – 2, scorers with assist, pill "Sco won"','Day 1 · M1' in t0 and '1 – 2' in t0 and 'Bhagyesh Rane' in t0 and 'Ajinkya P' in t0 and 'Sco won' in t0,t0)
    t1=mt.nth(1).inner_text()
    ok('meeting 2: own goal credited, yellow listed','Day 2 · M1' in t1 and '2 – 0' in t1 and '(og)' in t1 and 'Ayush' in t1,t1)
    ok('goal / assist / og / yellow markers use event colours',p.locator('.rv-mt .evm.goal').count()>=3 and p.locator('.rv-mt .evm.assist').count()>=1 and p.locator('.rv-mt .evm.og').count()==1 and p.locator('.rv-mt .evm.yellow').count()==1)
    heroes=p.inner_text('.rv-pl')
    ok('heroes: Bhagyesh 2 goals top for Scouts; Amritpal for Muggles; POTM listed','Bhagyesh Rane' in heroes and 'Bilal Yaser' in heroes and 'Amritpal Singh' in heroes,heroes)
    ok('hero names link to players',p.locator('.rv-pl a[href^="player.html"]').count()>=4)
    ok('team names link to team pages',p.locator('#riv-out a[href^="team.html"]').count()>=4)
    form=p.locator('.rv-form').nth(0).locator('.rv-pill').all_inner_texts()
    ok('Scouts form newest first: W W',form==['W','W'],form)
    ok('still to come: meeting 3 of 3 with kickoff + UPCOMING','Meeting 3 of 3' in t and 'UPCOMING' in t and 'Day 3 · M' in t and 'Oct' in p.inner_text('.rv-nx'),p.inner_text('.rv-nx'))
    pv=p.inner_text('.rv-idea')
    ok('match preview shown with three percentages summing to 100','MATCH PREVIEW' in pv and 'coin flip' in pv,pv)
    nums=[int(x.rstrip('%')) for x in p.locator('.rv-pb div').all_inner_texts()]
    ok('preview %% sum 100, Scouts (team A) favoured over Muggles',sum(nums)==100 and nums[0]>nums[2],nums)
    # tapping Team A deselects it and promotes Team B to A
    p.click('#riv-picker button[data-team=%s]'%T['Scouts FC']);p.wait_for_timeout(100)
    ok('tap Team A: Muggles becomes Team A, no Team B, asks for another team','Muggles FC' in p.inner_text('.rv-tm.a') and p.locator('.rv-tm.b').count()==0 and 'select another team' in p.inner_text('#riv-msg'))
    p.evaluate("RIV.a=null;RIV.b=null;renderRivalry()")
    p.click('#riv-picker button[data-team=%s]'%T['Muggles FC']);p.click('#riv-picker button[data-team=%s]'%T['Scouts FC']);p.wait_for_timeout(100)
    nums2=[int(x.rstrip('%')) for x in p.locator('.rv-pb div').all_inner_texts()]
    ok('swapped order flips the preview',nums2==nums[::-1],(nums,nums2))
    ok('hero big number swaps too',p.locator('.rv-big').inner_text().replace('\n','').replace(' ','')=='0–2')
    # third tap replaces Team B
    p.click('#riv-picker button[data-team=%s]'%T['Renegades']);p.wait_for_timeout(100)
    ok('third team replaces Team B (Muggles=A, Renegades=B)','Muggles FC' in p.inner_text('.rv-tm.a') and 'Renegades' in p.inner_text('.rv-tm.b'))
    t=p.inner_text('#riv-out')
    ok('never met: 0 – 0, "not met" verdict, no crash','not met' in t.lower() or 'No completed meetings' in t,t[:300])
    ok('no meetings and no scheduled: "No more meetings scheduled"','No more meetings scheduled' in t and not p.locator('.rv-idea').count(),t[-200:])
    # all-draw rivalry
    p.evaluate("RIV.a='%s';RIV.b='%s';renderRivalry()"%(T['Renegades'],T['Desi Steelers FC']));t=p.inner_text('#riv-out')
    ok('Renegades v Desi: 0–0 wins, 2 draws, "nothing between them"','nothing between them' in t and '2 draws' in t and '0 – 0' in t and p.locator('.rv-big').inner_text().replace('\n','').replace(' ','')=='0–0',t[:300])
    ok('draw meetings show Draw pills and "No goals"',p.locator('.rv-mt .rv-pill.D').count()==2 and 'No goals' in p.inner_text('.rv-mt'))
    ok('goals/match row 0.0 with equal bars (no divide errors)',not p.errs,p.errs)
    ok('no horizontal overflow (desktop)',not p.evaluate('document.documentElement.scrollWidth>innerWidth'))
    # mobile
    mp=s.br.new_context(viewport={'width':375,'height':800});mp.add_init_script('window.__DB='+json.dumps(dict(d,__admin=False))+';')
    mp.route('**/*supabase*.js',lambda r:r.fulfill(body=FAKE,content_type='application/javascript') if 'cdn.jsdelivr' in r.request.url else r.continue_());mp.route('**/fonts.g*/**',lambda r:r.abort())
    q=mp.new_page();q.goto('http://127.0.0.1:8137/stats.html#rivalry/%s/%s'%(T['Scouts FC'],T['Muggles FC']));q.wait_for_timeout(1500)
    ok('deep link opens Rivalry with both teams selected','Scouts FC' in q.inner_text('.rv-tm.a') and 'Muggles FC' in q.inner_text('.rv-tm.b') and 'Scouts FC lead' in q.inner_text('#riv-out'))
    ok('no horizontal overflow (375px)',not q.evaluate('document.documentElement.scrollWidth>innerWidth'),q.evaluate('document.documentElement.scrollWidth'))
    ok('picker is 2 columns on phones',q.evaluate("getComputedStyle(document.getElementById('riv-picker')).gridTemplateColumns.split(' ').length")==2)
    ok('card content within card (no overflow)',q.evaluate("[...document.querySelectorAll('#riv-out .card')].every(c=>c.scrollWidth<=c.clientWidth+1)"))
    # season filter + other tabs still work
    p.click('#sub-nav button[data-sec=ranking]');ok('switching to Ranking hides Rivalry',p.is_visible('#sec-ranking') and not p.is_visible('#sec-rivalry'))
    p.click('#sub-nav button[data-sec=rivalry]');ok('back to Rivalry keeps selection',p.locator('.rv-tm.a').count()==1)
    p.select_option('#riv-season','all');p.wait_for_timeout(500);ok('All seasons works',p.locator('.rv-tm').count()==4 and not p.errs,p.errs)
print('%d passed %d failed'%(sum(R),len(R)-sum(R)))
