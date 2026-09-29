import json
from harness import *; from fixtures import *
serve()
R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
with sync_playwright() as pw:
    # ---- public viewer ----
    db=scenario_auction();db['auction_state']=[{'season_id':'season1','current_player_id':'p4','updated_at':'x'}]
    s=Site(pw,db);p=s.page('auction.html',1200)
    ok('viewer: no JS errors',not p.errs,p.errs)
    ok('viewer: sees on-the-block player','Ayush' in p.inner_text('#on-block'))
    ok('viewer: no admin controls visible',not p.is_visible('#wheel-card') and not p.is_visible('#sell-panel'))
    t=p.inner_text('#team-grid')
    ok('viewer: 4 teams, owners at 0 pts, 200 left','200' in t and t.count('(owner)')==4 and t.count('0 pts')>=4,t[:200])
    ok('viewer: Round 1 list excludes owners (5 players)',p.locator('#round1 .chip').count()==5,p.locator('#round1 .chip').count())
    ok('nav: Auction link + breadcrumb',p.locator('nav.main-nav a[href="auction.html"]').count()==1 and p.locator('nav.breadcrumbs').count()==1)
    # ---- admin flow ----
    sa=Site(pw,scenario_auction(),admin=True);p=sa.page('auction.html',1200)
    ok('admin: controls visible',p.is_visible('#wheel-card'))
    ok('admin: wheel pool = 5 non-owners',p.evaluate('wheelNames.length')==5 and not any(n in p.evaluate('wheelNames') for n in ['Nasiq','Amritpal Singh','Bhagyesh Rane','Varun']),p.evaluate('wheelNames'))
    p.click('#btn-spin');p.wait_for_timeout(6200)
    picked=p.evaluate("(function(){var n=wheelNames.length,seg=360/n,a=((-wheelAngle)%360+360)%360;return wheelNames[Math.floor(a/seg)];})()")
    onblock=p.inner_text('#on-block')
    ok('wheel: player under pointer == player put on the block',picked in onblock,(picked,onblock))
    ok('wheel: state published for viewers',p.evaluate("__DB.auction_state.length")==1 and p.evaluate("__DB.auction_state[0].current_player_id")!=None)
    pid=p.evaluate("__DB.auction_state[0].current_player_id")
    # overspend blocked
    p.select_option('#sell-team',index=0);p.fill('#sell-price','250');p.click('#btn-sold');p.wait_for_timeout(400)
    ok('sell: price over budget rejected','Not enough points' in p.inner_text('#sell-msg') and p.evaluate("__DB.team_season_rosters.length")==4,p.inner_text('#sell-msg'))
    p.fill('#sell-price','');p.click('#btn-sold');p.wait_for_timeout(300)
    ok('sell: empty price rejected','Enter the sold price' in p.inner_text('#sell-msg'))
    p.fill('#sell-price','75');p.click('#btn-sold');p.wait_for_timeout(800)
    rows=p.evaluate("__DB.team_season_rosters")
    ok('sell: saved to roster with price, not owner',len(rows)==5 and rows[-1]['auction_price']==75 and rows[-1]['is_owner']==False and rows[-1]['player_id']==pid,rows[-1])
    tid=rows[-1]['team_id'];tname=[t for t in p.evaluate("__DB.teams") if t['id']==tid][0]['name']
    ok('sell: team budget now 125 left / 75 spent, feed shows sale', '125' in p.inner_text('#team-grid') and 'SOLD' in p.inner_text('#feed') and '75 pts' in p.inner_text('#feed'),p.inner_text('#feed'))
    ok('sell: player leaves pool (4 left) and block cleared',p.locator('#round1 .chip').count()==4 and 'Waiting' in p.inner_text('#on-block'))
    # second spin -> unsold -> round 2
    p.click('#btn-spin');p.wait_for_timeout(6200);pid2=p.evaluate("__DB.auction_state[0].current_player_id")
    p.click('#btn-unsold');p.wait_for_timeout(800)
    ok('unsold: recorded as round 1 and shown in Round 2 section',p.evaluate("__DB.auction_unsold")[0]['round']==1 and pid2 and p.locator('#round2 .chip').count()==1 and p.locator('#round1 .chip').count()==3,p.evaluate("__DB.auction_unsold"))
    ok('unsold: appears in feed as UNSOLD -> Round 2','UNSOLD' in p.inner_text('#feed') and 'Round 2' in p.inner_text('#feed'))
    # wheel round 2 pool
    p.select_option('#wheel-round','2');p.wait_for_timeout(300)
    ok('wheel: Round 2 pool contains only the unsold player',p.evaluate('wheelNames.length')==1,p.evaluate('wheelNames'))
    p.select_option('#wheel-round','1');p.wait_for_timeout(300)
    # undo last (the unsold)
    p.click('#btn-undo-last');p.wait_for_timeout(800)
    ok('undo last: reverses the unsold, player back in Round 1 pool',len(p.evaluate("__DB.auction_unsold"))==0 and p.locator('#round1 .chip').count()==4,p.evaluate("__DB.auction_unsold"))
    # undo sale via feed button (dialog auto-accepted)
    p.locator('[data-undo-sale]').first.click();p.wait_for_timeout(800)
    ok('undo sale: roster row removed, budget restored, player back in pool',p.evaluate("__DB.team_season_rosters.length")==4 and p.locator('#round1 .chip').count()==5 and p.inner_text('#team-grid').count('200 pts left')==4,p.inner_text('#team-grid')[:150])
    ok('undo: owners cannot be undone (no undo buttons for owners)',p.locator('[data-undo-sale]').count()==0)
    ok('admin flow: no JS errors',not [e for e in p.errs if 'DIALOG' not in e],p.errs)
    # ---- double sale guard + budget arithmetic across sales ----
    p.evaluate("""(async()=>{STATE={current_player_id:'p4'};})()""")
    # ---- profile/team/teams pages reflect the sale ----
    d=scenario_auction();d['team_season_rosters'].append({'id':'rx','season_id':'season1','team_id':'t4','player_id':'p4','is_owner':False,'auction_price':60,'jersey_number':None,'sold_at':'2026-10-02T00:00:00Z'})
    s2=Site(pw,d)
    p=s2.page('player.html?id=p4');ok('player page: shows team + "sold for 60 pts"','Desi Steelers FC' in p.inner_text('#player-team') and 'sold for 60 pts' in p.inner_text('#player-team'),p.inner_text('#player-team'))
    p=s2.page('player.html?id=p0');ok('player page: owner shows "Team owner"','Team owner' in p.inner_text('#player-team'),p.inner_text('#player-team'))
    p=s2.page('team.html?id=t4');ok('team page: sold player appears in squad with price','Ayush' in p.inner_text('#roster-grid') and '60 pts' in p.inner_text('#roster-grid'),p.inner_text('#roster-grid'))
    p=s2.page('teams.html');tt=p.inner_text('#teams-grid');ok('teams page: squad size + points left (2 players, 140 left for Desi)','2 players' in tt and '140 pts left' in tt and '200 pts left' in tt,tt)
    p=s2.page('players.html');ok('players page: sold player now listed under Desi Steelers FC','Desi Steelers FC' in p.inner_text('#players-grid'))
    # ---- migration missing ----
    d=scenario_auction();d['__missing']=['x'];s3=Site(pw,d)
print(f"\n{sum(R)} passed, {len(R)-sum(R)} failed")
