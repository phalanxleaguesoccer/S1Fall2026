import json, re
from harness import *; from fixtures import *
serve()
R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
names="Minti,Ketan Shilimkar,Preetesh Duvvuri,Rohith,Sangram Ghewade,Taranjot Singh Dang,Jitendra,Vivek,Sagar SJ,Vignesh,Vija,Kishor Ghadge,Vamshi,Pradnyal Gandhi,Vishnu Mohan,Sagar,Ketan Gaikwad,Dheeraj R Vatti,Kartik,Nuhu Okikiri,Rajeev Singh,Chirag,Dhruv,Dhananjay,Shailesh,Prajna,Sandeep Naik,Ashu,Kaushik,Ayush,Bilal Yaser,Ajinkya P,Rishabh Devgon".split(',')
def full():
    d=scenario_auction();have={p['full_name'] for p in d['players']}
    for k,n in enumerate(names):
        if n not in have: d['players'].append({'id':'q%d'%k,'full_name':n,'age':30,'preferred_position':'Mid','position_category':'Center','is_active':True,'photo_url':None,'skill_level':'Advanced','stamina_level':'Medium','skill_rating':7,'preferred_foot':'Right','jersey_size':'M','bio_notes':'','created_at':'2026-01-01'})
    return d
with sync_playwright() as pw:
    # ---- spoiler bug: few players ----
    sa=Site(pw,scenario_auction(),admin=True);a=sa.page('auction.html',1200)
    sv=Site(pw,scenario_auction(),admin=False);v=sv.page('auction.html',1200)
    a.evaluate("window.SPIN_MS=3000")
    before=a.inner_text('#round1');cnt=a.inner_text('#r1-count')
    a.click('#btn-spin');a.wait_for_timeout(1000)
    ok('admin mid-spin: side list unchanged (all 5 still listed)',a.inner_text('#round1')==before and a.inner_text('#r1-count')==cnt,(a.inner_text('#round1'),a.inner_text('#r1-count')))
    ok('admin mid-spin: still 5 items on the side list',a.locator('#round1 > *').count()==5 or a.evaluate("document.getElementById('round1').innerText.trim().split('\\n').length")>=5)
    a.wait_for_timeout(3000)
    st=a.evaluate("__DB.auction_state[0]");w=a.evaluate("(id)=>PLAYERS[id].full_name",st['spin_winner_id'])
    ok('admin after spin: winner removed from side list, 4 remain',w not in a.inner_text('#round1') and a.inner_text('#r1-count').strip().endswith('4)'),(w,a.inner_text('#round1'),a.inner_text('#r1-count')))
    # viewer mid-spin
    sb=Site(pw,scenario_auction(),admin=True);b=sb.page('auction.html',1200)
    vv=Site(pw,scenario_auction(),admin=False);v=vv.page('auction.html',1200)
    b.evaluate("window.SPIN_MS=6000");v.evaluate("window.SPIN_MS=6000")
    b.click('#btn-spin');b.wait_for_timeout(500)
    v.evaluate("(d)=>{__DB.auction_state.length=0;d.forEach(r=>__DB.auction_state.push(r));}",b.evaluate("__DB.auction_state"))
    v.wait_for_timeout(3200)
    ok('viewer mid-spin: animating and side list still lists all 5',v.evaluate('ANIM')==True and v.evaluate("document.getElementById('round1').innerText")==before,(v.evaluate('ANIM'),v.inner_text('#round1')))
    v.wait_for_timeout(6000)
    w=b.evaluate("(id)=>PLAYERS[id].full_name",b.evaluate("__DB.auction_state[0].spin_winner_id"))
    ok('viewer after spin: winner off the side list',w not in v.inner_text('#round1'),v.inner_text('#round1'))
    # ---- reserved pick ----
    sc=Site(pw,full(),admin=True);p=sc.page('auction.html',1500)
    ok('33 players on the wheel',p.evaluate('wheelNames.length')==33,p.evaluate('wheelNames.length'))
    ok('reserved note visible: Pick #22 reserved for Minti','22' in p.inner_text('#reserved-note') and 'Minti' in p.inner_text('#reserved-note'),p.inner_text('#reserved-note'))
    pv=Site(pw,full(),admin=False).page('auction.html',1200)
    ok('viewer also sees the reserved note',pv.is_visible('#reserved-note'))
    pos=[];firsts=[]
    for t in range(6):
        p.reload();p.wait_for_timeout(900);p.evaluate("window.SPIN_MS=120")
        order=[]
        for k in range(33):
            p.click('#btn-spin');p.wait_for_function("!ANIM && document.getElementById('btn-unsold') && __DB.auction_state[0].current_player_id",timeout=8000)
            order.append(p.evaluate("PLAYERS[__DB.auction_state[0].current_player_id].full_name"))
            p.evaluate("document.getElementById('btn-unsold').click()");p.wait_for_timeout(120)
        pos.append(order.index('Minti')+1);firsts.append(order[0])
        if t==0: ok('first trial: all 33 distinct players drawn',len(set(order))==33,order)
    ok('Minti drawn exactly at pick 22 in all 6 trials',pos==[22]*6,pos)
    ok('other picks stay random (first pick differs across trials)',len(set(firsts))>1,firsts)
    # after pick 22 Minti is gone; Round 2 doesn't reserve
    ok('no JS errors',not p.errs and not pv.errs and not a.errs and not v.errs,(p.errs,a.errs,v.errs))
print(f"\n{sum(R)} passed, {len(R)-sum(R)} failed")
