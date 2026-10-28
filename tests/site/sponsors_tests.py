# Sponsors band on the landing page: logos load, links, Robinson highlight, layout on desktop and phone.
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();d=finish(b)
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('index.html',1500)
    ok('no JS errors',not p.errs,p.errs)
    t=p.inner_text('#sponsors')
    ok('heading and both sponsors shown','PROUDLY SUPPORTED BY' in t.upper() and 'TROPICAL SMOOTHIE CAFE' in t.upper() and 'EASEOURTRIP' in t.upper(),t)
    ok('Tropical title mentions Robinson','Tropical Smoothie Cafe – Robinson'.upper() in t.upper() and 'OUR ROBINSON LOCATION' in t.upper(),t)
    ok('address and phone shown','322 McHolme Dr' in t and 'Pittsburgh, PA 15275' in t and '(412) 505-8126' in t,t)
    hr=lambda sel:p.eval_on_selector_all(sel,'els=>els.map(e=>e.href)')
    th=hr('#sponsor-tropical a')
    ok('Tropical store links go to the Robinson page','https://locations.tropicalsmoothiecafe.com/pa/pittsburgh/322-mcholme-dr' in th and th.count('https://locations.tropicalsmoothiecafe.com/pa/pittsburgh/322-mcholme-dr')==2,th)
    ok('directions + tel links','google.com/maps/dir' in ' '.join(th) and any(x.startswith('tel:+14125058126') for x in th),th)
    eh=hr('#sponsor-easeourtrip a')
    ok('EaseOurTrip links go to its website',eh==['https://www.easeourtrip.com/']*2,eh)
    ok('external links open in a new tab safely',p.eval_on_selector_all('#sponsors a[href^=http]','els=>els.every(e=>e.target==="_blank"&&/noopener/.test(e.rel))'))
    ok('both logos loaded (not broken)',p.eval_on_selector_all('#sponsors img','els=>els.length===2&&els.every(i=>i.complete&&i.naturalWidth>50)'))
    ok('no horizontal scroll on desktop',p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    m=s.br.new_context(viewport={'width':375,'height':800});m.add_init_script('window.__DB='+__import__('json').dumps(d)+';')
    m.route('**/*supabase*.js',lambda r:r.fulfill(body=FAKE,content_type='application/javascript'))
    q=m.new_page();q.goto('http://127.0.0.1:8137/index.html');q.wait_for_timeout(1800)
    ok('phone: no horizontal scroll and sponsors visible',q.evaluate('document.documentElement.scrollWidth<=innerWidth') and q.is_visible('#sponsor-tropical') and q.is_visible('#sponsor-easeourtrip'))
    q.locator('#sponsors').screenshot(path='/tmp/sp_mob.png')
    p.locator('#sponsors').screenshot(path='/tmp/sp_desk.png')
print('==',sum(R),'passed,',len(R)-sum(R),'failed')
