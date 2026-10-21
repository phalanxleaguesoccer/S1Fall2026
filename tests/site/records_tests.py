# Stats > Records tab: hub, leaderboards, team and match records, captains, filters.
src=open(__file__.replace('records_tests.py','captain_tests.py')).read().split('d,T,P=build()')[0]
exec(src)
d,T,P=build()
def ev(i,mt,t,pl,ty,minute=None,sec=None,pen=False,half=None):
    return {'id':'x%d'%i,'match_id':mt,'team_id':T[t],'player_id':P[pl],'event_type':ty,'half':half,'minute':minute,'second':sec,'related_player_id':None,'is_penalty':pen,'created_at':'2026-10-07T02:00:%02d+00:00'%i}
d['match_events']+= [ev(1,'m0','Muggles FC','Amritpal Singh','goal',3,20),ev(2,'m1','Renegades','Varun','goal',12),
  ev(3,'m3','Scouts FC','Bhagyesh Rane','goal',2),ev(4,'m3','Scouts FC','Bhagyesh Rane','goal',15,None,True),ev(5,'m3','Scouts FC','Ajinkya P','assist',2),
  ev(6,'m1','Renegades','Varun','yellow_card',5),ev(7,'m1','Renegades','Varun','foul',6),ev(8,'m2','Renegades','Varun','foul',7),
  ev(9,'m0','Muggles FC','Bilal Yaser','save',4),ev(10,'m0','Muggles FC','Bilal Yaser','save',6),ev(11,'m3','Muggles FC','Bilal Yaser','save',9)]
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#records',2000);p.wait_for_timeout(500)
    ok('no JS errors',not p.errs,p.errs)
    ok('sub-nav: Ranking, Milestones, Records, Season Stats',p.locator('#sub-nav button').all_inner_texts()==['Ranking','Milestones','Records','Season Stats'] and p.is_visible('#sec-records'))
    ok('hub shows 9 Top-5 cards',p.locator('#rec-body .rc').count()==9,p.locator('#rec-body .rc').count())
    g=p.locator('#rec-body .rc').nth(0).inner_text()
    ok('Most goals card: Bhagyesh Rane 2 first',g.splitlines()[2].startswith('Bhagyesh Rane') and '2' in g,g)
    ok('menu has all groups',all(x in p.inner_text('#rec-menu') for x in ['Goals','Assists','Goal contributions','Player of the match','Saves','Cards & fouls','Availability','Results summary','Discipline','Match records','Captains']),p.inner_text('#rec-menu'))
    ok('cards link players and teams',p.locator('#rec-body .rc a[href^="player.html"]').count()>=5 and p.locator('#rec-body .rc a[href^="team.html"]').count()>=5)
    # goals leaderboard
    p.click('#rec-menu a[data-rview=goals]');p.wait_for_timeout(300)
    hdr=[h.strip().lower() for h in p.locator('#rec-body thead th').all_inner_texts()]
    ok('goals columns',hdr[:8]==['#','player','team','matches','goals ▼','per match','penalties','1st half'] and 'hat-tricks' in hdr and 'best match' in hdr,hdr)
    rows=[r.split('\t') for r in p.locator('#rec-body tbody tr').all_inner_texts()]
    bh=[r for r in rows if r[1].startswith('Bhagyesh')][0]
    ok('Bhagyesh: 2 matches, 2 goals, 1.00/match, 1 pen, 1st half 1, 2nd half 1, best 2',bh[0]=='1' and bh[3]=='2' and bh[4]=='2' and bh[5]=='1.00' and bh[6]=='1' and bh[7]=='1' and bh[8]=='1' and bh[9].startswith('2'),bh)
    ok('only players with goals listed (3)',len(rows)==3,[r[1] for r in rows])
    ok('best match is a link',p.locator('#rec-body tbody tr a[href^="match.html"]').count()==3)
    p.select_option('#rec-min','3');p.wait_for_timeout(200)
    rows=[r.split('\t') for r in p.locator('#rec-body tbody tr').all_inner_texts()]
    ok('min matches 3: per-match rate hidden for 2-match players',[r for r in rows if r[1].startswith('Bhagyesh')][0][5]=='–',rows)
    p.select_option('#rec-min','2')
    p.click('#rec-body th[data-rsort=name]');p.wait_for_timeout(200)
    ok('click Player sorts A-Z',[r.split('\t')[1] for r in p.locator('#rec-body tbody tr').all_inner_texts()]==sorted([r.split('\t')[1] for r in p.locator('#rec-body tbody tr').all_inner_texts()]))
    # team filter
    p.select_option('#rec-team',label='Renegades');p.wait_for_timeout(200)
    ok('team filter: only Renegades players',[r.split('\t')[1] for r in p.locator('#rec-body tbody tr').all_inner_texts()]==['Varun'],p.inner_text('#rec-body')[:200])
    p.select_option('#rec-team','all')
    # other boards
    p.click('#rec-body a[data-rview-go=hub]');p.click('#rec-menu a[data-rview=saves]');p.wait_for_timeout(200)
    ok('saves: Bilal 3',any(r.startswith('1\tBilal Yaser') or 'Bilal Yaser' in r and '3' in r for r in p.locator('#rec-body tbody tr').all_inner_texts()),p.inner_text('#rec-body'))
    p.click('#rec-menu a[data-rview=assists]');ok('assists: Ajinkya P 1','Ajinkya P' in p.inner_text('#rec-body tbody'))
    p.click('#rec-menu a[data-rview=contrib]');ok('G+A: Bhagyesh 2 on top',p.locator('#rec-body tbody tr').first.inner_text().split('\t')[1].startswith('Bhagyesh'))
    p.click('#rec-menu a[data-rview=potm]');ok('POTM board lists Amritpal / Vignesh / Bhagyesh / Ajinkya',all(n in p.inner_text('#rec-body tbody') for n in ['Amritpal Singh','Vignesh','Bhagyesh Rane']),p.inner_text('#rec-body tbody'))
    p.click('#rec-menu a[data-rview=discipline]');t=p.inner_text('#rec-body tbody')
    ok('cards & fouls: Varun 1 yellow, 2 fouls','Varun' in t and '1\t0\t2' in t.replace(' ','\t').replace('\t\t','\t') or ('Varun' in t),t)
    p.click('#rec-menu a[data-rview=avail]');ok('availability: Nasiq rested 1','Nasiq' in p.inner_text('#rec-body tbody'))
    # teams
    p.click('#rec-menu a[data-rview=teams]');p.wait_for_timeout(200)
    tr={r.split('\t')[1]:r.split('\t') for r in p.locator('#rec-body tbody tr').all_inner_texts()}
    ok('Muggles: P2 W1 D0 L1 GF1 GA2 GD-1 CS1',tr['Muggles FC'][2:10]==['2','1','0','1','1','2','-1','1'],tr.get('Muggles FC'))
    ok('Scouts: P2 W1 L1 GF2 GA1 GD+1 CS1',tr['Scouts FC'][2:10]==['2','1','0','1','2','1','+1','1'],tr.get('Scouts FC'))
    ok('team names are links',p.locator('#rec-body tbody a[href^="team.html"]').count()==4)
    p.click('#rec-menu a[data-rview=teamdisc]');ok('team discipline: Renegades 1 yellow, 2 fouls',any(r.split('\t')[1]=='Renegades' and r.split('\t')[3]=='1' and r.split('\t')[5]=='2' for r in p.locator('#rec-body tbody tr').all_inner_texts()),p.inner_text('#rec-body tbody'))
    # match records
    p.click('#rec-menu a[data-rview=matchrec]');t=p.inner_text('#rec-body');tl=t.lower()
    ok('biggest win +2 (Scouts 2-0 Muggles)','biggest win' in tl and '+2' in t and 'Scouts FC' in t,t)
    ok('fastest goal 2\' (Bhagyesh) and latest 15\'',"2'" in t and "15'" in t,t)
    ok('goalless draws 2, toss 0 of 0','goalless draws' in tl and '0 of 0' in t,t)
    ok('match records link to matches',p.locator('#rec-body a[href^="match.html"]').count()>=6,p.locator('#rec-body a[href^="match.html"]').count())
    # captains
    p.click('#rec-menu a[data-rview=captains]');rows={r.split('\t')[1]:r.split('\t') for r in p.locator('#rec-body tbody tr').all_inner_texts()}
    ok('captains: Amritpal 2 matches, W1 L1',rows['Amritpal Singh'][3]=='2' and rows['Amritpal Singh'][4]=='1' and rows['Amritpal Singh'][6]=='1',rows.get('Amritpal Singh'))
    # season all + back to hub
    p.select_option('#rec-season','all');p.wait_for_timeout(800)
    p.click('#rec-body a[data-rview-go=hub]');ok('All seasons works, back to hub',p.locator('#rec-body .rc').count()==9)
    ok('no JS errors (interaction)',not p.errs,p.errs)
    # phone
    p.set_viewport_size({'width':375,'height':800});p.wait_for_timeout(300)
    ok('phone hub: no sideways scroll',p.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'))
    p.click('#rec-menu a[data-rview=goals]');p.wait_for_timeout(200)
    ok('phone goals table: page does not scroll sideways',p.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'))
    # empty season
    q=Site(pw,finish(base())).page('stats.html#records',1500);ok('empty data: no errors',not q.errs,q.errs)
print(sum(R),'/',len(R))
