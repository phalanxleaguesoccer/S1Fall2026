from harness import *; from fixtures import *
Site.closed=True
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
d=scenario_auction();d['team_season_rosters'].append({'id':'y1','season_id':'season1','team_id':'t4','player_id':'p4','is_owner':False,'auction_price':60,'jersey_number':None,'sold_at':'2026-10-02T00:00:00Z'})
with sync_playwright() as pw:
    for adm in (True,False):
        p=Site(pw,d,admin=adm).page('auction.html',1500);tag='admin' if adm else 'visitor'
        ok(tag+': no JS errors',not p.errs,p.errs)
        ok(tag+': wheel/on-block/on-wheel/round2/spin/reset/undo hidden',not any(p.is_visible(x) for x in ('#wheel','#on-block','#round1','#round2','#btn-spin','#btn-reset','#btn-undo-last','#w-hub','[data-undo-sale]','#pop')))
        ok(tag+': budgets + feed visible, banner shown',p.is_visible('#team-grid') and p.is_visible('#feed') and 'completed' in p.inner_text('#closed-banner') and 'Ayush' in p.inner_text('#feed'))
        ok(tag+': clicking where the wheel was does nothing',p.evaluate("document.querySelector('#wheel').click(), __DB.auction_state.length")==0)
    s=Site(pw,d)
    q=s.page('player.html?id=p4',1500)
    ok('profile header line',q.inner_text('#player-team')=='Plays for Desi Steelers FC : Auction sold for 60 pts',q.inner_text('#player-team'))
    q.click('#history-toggle')
    for m in ('seasons','matches'):
        q.select_option('#history-mode',m);q.wait_for_timeout(300)
        ok('auction history visible in '+m+' filter','sold for 60 pts' in q.inner_text('#auction-history'))
    ok('season table has Bought by / Sold for','60 pts' in q.inner_text('#career-by-season-body') and 'Desi Steelers FC' in q.inner_text('#career-by-season-body'))
    ok('owner profile',s.page('player.html?id=p0',1200).inner_text('#player-team')=='Plays for Desi Steelers FC : Team owner')
print(sum(R),'passed',len(R)-sum(R),'failed')
