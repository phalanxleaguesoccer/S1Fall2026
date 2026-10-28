# Sponsor pop-up: appears on first page of a session, close options, links, once per session, skipped on admin/sponsors page and for automated browsers.
import json
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();d=finish(b)
with sync_playwright() as pw:
    # default test browsers are "webdriver": no pop-up (so other suites are not blocked by it)
    s=Site(pw,d);p=s.page('index.html',1500)
    ok('automated browsers do not get the pop-up by default',p.locator('#spp').count()==0)
    # forced on
    s2=Site(pw,d);s2.ctx.add_init_script('window.__FORCE_SPONSOR_POPUP=true;')
    p=s2.page('index.html',400)
    ok('not instant: appears after a short delay',p.locator('#spp').count()==0)
    p.wait_for_timeout(1200)
    ok('pop-up appears on opening the page',p.is_visible('#spp') and 'OUR SPONSORS' in p.inner_text('#spp').upper(),p.inner_text('body')[:100])
    t=p.inner_text('#spp')
    ok('shows both sponsors, Robinson, address','TROPICAL SMOOTHIE CAFE – ROBINSON' in t.upper() and '322 MCHOLME DR' in t.upper() and 'EASEOURTRIP' in t.upper(),t)
    hs=p.eval_on_selector_all('#spp a','els=>els.map(e=>e.href)')
    ok('links are all there (store, directions, tel, EaseOurTrip, all sponsors)','https://locations.tropicalsmoothiecafe.com/pa/pittsburgh/322-mcholme-dr' in hs and 'https://www.easeourtrip.com/' in hs and any('maps/dir' in h for h in hs) and any(h.startswith('tel:') for h in hs) and any(h.endswith('sponsors.html') for h in hs),hs)
    ok('external links open in a new tab safely',p.eval_on_selector_all('#spp a[href^=http]','els=>els.every(e=>e.target==="_blank"&&/noopener/.test(e.rel))'))
    ok('logos loaded',p.eval_on_selector_all('#spp img','els=>els.length===2&&els.every(i=>i.complete&&i.naturalWidth>50)'))
    ok('has a close X and a Close button',p.is_visible('#spp-x') and p.is_visible('#spp-close'))
    p.locator('#spp-box,.spp-box').screenshot(path='/tmp/spp_desk.png')
    p.click('#spp-x');p.wait_for_timeout(200)
    ok('X closes it',p.locator('#spp').count()==0 and not p.evaluate('document.body.classList.contains("spp-open")'))
    # once per session
    p.goto('http://127.0.0.1:8137/matches.html');p.wait_for_timeout(1800);q=p
    ok('does not come back on the next page of the same tab/session',q.locator('#spp').count()==0)
    # fresh session: Close button, Esc, outside click
    for how in ('btn','esc','out'):
        s3=Site(pw,d);s3.ctx.add_init_script('window.__FORCE_SPONSOR_POPUP=true;')
        p3=s3.page('stats.html',1500)
        ok('(%s) pop-up shows on another page too'%how,p3.is_visible('#spp'))
        if how=='btn': p3.click('#spp-close')
        elif how=='esc': p3.keyboard.press('Escape')
        else: p3.mouse.click(5,5)
        p3.wait_for_timeout(200)
        ok('(%s) closes'%how,p3.locator('#spp').count()==0)
        ok('(%s) page is usable again (scroll unlocked)'%how,not p3.evaluate('document.body.classList.contains("spp-open")') and not p3.errs,p3.errs)
    # not on sponsors page, not on admin
    s4=Site(pw,d);s4.ctx.add_init_script('window.__FORCE_SPONSOR_POPUP=true;')
    p4=s4.page('sponsors.html',1800);ok('not shown on the Sponsors page',p4.locator('#spp').count()==0)
    s5=Site(pw,d,admin=True);s5.ctx.add_init_script('window.__FORCE_SPONSOR_POPUP=true;')
    p5=s5.page('admin/dashboard.html',1800);ok('not shown on admin pages',p5.locator('#spp').count()==0)
    # phone
    s6=Site(pw,d);s6.ctx.add_init_script('window.__FORCE_SPONSOR_POPUP=true;')
    m=s6.br.new_context(viewport={'width':375,'height':640});m.add_init_script('window.__FORCE_SPONSOR_POPUP=true;window.__DB='+json.dumps(d)+';')
    m.route('**/*supabase*.js',lambda r:r.fulfill(body=FAKE,content_type='application/javascript'))
    q=m.new_page();q.goto('http://127.0.0.1:8137/index.html');q.wait_for_timeout(1900)
    ok('phone: pop-up visible, X reachable, no sideways scroll',q.is_visible('#spp') and q.is_visible('#spp-x') and q.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    ok('phone: pop-up fits the screen (scrolls inside if needed)',q.evaluate('(()=>{const b=document.querySelector(".spp-box").getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight+1&&b.left>=0&&b.right<=innerWidth+1})()'))
    q.locator('.spp-box').screenshot(path='/tmp/spp_mob.png')
print('==',sum(R),'passed,',len(R)-sum(R),'failed')
