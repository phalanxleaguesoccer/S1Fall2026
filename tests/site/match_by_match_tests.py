# Player page "Match-by-Match" lists every match of the player's team (played / rested / absent), even with no events.
src=open(__file__.replace('match_by_match_tests.py','captain_tests.py')).read().split('d,T,P=build()')[0]
exec(src)
d,T,P=build()
with sync_playwright() as pw:
    s=Site(pw,d)
    def mbm(name):
        p=s.page('player.html?id='+P[name],1500);p.wait_for_timeout(400)
        p.evaluate("document.getElementById('history-mode').scrollIntoView()")
        try: p.click('text=Maximize',timeout=1500)
        except Exception: pass
        p.select_option('#history-mode','matches');p.wait_for_timeout(900);return p
    p=mbm('Nasiq');t=p.inner_text('#events-list')
    ok('Nasiq (no events): all 3 Desi matches listed, not "No events logged"',p.locator('#events-list > div').count()==3 and 'No events logged' not in t,t)
    ok('rested match shown as Rested',p.locator('#events-list .pill',has_text='Rested').count()==1,t)
    ok('summary line counts played/rested',('1 rested' in t) and ('played' in t),t[:200])
    ok('match, team and opponent are links',p.locator('#events-list a[href^="match.html"]').count()>=3 and p.locator('#events-list a[href^="team.html"]').count()>=6,p.locator('#events-list a').count())
    ok('captain chip on matches he captained',p.locator('#events-list .chip',has_text='Captain').count()==2,t)
    ok('result with score shown',('Drew 0–0' in t or 'Won' in t or 'Lost' in t),t)
    p2=mbm('Amritpal Singh');t2=p2.inner_text('#events-list')
    ok('Amritpal: POTM event shown on its match','Player of the Match' in t2,t2)
    ok('no JS errors',not p.errs and not p2.errs,(p.errs,p2.errs))
    tp=s.page('teams.html',1200)
    ok('teams page no longer shows "pts left"','pts left' not in tp.inner_text('body') and 'players' in tp.inner_text('body') or 'player' in tp.inner_text('body'),tp.inner_text('body')[:300])
print(sum(R),'/',len(R))
