# Matches page: Recent / Previous / Upcoming / All tabs, weekly default rule (Eastern), team filter, All ordering.
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
def scen(day4=False):
    b=base();m=b['m'];T=b['T'];P=b['P']
    m(1,1,'Muggles FC','Scouts FC','completed',1,2);m(1,2,'Renegades','Desi Steelers FC','completed',0,0)
    m(2,1,'Scouts FC','Muggles FC','completed',2,0);m(2,2,'Desi Steelers FC','Renegades','completed',0,0)
    m(3,1,'Muggles FC','Desi Steelers FC','completed',1,0);m(3,2,'Renegades','Scouts FC','completed',1,0)
    if day4: m(4,1,'Renegades','Scouts FC','completed',0,1);m(4,2,'Muggles FC','Desi Steelers FC','completed',2,2)
    else: m(4,1,'Renegades','Scouts FC');m(4,2,'Muggles FC','Desi Steelers FC')
    d=finish(b)
    def ev(i,mt,t,pl,ty,minute=3,rel=None): return {'id':'v%d'%i,'match_id':mt,'team_id':T[t],'player_id':P[pl],'event_type':ty,'half':1,'minute':minute,'second':None,'related_player_id':P[rel] if rel else None,'is_penalty':False,'created_at':'2026-10-07T01:00:%02d+00:00'%i}
    d['match_events']=[ev(1,'m0','Muggles FC','Amritpal Singh','goal',2),ev(2,'m0','Scouts FC','Bhagyesh Rane','goal',5),ev(3,'m0','Scouts FC','Ajinkya P','assist',5),ev(4,'m0','Scouts FC','Bilal Yaser','goal',9),
      ev(5,'m2','Scouts FC','Bhagyesh Rane','goal',4),ev(6,'m2','Muggles FC','Bilal Yaser','own_goal',8)]
    d['match_appearances']=[{'id':'a1','match_id':'m0','team_id':T['Muggles FC'],'player_id':P['Ayush'],'status':'rested','started':False,'is_captain':False,'captain_stand_in':False,'absent_reason':None}]
    return d,T
def openat(pw_ctx_site,iso,path='matches.html',day4=False,vw=None):
    pass
with sync_playwright() as pw:
    d,T=scen();s=Site(pw,d)
    def at(iso,path='matches.html',wait=900):
        p=s.ctx.new_page();errs=[];p.on('pageerror',lambda e:errs.append(str(e)))
        p.clock.set_fixed_time(iso);p.goto('http://127.0.0.1:8137/'+path);p.wait_for_timeout(wait);p.errs=errs;return p
    tabs=lambda p:[x.split(' ·')[0] for x in p.locator('#mt-tabs button').all_inner_texts()]
    on=lambda p:p.locator('#mt-tabs button.on').inner_text().split(' ·')[0]
    # --- weekly rule, boundaries in Eastern time (EDT until Nov 1, EST after)
    cases=[('Mon Oct 26 22:00 EDT','2026-10-27T02:00:00Z','Upcoming'),('Tue Oct 27 20:30 EDT','2026-10-28T00:30:00Z','Upcoming'),('Tue Oct 27 20:31 EDT','2026-10-28T00:31:00Z','Recent'),
           ('Wed Oct 28 09:00','2026-10-28T13:00:00Z','Recent'),('Thu Oct 29 23:59 EDT','2026-10-30T03:59:00Z','Recent'),('Fri Oct 30 00:00 EDT','2026-10-30T04:00:00Z','Upcoming'),
           ('Sat Oct 31','2026-10-31T16:00:00Z','Upcoming'),('Sun Nov 1 noon EST','2026-11-01T17:00:00Z','Upcoming'),
           ('Tue Nov 3 20:30 EST','2026-11-04T01:30:00Z','Upcoming'),('Tue Nov 3 20:31 EST','2026-11-04T01:31:00Z','Recent'),('Thu Nov 5 23:59 EST','2026-11-06T04:59:00Z','Recent'),('Fri Nov 6 00:00 EST','2026-11-06T05:00:00Z','Upcoming')]
    for name,iso,exp in cases:
        p=at(iso);ok('%s -> default %s'%(name,exp),on(p)==exp and p.locator('#mt-tabs button').first.inner_text().startswith(exp) and not p.errs,(on(p),p.errs));p.close()
    p=at('2026-10-27T02:00:00Z')
    ok('Upcoming default: order Upcoming, Recent, Previous, All',tabs(p)==['Upcoming','Recent','Previous','All'],tabs(p))
    ok('Recent tab labelled with its day','Recent · Day 3' in p.locator('#mt-tabs').inner_text())
    ok('explanation line (Upcoming window)','Friday 12:00 AM to Tuesday 8:30 PM' in p.inner_text('#mt-why'))
    t=p.inner_text('#days-list')
    ok('next-kickoff banner with countdown and NEXT badge','NEXT KICKOFF' in t.upper() and 'until kickoff' in t.lower() and 'NEXT' in p.locator('.mt-badge.next').inner_text() and 'RENEGADES' in p.locator('.mt-next').inner_text().upper(),t[:300])
    ok('countdown is 23h 0m on Mon 10pm','23h 0m' in p.locator('#mt-cd').inner_text(),p.locator('#mt-cd').inner_text())
    ok('upcoming lists only Day 4 (2 matches)',p.locator('.match-row').count()==2 and 'MATCH DAY 4' in p.locator('.mt-dh').first.inner_text().upper())
    ok('scheduled pill, Match page link, Head to head link to Rivalry',p.locator('.match-row .pill.scheduled').count()==2 and p.locator('a[href^="stats.html#rivalry/%s/%s"]'%(T['Renegades'],T['Scouts FC'])).count()==1)
    p.click('#mt-tabs button[data-mt-tab=recent]');p.wait_for_timeout(200)
    ok('Recent: one match day (Day 3) with LATEST badge, 2 results',p.locator('.mt-dh h2').count()==1 and 'MATCH DAY 3' in p.locator('.mt-dh h2').inner_text().upper() and 'LATEST' in p.locator('.mt-badge.latest').inner_text() and p.locator('.match-row').count()==2)
    ok('hash updated to #recent',p.evaluate('location.hash')=='#recent')
    ok('Recent is not the default here so no explanation line',p.inner_text('#mt-why').strip()=='')
    p.click('#mt-tabs button[data-mt-tab=previous]');p.wait_for_timeout(200)
    hs=[x.upper() for x in p.locator('.mt-dh h2').all_inner_texts()]
    ok('Previous: Day 2 then Day 1 (newest first), latest day excluded',len(hs)==2 and 'DAY 2' in hs[0] and 'DAY 1' in hs[1],hs)
    # result row content
    ok('results show scores, Full time pill, Match report link',p.locator('.match-row .pill.completed').count()==4 and '1 – 2' in p.inner_text('#days-list') and 'Match report' in p.inner_text('#days-list'))
    t=p.inner_text('#days-list')
    ok('scorer with assist and own goal listed','Bhagyesh Rane' in t and 'Ajinkya P' in t and '(og)' in t and 'Goalless draw' in t,t)
    ok('event markers use goal/assist/og classes',p.locator('.mt-ev .evm.goal').count()>=3 and p.locator('.mt-ev .evm.assist').count()>=1 and p.locator('.mt-ev .evm.og').count()==1)
    ok('rested count kept on the row','Rested: Muggles FC 1' in t,t)
    ok('no nested links',p.locator('a a').count()==0)
    p.locator('.match-row').first.locator('.pill').click();p.wait_for_timeout(500)
    ok('clicking a row (not a link) opens the match','match.html?id=' in p.url,p.url)
    # --- team filter on every tab, shared across tabs
    p=at('2026-10-27T02:00:00Z')
    p.select_option('#mt-team',label='Scouts FC');p.wait_for_timeout(200)
    ok('Upcoming + Scouts: only their Day 4 match, banner follows',p.locator('.match-row').count()==1 and 'SCOUTS' in p.locator('.mt-next').inner_text().upper() and 'RENEGADES V SCOUTS' in p.locator('.mt-next .t').inner_text().replace('\n',' ').upper(),p.inner_text('#days-list')[:200])
    p.click('#mt-tabs button[data-mt-tab=recent]');p.wait_for_timeout(200)
    ok('team choice persists across tabs and filters Recent',p.locator('#mt-team').input_value()==T['Scouts FC'] and p.locator('.match-row').count()==1 and 'Renegades' in p.inner_text('.match-row') and 'Scouts FC' in p.inner_text('.match-row'))
    ok('Win/Loss pill relative to the chosen team (Scouts lost 0-1 at Renegades)',p.locator('.match-row .pill.L').count()==1,p.inner_text('.match-row')[:120])
    p.click('#mt-tabs button[data-mt-tab=previous]');p.wait_for_timeout(200)
    ok('Previous + Scouts: both earlier matches, both Wins',p.locator('.match-row').count()==2 and p.locator('.match-row .pill.W').count()==2,[x.inner_text()[:40] for x in p.locator('.match-row .pill').all()])
    p.close()
    # --- All tab
    p=at('2026-10-27T02:00:00Z','matches.html#all')
    ok('#all opens the All tab',on(p)=='All' and 'ORDER BY DATE' in p.inner_text('#days-list').upper())
    hs=[x.upper() for x in p.locator('.mt-dh h2').all_inner_texts()]
    ok('default Descending: Day 4 first … Day 1 last',len(hs)==4 and 'DAY 4' in hs[0] and 'DAY 1' in hs[3],hs)
    ok('exactly two order options: Ascending / Descending',p.locator('[data-mt-order]').all_inner_texts()==['Ascending ↑','Descending ↓'] and p.locator('[data-mt-order=desc].on').count()==1)
    p.click('[data-mt-order=asc]');p.wait_for_timeout(200)
    hs=[x.upper() for x in p.locator('.mt-dh h2').all_inner_texts()]
    ok('Ascending: Day 1 first … Day 4 last',len(hs)==4 and 'DAY 1' in hs[0] and 'DAY 4' in hs[3] and p.locator('[data-mt-order=asc].on').count()==1,hs)
    first=p.locator('.match-row').first.inner_text()
    ok('ascending also orders matches within a day (M1 first)','M1 ·' in first,first[:80])
    p.select_option('#mt-day','2');p.wait_for_timeout(200)
    ok('filter by match day',p.locator('.mt-dh h2').count()==1 and 'DAY 2' in p.locator('.mt-dh h2').inner_text().upper())
    p.select_option('#mt-day','all');p.select_option('#mt-status','up');p.wait_for_timeout(200)
    ok('status filter: not played yet -> Day 4 only',p.locator('.match-row').count()==2 and p.locator('.mt-dh h2').count()==1)
    p.select_option('#mt-status','done');p.wait_for_timeout(200)
    ok('status filter: played -> 6 matches',p.locator('.match-row').count()==6)
    p.select_option('#mt-status','all');p.select_option('#mt-team',label='Muggles FC');p.wait_for_timeout(200)
    t=p.inner_text('#days-list')
    ok('team summary: Muggles 3 played 1W 0D 2L goals 3-3? (1-2,0-2,1-0) = GF 2 GA 4, 2 to play? (1 to play)','3 played' in t and '1W' in t and '0D' in t and '2L' in t and 'goals 2–4' in t and '1 to play' in t,t[:300])
    ok('no JS errors on All',not p.errs,p.errs)
    p.close()
    # --- awaiting result
    p=at('2026-10-28T01:05:00Z')   # Tue Oct 27 9:05 PM EDT: Day 4 M1 kicked off at 9:00, no result yet
    p.click('#mt-tabs button[data-mt-tab=upcoming]');p.wait_for_timeout(200)
    ok('past-kickoff match with no result: Awaiting result pill and banner',p.locator('.match-row .pill.wait').count()>=1 and 'AWAITING RESULTS' in p.locator('.mt-next .k').inner_text().upper(),p.inner_text('#days-list')[:200])
    p.close()
    # --- no clock override: real now -> page fine; mobile
    mp=s.br.new_context(viewport={'width':375,'height':800});mp.add_init_script('window.__DB='+json.dumps(dict(d,__admin=False))+';')
    mp.route('**/*supabase*.js',lambda r:r.fulfill(body=FAKE,content_type='application/javascript') if 'cdn.jsdelivr' in r.request.url else r.continue_());mp.route('**/fonts.g*/**',lambda r:r.abort())
    for h in ['upcoming','recent','previous','all']:
        q=mp.new_page();q.clock.set_fixed_time('2026-10-27T02:00:00Z');q.goto('http://127.0.0.1:8137/matches.html#'+h);q.wait_for_timeout(900)
        ok('375px #%s: no sideways scroll, all within cards'%h,not q.evaluate('document.documentElement.scrollWidth>innerWidth') and q.evaluate("[...document.querySelectorAll('#days-list .card')].every(c=>c.scrollWidth<=c.clientWidth+1)"),q.evaluate('document.documentElement.scrollWidth'));q.close()
# --- fallbacks
with sync_playwright() as pw:
    d,T=scen(day4=True);s=Site(pw,d)
    p=s.ctx.new_page();p.clock.set_fixed_time('2026-10-27T02:00:00Z');p.goto('http://127.0.0.1:8137/matches.html');p.wait_for_timeout(900)
    on=lambda p:p.locator('#mt-tabs button.on').inner_text().split(' ·')[0]
    ok('all matches played: default Recent even in the Upcoming window',on(p)=='Recent')
    p.click('#mt-tabs button[data-mt-tab=upcoming]');p.wait_for_timeout(200)
    ok('season complete: Upcoming says nothing left',('No more matches' in p.inner_text('#days-list')),p.inner_text('#days-list')[:100])
    b=base();m=b['m'];m(1,1,'Muggles FC','Scouts FC');m(1,2,'Renegades','Desi Steelers FC');s2=Site(pw,finish(b))
    q=s2.ctx.new_page();q.clock.set_fixed_time('2026-10-29T16:00:00Z');q.goto('http://127.0.0.1:8137/matches.html');q.wait_for_timeout(900)
    ok('no results yet: Upcoming even on a Thursday (Recent window)',on(q)=='Upcoming' and q.locator('#mt-tabs button').first.inner_text()=='Upcoming')
    q.click('#mt-tabs button[data-mt-tab=recent]');q.wait_for_timeout(200)
    ok('Recent with no results: friendly text','No results yet' in q.inner_text('#days-list'))
print('%d passed %d failed'%(sum(R),len(R)-sum(R)))
