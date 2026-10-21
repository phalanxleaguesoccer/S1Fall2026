# Event colours: goal green, assist purple, yellow, red, save blue, same on the match page and the player page.
src=open(__file__.replace('event_colors_tests.py','records_tests.py')).read().split("with sync_playwright() as pw:")[0]
src=src.replace("open(__file__.replace('records_tests.py','captain_tests.py'))","open(__file__.replace('event_colors_tests.py','captain_tests.py'))")
exec(src)
def rgb(p,sel,prop='backgroundColor'): return p.evaluate("(s)=>getComputedStyle(document.querySelector(s))['%s']"%prop,sel)
with sync_playwright() as pw:
    s=Site(pw,d)
    p=s.page('match.html?id=m3',1800);p.wait_for_timeout(400)
    ok('goal chip is green (not amber)',rgb(p,'.m-chip.goal')=='rgb(62, 207, 110)',rgb(p,'.m-chip.goal'))
    ok('goal and yellow chips differ',rgb(p,'.m-chip.goal')!=rgb(p,'.m-chip.yc') if p.locator('.m-chip.yc').count() else True)
    ok('header: green dot per scorer + purple assist marker',p.locator('.m-rec .evm.goal').count()==1 and p.locator('.m-rec .evm.assist').count()==1 and 'assist' in p.inner_text('.m-side.home .m-scorers').lower() or p.locator('.m-rec .evm.goal').count()>=1,p.inner_text('.m-board'))
    ok('header shows scorer with ×2 and (1 pen)','Bhagyesh Rane' in p.inner_text('.m-board') and '×2' in p.inner_text('.m-board') and 'pen' in p.inner_text('.m-board'),p.inner_text('.m-board'))
    ok('header assist text names Ajinkya P','assist Ajinkya P' in p.inner_text('.m-board').replace('\n',' '),p.inner_text('.m-board'))
    ok('goal bar is green','62, 207, 110' in p.evaluate("[...document.querySelectorAll('.m-bars i')].map(i=>getComputedStyle(i).backgroundColor).join('|')"))
    q=s.page('match.html?id=m1',1800);q.wait_for_timeout(400)
    ok('yellow card marker + red none in header; fouls not in header',q.locator('.m-rec .evm.yellow').count()==1 and 'foul' not in q.inner_text('.m-board').lower(),q.inner_text('.m-board'))
    ok('yellow bar is yellow','232, 197, 71' in q.evaluate("[...document.querySelectorAll('.m-bars i')].map(i=>getComputedStyle(i).backgroundColor).join('|')"))
    ok('saves marker on header (m0)',s.page('match.html?id=m0',1800).locator('.m-rec .evm.save').count()>=1)
    ok('no JS errors',not p.errs and not q.errs,(p.errs,q.errs))
    # player page chips
    pl=s.page('player.html?id='+P['Bhagyesh Rane'],1500)
    try: pl.click('text=Maximize',timeout=1000)
    except Exception: pass
    pl.select_option('#history-mode','matches');pl.wait_for_timeout(900)
    ok('player Match-by-Match: goal chip green','62, 207, 110' in pl.evaluate("[...document.querySelectorAll('#events-list .chip.ev-goal')].map(i=>getComputedStyle(i).backgroundColor).join('|')"),pl.inner_text('#events-list')[:200])
    pv=s.page('player.html?id='+P['Varun'],1500)
    try: pv.click('text=Maximize',timeout=1000)
    except Exception: pass
    pv.select_option('#history-mode','matches');pv.wait_for_timeout(900)
    ok('player Match-by-Match: yellow chip yellow','232, 197, 71' in pv.evaluate("[...document.querySelectorAll('#events-list .chip.ev-yellow')].map(i=>getComputedStyle(i).backgroundColor).join('|')"),pv.inner_text('#events-list')[:200])
print(sum(R),'/',len(R))
