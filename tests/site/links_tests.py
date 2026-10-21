# Every team name / match label / player name should be a link (stats tabs, home, matches, team, player, match pages).
src=open(__file__.replace('links_tests.py','captain_tests.py')).read().split('d,T,P=build()')[0]
exec(src)
d,T,P=build()
d['match_events'].append({'id':'g1','match_id':'m0','team_id':T['Muggles FC'],'player_id':P['Amritpal Singh'],'event_type':'goal','half':1,'minute':5,'related_player_id':None,'is_penalty':False,'created_at':'2026-10-07T01:00:09+00:00'})
# one scheduled match so the home page "upcoming" list has something
with sync_playwright() as pw:
    s=Site(pw,d)
    def hrefs(p,sel): return p.locator(sel).evaluate_all('e=>e.map(x=>x.getAttribute("href"))')
    p=s.page('stats.html#milestones',1500);p.click('#tabs button[data-tab=captains]');p.wait_for_timeout(300)
    tb=p.locator('#ms-body table')
    h0=hrefs(p,'#ms-body table >> nth=0 >> tbody tr td:nth-child(1) a')
    ok('Captain changes: "When" links to the match',len(h0)>=2 and all(x.startswith('match.html?id=') for x in h0),h0)
    ok('Captain changes: team column links to team',all(x.startswith('team.html?id=') for x in hrefs(p,'#ms-body table >> nth=0 >> tbody tr td:nth-child(2) a')) and len(hrefs(p,'#ms-body table >> nth=0 >> tbody tr td:nth-child(2) a'))>=2)
    ok('Matches captained: team column links',len(hrefs(p,'#cap-totals tbody tr td:nth-child(2) a'))==len(p.locator('#cap-totals tbody tr').all()))
    ok('Captain in every match: team column links',len(hrefs(p,'#ms-body table >> nth=2 >> tbody tr td:nth-child(2) a'))==10)
    for tab,ty in (('goals','goal'),):
        p.click('#tabs button[data-tab=%s]'%tab);p.wait_for_timeout(300)
        p.click('#ms-body [data-det]');p.wait_for_timeout(200)
        det=p.locator('#ms-body .det-grid').first
        ok('Milestone details: match, team and opponent link',det.locator('a[href^="match.html"]').count()>=1 and det.locator('a[href^="team.html"]').count()>=3,det.inner_text())
        ok('Milestone table: team cell links',p.locator('#ms-body tbody tr:not(.det) td:nth-child(3) a[href^="team.html"]').count()>=1)
    ok('no JS errors (stats)',not p.errs,p.errs)
    # team page schedule
    q=s.page('team.html?id='+T['Renegades'],1500);q.wait_for_timeout(400)
    ok('team page schedule: Day, teams and score link',len(hrefs(q,'#schedule-body tr td:nth-child(2) a'))>=1 and len(hrefs(q,'#schedule-body tr td:nth-child(3) a[href^="team.html"]'))>=2,q.inner_text('#schedule-body')[:200])
    first=q.locator('#schedule-body tr td:nth-child(3) a[href^="team.html"]').first;first.click();q.wait_for_timeout(500)
    ok('clicking a team in the schedule opens that team (not the match)','team.html?id=' in q.url,q.url)
    q=s.page('team.html?id='+T['Renegades'],1500);q.wait_for_timeout(400)
    ok('team page captain card: match labels link',q.locator('#captain-body a[href^="match.html"]').count()>=1)
    # player page
    q=s.page('player.html?id='+P['Amritpal Singh'],1500);q.wait_for_timeout(500)
    ok('player page captain table: team and opponent link',q.locator('#captain-body td a[href^="team.html"]').count()>=2,q.inner_text('#captain-body')[:200])
    # home page upcoming list (one match made 'scheduled')
    d2=build()[0];d2['matches'][4]['status']='scheduled'
    s2=Site(pw,d2);h=s2.page('index.html',1500);h.wait_for_timeout(300)
    ok('home upcoming: Day links to match, teams link',h.locator('#upcoming-list a[href^="match.html"]').count()==1 and h.locator('#upcoming-list a[href^="team.html"]').count()==2,h.inner_text('#upcoming-list'))
    ok('no JS errors (home)',not h.errs,h.errs)
    # matches page
    q=s.page('matches.html',1500);q.wait_for_timeout(300)
    ok('matches page: team names and score link, no nested links',q.locator('.match-row a[href^="team.html"]').count()>=2 and q.locator('.match-row a[href^="match.html"]').count()>=1 and q.locator('a a').count()==0)
    q.locator('.match-row').first.locator('.pill').click();q.wait_for_timeout(500)
    ok('clicking the row (not a link) still opens the match','match.html?id=' in q.url,q.url)
    # match page
    q=s.page('match.html?id=m0',1500);q.wait_for_timeout(500)
    ok('match page: team names link everywhere',q.locator('#match-root a[href^="team.html"]').count()>=4,q.locator('#match-root a[href^="team.html"]').count())
    ok('no JS errors (pages)',not q.errs,q.errs)
print(sum(R),'/',len(R))
