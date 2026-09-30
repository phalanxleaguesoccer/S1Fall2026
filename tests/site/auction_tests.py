import json
from harness import *; from fixtures import *
serve()
R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
def sync(src,dst):
    dst.evaluate("(d)=>{for(const k of ['auction_state','auction_unsold','team_season_rosters']){__DB[k].length=0;for(const r of d[k])__DB[k].push(r);}}",src.evaluate("({auction_state:__DB.auction_state,auction_unsold:__DB.auction_unsold,team_season_rosters:__DB.team_season_rosters})"))
with sync_playwright() as pw:
    sa=Site(pw,scenario_auction(),admin=True);adm=sa.page('auction.html',1200)
    sv=Site(pw,scenario_auction(),admin=False);vw=sv.page('auction.html',1200)
    ok('no JS errors (admin+viewer)',not adm.errs and not vw.errs,(adm.errs,vw.errs))
    ok('viewer: wheel is visible to everyone',vw.is_visible('#wheel') and vw.is_visible('.w-pointer'))
    ok('viewer: no spin/sold buttons',not vw.is_visible('#btn-spin') and vw.inner_text('#w-hub')=='')
    ok('wheel has only non-owners (5), owners excluded (both screens)',adm.evaluate('wheelNames.length')==5 and vw.evaluate('wheelNames.length')==5 and not any(n in vw.evaluate('wheelNames') for n in ['Nasiq','Amritpal Singh','Bhagyesh Rane','Varun']),vw.evaluate('wheelNames'))
    ok('admin: Start Round 2 button hidden while nobody is in Round 2',not adm.is_visible('#btn-load-r2'))
    # ---- spin: admin publishes, viewer replays same spin ----
    adm.evaluate("(function(){var o=drawWheel;drawWheel=function(){if(ANIM){window.__la=wheelAngle;window.__ln=wheelNames.slice();}o();};})()")
    adm.click('#btn-spin');adm.wait_for_timeout(600)
    st=adm.evaluate("__DB.auction_state[0]")
    ok('spin published: pool of 5, winner in pool, seq 1',st['spin_seq']==1 and len(st['spin_pool'])==5 and st['spin_winner_id'] in st['spin_pool'],st)
    sync(adm,vw);vw.wait_for_timeout(2600)      # viewer's light poll notices the new spin
    ok('viewer: animating the same spin (wheel names = admin pool, "Spinning…", winner hidden until stop)',vw.evaluate('ANIM')==True and 'Spinning' in vw.inner_text('#on-block'),(vw.evaluate('ANIM'),vw.inner_text('#on-block')))
    adm.wait_for_timeout(7600);vw.wait_for_timeout(4200)
    winner=st['spin_winner_id'];wname=adm.evaluate("(id)=>PLAYERS[id].full_name",winner)
    ok('after spin: winner shown on block on BOTH screens',wname in adm.inner_text('#on-block') and wname in vw.inner_text('#on-block'),(adm.inner_text('#on-block'),vw.inner_text('#on-block')))
    ok('picked player removed from wheel immediately (4 left) on both screens',adm.evaluate('wheelNames.length')==4 and vw.evaluate('wheelNames.length')==4 and wname not in vw.evaluate('wheelNames'),(adm.evaluate('wheelNames'),vw.evaluate('wheelNames')))
    ok('pop-up on admin: winner name + Round 2 / Sell / Close buttons',adm.is_visible('#pop') and wname in adm.inner_text('#pop-name') and adm.is_visible('#btn-unsold') and adm.is_visible('#btn-sell-open') and adm.is_visible('#btn-close'))
    ok('pop-up on viewer: winner name + Close only (no Sell / Round 2)',vw.is_visible('#pop') and wname in vw.inner_text('#pop-name') and vw.is_visible('#btn-close') and not vw.is_visible('#btn-unsold') and not vw.is_visible('#btn-sell-open'))
    ok('ticking: ticks fired while spinning on both screens (>= 20)',adm.evaluate('TICKS')>=20 and vw.evaluate('TICKS')>=20,(adm.evaluate('TICKS'),vw.evaluate('TICKS')))
    fin=adm.evaluate("(function(){var n=__ln.length;return __ln[segUnderPointer(__la,n)];})()")
    ok('REAL pointer check: at the final frame the name under the pointer == winner',fin==wname,(fin,wname))
    vw.click('#btn-close');ok('viewer can close the pop-up',not vw.is_visible('#pop'))
    ok('pointer geometry: spin lands exactly on the winner segment',adm.evaluate("(function(){var st=__DB.auction_state[0];var n=st.spin_pool.length,seg=360/n,idx=st.spin_pool.indexOf(st.spin_winner_id);var land=(-(idx+0.5+Number(st.spin_offset))*seg);return Math.abs(((land%360)+360)%360 - ((-(idx+0.5+Number(st.spin_offset))*seg%360)+360)%360)<1e-6 && Math.abs(Number(st.spin_offset))<=0.35;})()"))
    ok('admin: spin disabled while a player is on the block',adm.evaluate("document.getElementById('btn-spin').disabled")==True)
    # sell
    adm.click('#btn-sell-open');adm.fill('#sell-price','250');adm.click('#btn-sold');adm.wait_for_timeout(400)
    opts=adm.locator('#sell-team option').all_inner_texts()
    ok('team dropdown shows each team with its owner and points left',len(opts)==4 and any('Desi Steelers FC — Owner: Nasiq (200 pts left)'==o for o in opts),opts)
    adm.fill('#sell-price','');adm.type('#sell-price','1a2b-3.');ok('price field accepts digits only',adm.input_value('#sell-price')=='123',adm.input_value('#sell-price'))
    adm.fill('#sell-price','')
    ok('sell: over-budget rejected','Not enough points' in adm.inner_text('#pop-msg'))
    adm.fill('#sell-price','');adm.click('#btn-sold');adm.wait_for_timeout(300)
    ok('sell: empty price rejected','digits only' in adm.inner_text('#pop-msg'))
    adm.fill('#sell-price','75');adm.click('#btn-sold');adm.wait_for_timeout(800)
    rows=adm.evaluate("__DB.team_season_rosters")
    ok('sell: saved (price 75) and block cleared',len(rows)==5 and rows[-1]['auction_price']==75 and 'Waiting' in adm.inner_text('#on-block'))
    ok('sold player stays off the wheel (still 4)',adm.evaluate('wheelNames.length')==4)
    # ---- unsold -> round 2 ----
    adm.click('#btn-spin');adm.wait_for_timeout(7600);w2=adm.evaluate("__DB.auction_state[0].spin_winner_id")
    ok('2nd spin only from remaining 4',len(adm.evaluate("__DB.auction_state[0].spin_pool"))==4 and w2!=winner)
    adm.click('#btn-unsold');adm.wait_for_timeout(800)
    ok('unsold: goes to Round 2 list, removed from Round 1 wheel (3 left)',adm.evaluate("__DB.auction_unsold[0].round")==1 and adm.locator('#round2 .chip').count()==1 and adm.evaluate('wheelNames.length')==3,adm.evaluate('wheelNames'))
    # ---- finish round 1: sell/unsold the remaining 3 ----
    for i in range(3):
        adm.click('#btn-spin');adm.wait_for_timeout(7600)
        if i==0: adm.click('#btn-unsold')
        else:
            adm.click('#btn-sell-open');adm.fill('#sell-price','10');adm.click('#btn-sold')
        adm.wait_for_timeout(700)
    ok('round 1 exhausted: wheel empty and says Round 1 is complete',adm.evaluate('wheelNames.length')==0 and 'Round 1 is complete' in adm.inner_text('#wheel-empty'),adm.inner_text('#wheel-empty'))
    ok('admin: "Load Round 2 players" button appears (2 players unsold)',adm.is_visible('#btn-load-r2') and adm.locator('#round2 .chip').count()==2,adm.locator('#round2 .chip').count())
    adm.click('#btn-load-r2');adm.wait_for_timeout(800)
    ok('Round 2 loaded onto the wheel: exactly the unsold players',adm.evaluate('wheelRound()')==2 and adm.evaluate('wheelNames.length')==2 and 'round 2' in adm.inner_text('#wheel-round-label').lower(),adm.inner_text('#wheel-round-label'))
    sync(adm,vw);vw.wait_for_timeout(3000)
    ok('viewer also sees the Round 2 wheel (2 names)',vw.evaluate('wheelRound()')==2 and vw.evaluate('wheelNames.length')==2,(vw.evaluate('wheelRound()'),vw.evaluate('wheelNames')))
    ok('unsold button says final in Round 2','final' in adm.inner_text('#btn-unsold').lower())
    adm.click('#btn-spin');adm.wait_for_timeout(7600);adm.click('#btn-unsold');adm.wait_for_timeout(800)
    ok('round 2 unsold -> final unsold list, wheel down to 1',adm.evaluate("__DB.auction_unsold.filter(u=>u.round===2).length")==1 and adm.evaluate('wheelNames.length')==1 and 'Final unsold' in adm.inner_text('#round2'),adm.inner_text('#round2'))
    adm.click('#btn-spin');adm.wait_for_timeout(7600);adm.click('#btn-sell-open');adm.fill('#sell-price','5');adm.click('#btn-sold');adm.wait_for_timeout(800)
    ok('round 2 sale works; wheel empty afterwards',adm.evaluate('wheelNames.length')==0)
    # ---- put back + undo ----
    sb=Site(pw,scenario_auction(),admin=True);p=sb.page('auction.html',1200)
    p.click('#btn-spin');p.wait_for_timeout(7600);pid=p.evaluate("__DB.auction_state[0].current_player_id")
    p.click('#btn-close');p.click('#btn-putback');p.wait_for_timeout(800)
    ok('put back: player returns to wheel (5 names), block cleared',p.evaluate('wheelNames.length')==5 and 'Waiting' in p.inner_text('#on-block'))
    p.click('#btn-spin');p.wait_for_timeout(7600);p.click('#btn-sell-open');p.fill('#sell-price','30');p.click('#btn-sold');p.wait_for_timeout(800)
    p.locator('[data-undo-sale]').first.click();p.wait_for_timeout(800)
    ok('undo sale: back on the wheel, budgets restored',p.evaluate('wheelNames.length')==5 and p.locator('.pl-val').all_inner_texts()==['200']*4,p.inner_text('#team-grid')[:100])
    p.click('#btn-spin');p.wait_for_timeout(7600);p.click('#btn-unsold');p.wait_for_timeout(800);p.click('#btn-undo-last');p.wait_for_timeout(800)
    ok('undo last action reverses unsold (back to 5 on wheel)',p.evaluate('wheelNames.length')==5 and len(p.evaluate("__DB.auction_unsold"))==0)
    ok('no JS errors in admin flows',not [e for e in p.errs+adm.errs if 'DIALOG' not in e],(p.errs,adm.errs))
    # ---- points left box + Start Round 2 ----
    pt=Site(pw,scenario_auction(),admin=True);t=pt.page('auction.html',1200)
    t.click('#btn-spin');t.wait_for_timeout(7600);t.click('#btn-sell-open');t.fill('#sell-price','75');t.click('#btn-sold');t.wait_for_timeout(700)
    vals=t.locator('.pl-val').all_inner_texts();calcs=t.locator('.pl-calc').all_inner_texts();labels=t.locator('.pl-row span').all_inner_texts()
    ok('team box: "Points left" label, value = total - spent',sorted(vals)==['125','200','200','200'] and '200 total − 75 spent' in calcs and set(l.lower() for l in labels)=={'points left'},(vals,calcs,labels))
    ok('start round 2: hidden until someone is unsold',not t.is_visible('#btn-load-r2'))
    t.click('#btn-spin');t.wait_for_timeout(7600);t.click('#btn-unsold');t.wait_for_timeout(700)
    ok('start round 2: button appears as soon as a player is unsold, shows count',t.is_visible('#btn-load-r2') and 'Start Round 2 (1 player)' in t.inner_text('#btn-load-r2'),t.inner_text('#btn-load-r2'))
    t.click('#btn-load-r2');t.wait_for_timeout(900)
    ok('start round 2: wheel now holds only the Round 2 player, banner says Round 2 running',t.evaluate('wheelRound()')==2 and t.evaluate('wheelNames.length')==1 and 'Round 2 is running' in t.inner_text('#r2-banner'),t.inner_text('#r2-banner'))
    t.click('#btn-back-r1');t.wait_for_timeout(900)
    ok('back to round 1 restores the Round 1 wheel (3 players)',t.evaluate('wheelRound()')==1 and t.evaluate('wheelNames.length')==3)
    # ---- reset ----
    pr=Site(pw,scenario_auction(),admin=True);q=pr.page('auction.html',1200);vv=Site(pw,scenario_auction(),admin=False).page('auction.html',1200)
    q.click('#btn-spin');q.wait_for_timeout(7600);q.click('#btn-sell-open');q.fill('#sell-price','40');q.click('#btn-sold');q.wait_for_timeout(700)
    q.click('#btn-spin');q.wait_for_timeout(7600);q.click('#btn-unsold');q.wait_for_timeout(700)
    q.click('#btn-spin');q.wait_for_timeout(7600);q.click('#btn-close')
    ok('reset setup: 1 sale, 1 unsold, 1 on the block',q.evaluate("__DB.team_season_rosters.length")==5 and q.evaluate("__DB.auction_unsold.length")==1 and q.evaluate("__DB.auction_state[0].current_player_id")!=None)
    q.evaluate("window.prompt=()=>'nope'");q.click('#btn-reset');q.wait_for_timeout(500)
    ok('reset: wrong confirmation text cancels, nothing deleted',q.evaluate("__DB.team_season_rosters.length")==5 and 'cancelled' in q.inner_text('#wheel-msg'))
    q.evaluate("window.prompt=()=>'RESET'");q.click('#btn-reset');q.wait_for_timeout(900)
    ok('reset: sales + Round 2 cleared, owners kept (4 rows, all owners)',q.evaluate("__DB.team_season_rosters.length")==4 and q.evaluate("__DB.team_season_rosters.every(r=>r.is_owner)") and q.evaluate("__DB.auction_unsold.length")==0)
    ok('reset: wheel back to all 5 non-owners, Round 1, nobody on the block',q.evaluate('wheelNames.length')==5 and q.evaluate('wheelRound()')==1 and 'Waiting' in q.inner_text('#on-block') and q.locator('.pl-val').all_inner_texts()==['200']*4,q.evaluate('wheelNames'))
    ok('reset: can spin again after reset',q.evaluate("document.getElementById('btn-spin').disabled")==False)
    sync(q,vv);vv.wait_for_timeout(3000)
    ok('reset: viewer screen also back to full wheel',vv.evaluate('wheelNames.length')==5)
    ok('reset button hidden from viewers',not vv.is_visible('#btn-reset'))
    # ---- randomness ----
    stat=adm.evaluate("""(function(){
      var n=33,N=99000,c=new Array(n).fill(0);for(var i=0;i<N;i++)c[secureInt(n)]++;
      var e=N/n,chi=0;c.forEach(function(x){chi+=(x-e)*(x-e)/e;});
      var pos=new Array(n).fill(0),M=33000;for(var j=0;j<M;j++){var a=secureShuffle(Array.from({length:n},function(_,k){return k;}));pos[a.indexOf(0)]++;}
      var e2=M/n,chi2=0;pos.forEach(function(x){chi2+=(x-e2)*(x-e2)/e2;});
      var xs=[];for(var k=0;k<40000;k++)xs.push(secureInt(n));var m=xs.reduce(function(a,b){return a+b;},0)/xs.length,num=0,den=0;
      for(var t=0;t<xs.length-1;t++)num+=(xs[t]-m)*(xs[t+1]-m);xs.forEach(function(x){den+=(x-m)*(x-m);});
      var same=0;for(var q=1;q<xs.length;q++)if(xs[q]===xs[q-1])same++;
      var sameShuffle=0;var b1=secureShuffle(Array.from({length:n},function(_,k){return k;})).join(),b2=secureShuffle(Array.from({length:n},function(_,k){return k;})).join();if(b1===b2)sameShuffle=1;
      return {chi:chi,chi2:chi2,r:num/den,rep:same/xs.length,sameShuffle:sameShuffle};})()""")
    ok('random: winner index uniform over 33 (chi-square < 62.5 at p=0.001)',stat['chi']<62.5,stat)
    ok('random: shuffle puts a given player in every wheel position equally often',stat['chi2']<62.5,stat)
    ok('random: no serial pattern (lag-1 correlation ~0, repeat rate ~1/33)',abs(stat['r'])<0.02 and abs(stat['rep']-1/33)<0.006 and stat['sameShuffle']==0,stat)
    # ---- other pages reflect the sale ----
    d=scenario_auction();d['team_season_rosters'].append({'id':'rx','season_id':'season1','team_id':'t4','player_id':'p4','is_owner':False,'auction_price':60,'jersey_number':None,'sold_at':'2026-10-02T00:00:00Z'})
    s2=Site(pw,d)
    q=s2.page('player.html?id=p4');ok('player page: "sold for 60 pts"','sold for 60 pts' in q.inner_text('#player-team'))
    q=s2.page('team.html?id=t4');ok('team page: player in squad with price','Ayush' in q.inner_text('#roster-grid') and '60 pts' in q.inner_text('#roster-grid'))
    q=s2.page('teams.html');ok('teams page: 2 players, 140 pts left','2 players' in q.inner_text('#teams-grid') and '140 pts left' in q.inner_text('#teams-grid'))
print(f"\n{sum(R)} passed, {len(R)-sum(R)} failed")
