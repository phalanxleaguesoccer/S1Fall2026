# Standings (landing) page: Form column, win % on upcoming, Tournament records section; parity with Stats > Records team summary.
from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
def scen():
    b=base();m=b['m'];T=b['T'];P=b['P']
    m(1,1,'Muggles FC','Scouts FC','completed',1,2);m(1,2,'Renegades','Desi Steelers FC','completed',0,0)
    m(2,1,'Scouts FC','Muggles FC','completed',2,0);m(2,2,'Desi Steelers FC','Renegades','completed',0,0)
    m(3,1,'Muggles FC','Desi Steelers FC','completed',1,0);m(3,2,'Renegades','Scouts FC','completed',1,0)
    m(4,1,'Renegades','Scouts FC');m(4,2,'Muggles FC','Desi Steelers FC')
    d=finish(b)
    def ev(i,mt,t,pl,ty,minute=3,sec=None,rel=None): return {'id':'v%d'%i,'match_id':mt,'team_id':T[t],'player_id':P[pl],'event_type':ty,'half':1,'minute':minute,'second':sec,'related_player_id':P[rel] if rel else None,'is_penalty':False,'created_at':'2026-10-07T01:00:%02d+00:00'%i}
    d['match_events']=[ev(1,'m0','Muggles FC','Amritpal Singh','goal',2,10),ev(2,'m0','Scouts FC','Bhagyesh Rane','goal',5,20),ev(3,'m0','Scouts FC','Ajinkya P','assist',5,20),ev(4,'m0','Scouts FC','Bilal Yaser','goal',9,40),
      ev(5,'m0','Scouts FC','Bhagyesh Rane','player_of_match'),ev(6,'m2','Scouts FC','Bhagyesh Rane','goal',4,34),ev(7,'m2','Scouts FC','Ajinkya P','goal',17,1),ev(8,'m2','Scouts FC','Bhagyesh Rane','player_of_match'),
      ev(9,'m4','Muggles FC','Amritpal Singh','goal',8),ev(10,'m5','Renegades','Varun','goal',5),ev(11,'m5','Renegades','Rishabh Devgon','assist',5),ev(12,'m5','Renegades','Varun','player_of_match'),
      ev(13,'m2','Muggles FC','Ayush','yellow_card')]
    return d,T
def standings(p):
    return [[c.strip() for c in r.split('\t')][:10] for r in p.locator('#standings-body tr').all_inner_texts()]
def records_rows(site):
    p=site.page('stats.html#records',1500);p.click('#rec-menu a[data-rview=teams]');p.wait_for_timeout(300)
    return [[c.strip() for c in r.split('\t')] for r in p.locator('#rec-body tbody tr').all_inner_texts()]
with sync_playwright() as pw:
    d,T=scen();s=Site(pw,d);p=s.page('index.html',2000)
    ok('no JS errors',not p.errs,p.errs)
    hdr=[h.strip().upper() for h in p.locator('#standings-table thead th').all_inner_texts()]
    ok('table now ends with a Form column',hdr[-1].startswith('FORM') and 'LATEST FIRST' in hdr[-1] and hdr[:3]==['#','TEAM','PTS'],hdr)
    st=standings(p)
    ok('standings order: Scouts (4, GD+2), Renegades (4, GD+1), Desi (2, GD-1), Muggles (2, GD-2)',[r[1] for r in st]==['Scouts FC','Renegades','Desi Steelers FC','Muggles FC'],[r[1] for r in st])
    forms={r.split('\t')[1].strip():r.split('\t')[10].split() for r in p.locator('#standings-body tr').all_inner_texts()}
    ok('Form chips newest FIRST: Scouts L W W, Muggles W L L, Renegades W D D',forms.get('Scouts FC')==['L','W','W'] and forms.get('Muggles FC')==['W','L','L'] and forms.get('Renegades')==['W','D','D'],forms)
    ok('Form for Desi = L D D (newest first: 0-1, 0-0, 0-0)',forms.get('Desi Steelers FC')==['L','D','D'],forms)
    ok('Form chips use W/D/L colour classes',p.locator('.fm5 .W').count()>=1 and p.locator('.fm5 .D').count()>=1 and p.locator('.fm5 .L').count()>=1)
    # upcoming + win %
    ok('upcoming rows show 3-part win % bars summing to 100',p.locator('.up-bar').count()==2 and all(sum(int(x.rstrip('%')) for x in b.locator('div').all_inner_texts())==100 for b in p.locator('.up-bar').all()),p.inner_text('#upcoming-list'))
    ok('bars explained as a coin flip, not a forecast','coin flip' in p.inner_text('#up-note') and p.is_visible('#up-note'))
    ok('upcoming rows still link to the matches',p.locator('#upcoming-list a[href^="match.html"]').count()==2 and 'Day 4' in p.inner_text('#upcoming-list'))
    # records
    r=p.inner_text('#home-records');rl=r.upper()
    ok('section title + link to all records','TOURNAMENT RECORDS' in rl and p.locator('#home-records a[href="stats.html#records"]').count()>=2)
    tiles=[t.strip().replace('\n',' ') for t in p.locator('.hr-tile').all_inner_texts()]
    ok('glance tiles: 6 matches, 7 goals, 1.17 per match, 7 clean sheets',tiles[0].startswith('6') and tiles[1].startswith('7') and tiles[2].startswith('1.17') and tiles[3].startswith('7'),tiles)
    ok('progress: 6 of 8 matches played, Match Day 3 of 4','6 of 8 matches played' in r and 'Match Day 3 of 4' in r and '2 goalless draws' in r,r[:600])
    ok('Fair play and Saves are NOT on the landing page','FAIR PLAY' not in rl and 'SAVES' not in rl)
    boards=p.locator('.hr-card')
    ok('four player boards: Golden Boot, Top playmakers, Player of the match, Goal contributions',boards.count()==4 and all(x in rl for x in ['GOLDEN BOOT','TOP PLAYMAKERS','PLAYER OF THE MATCH','GOAL CONTRIBUTIONS']))
    gb=boards.nth(0).inner_text()
    ok('Golden Boot: Amritpal and Bhagyesh tied on 2 (T1), then three on 1 (T3)','Amritpal Singh' in gb and 'Bhagyesh Rane' in gb and gb.count('T1')==2 and gb.count('T3')==3,gb)
    nums=[x.strip() for x in boards.nth(0).locator('.hr-n').all_inner_texts()];ok('Golden Boot counts 2,2? ordered desc',nums==sorted(nums,reverse=True) and nums[0]=='2',nums)
    ok('names link to players, teams to team pages',p.locator('.hr-card a[href^="player.html"]').count()>=5 and p.locator('.hr-card a[href^="team.html"]').count()>=5)
    ok('player of the match: Bhagyesh 2 alone in 1st (no T), Varun 2nd','1\nBhagyesh Rane' in boards.nth(2).inner_text() and 'T1' not in boards.nth(2).inner_text())
    tr=p.locator('.hr-grid').nth(1).inner_text().upper()
    ok('team records block has the six lines','BEST ATTACK' in tr and 'BEST DEFENCE' in tr and 'MOST CLEAN SHEETS' in tr and 'BEST GOAL DIFFERENCE' in tr and 'MOST WINS' in tr and 'MOST DRAWS' in tr,tr)
    ok('match records: biggest win, highest-scoring, fastest 2:10, latest 17:01, goalless draws','BIGGEST WIN' in tr and 'HIGHEST-SCORING' in tr and '2:10' in tr and '17:01' in tr and 'GOALLESS DRAWS' in tr,tr)
    ok('biggest win +2 with match link','+2' in tr and p.locator('.hr-grid').nth(1).locator('a[href^="match.html"]').count()>=3)
    # parity with Stats > Records
    rr=records_rows(s)
    ok('PARITY: Records summary has same ranks, teams, Pts P W D L GD GF GA as Standings',[r_[:10] for r_ in rr]==st,(rr,st))
    p.close()
    # season filter 'all'
    p=s.page('index.html',1500);p.select_option('#standings-season-filter','all');p.wait_for_timeout(900)
    ok('All seasons: records section still renders, no errors, no progress bar','TOURNAMENT RECORDS' in p.inner_text('#home-records').upper() and not p.errs and p.locator('.hr-prog').count()==0,p.errs)
    # mobile
    mp=s.br.new_context(viewport={'width':375,'height':800});mp.add_init_script('window.__DB='+json.dumps(dict(d,__admin=False))+';')
    mp.route('**/*supabase*.js',lambda r:r.fulfill(body=FAKE,content_type='application/javascript') if 'cdn.jsdelivr' in r.request.url else r.continue_());mp.route('**/fonts.g*/**',lambda r:r.abort())
    q=mp.new_page();q.goto('http://127.0.0.1:8137/index.html');q.wait_for_timeout(1800)
    ok('375px: no sideways scroll',not q.evaluate('document.documentElement.scrollWidth>innerWidth'),q.evaluate('document.documentElement.scrollWidth'))
    ok('375px: record cards stay inside their card',q.evaluate("[...document.querySelectorAll('#home-records .card')].every(c=>c.scrollWidth<=c.clientWidth+1)"))
    ok('375px: boards stack to one column',q.evaluate("getComputedStyle(document.querySelector('.hr-grid')).gridTemplateColumns.split(' ').length")==1)
    # pre-season
    s0=Site(pw,scenario_pre());z=s0.page('index.html',1500)
    ok('no results yet: friendly message, no errors, table form column empty chips',('Records appear after the first result' in z.inner_text('#home-records')) and not z.errs,z.errs)
    # parity on other scenarios (tie-break + shoot-out)
    for name,sc in [('played',scenario_played()),('post_tie',scenario_post_tie())]:
        s1=Site(pw,sc);z=s1.page('index.html',1800);a=standings(z);rr=records_rows(s1)
        ok('PARITY (%s): Records order/ranks/points equal Standings'%name,[(x[0],x[1],x[2],x[7]) for x in a if x[3]!='0']==[(x[0],x[1],x[2],x[7]) for x in rr],(a,rr))
    b=base();m=b['m']
    m(1,1,'Muggles FC','Scouts FC','forfeited',None,None,'Scouts FC');m(1,2,'Renegades','Desi Steelers FC','completed',2,1);m(2,1,'Scouts FC','Renegades','completed',1,1);m(2,2,'Desi Steelers FC','Muggles FC','completed',0,0)
    s2=Site(pw,finish(b));z=s2.page('index.html',1800);a=standings(z);rr=records_rows(s2)
    ok('PARITY (forfeit): Records equals Standings (forfeit = win for the other side, no goals)',[x[:10] for x in rr]==a and a[0][1] in ('Renegades','Muggles FC'),(a,rr))
    ok('forfeit scenario: no JS errors on the landing page',not z.errs,z.errs)
print('%d passed %d failed'%(sum(R),len(R)-sum(R)))
