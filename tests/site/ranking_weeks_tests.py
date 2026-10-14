from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
m(1,1,'Desi Steelers FC','Muggles FC','completed',1,0);m(1,2,'Renegades','Scouts FC','completed',0,0)
m(2,1,'Muggles FC','Scouts FC','completed',2,0);m(2,2,'Renegades','Desi Steelers FC','completed',1,3);m(3,1,'Scouts FC','Desi Steelers FC')
d=finish(b);ev=[]
def e(match,team,pl,typ):
    ev.append({'id':'e%02d'%len(ev),'match_id':match,'team_id':T[team],'player_id':P[pl],'event_type':typ,'half':1,'minute':None,'related_player_id':None,'created_at':'2026-10-07T01:00:%02d+00:00'%len(ev)})
e('m0','Desi Steelers FC','Nasiq','goal');e('m2','Muggles FC','Amritpal Singh','goal');e('m2','Muggles FC','Amritpal Singh','goal')
e('m3','Desi Steelers FC','Nasiq','goal');e('m3','Renegades','Varun','yellow_card');e('m1','Scouts FC','Bhagyesh Rane','foul')
d['match_events']=ev;d['match_appearances']=[]
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#ranking',1500);p.click('#qa-accept')
    ok('no JS errors',not p.errs,p.errs)
    rowsel='#rk-body .table-scroll > table > tbody > tr:not(.det)'
    hdr=[h.strip().lower() for h in p.locator('#rk-body thead th').all_inner_texts()]
    RW=lambda:[r.split('\t') for r in p.locator(rowsel).all_inner_texts()]
    pc=hdr.index('points')
    import re
    def mainrank():
        return p.evaluate("[...document.querySelectorAll('#rk-body .table-scroll > table > tbody > tr:not(.det)')].map(tr=>[tr.children[1].innerText.trim(),tr.children[0].lastChild.textContent.trim()])")
    mr=dict((a,b) for a,b in mainrank())
    main={r[1].strip():(mr[r[1].strip()],r[pc].strip()) for r in RW()}
    up=p.locator('#rk-body td.ms-n .mv.up').count();dn=p.locator('#rk-body td.ms-n .mv.down').count();tot=len(RW())
    ok('some players moved up (green) and some down (red)',up>0 and dn>0,(up,dn))
    ok('players with no change have no sign',up+dn<tot,(up,dn,tot))
    col=lambda c:p.evaluate("getComputedStyle(document.querySelector('%s')).color"%c)
    ok('green is green, red is red',col('#rk-body .mv.up')=='rgb(62, 207, 110)' and col('#rk-body .mv.down')=='rgb(255, 92, 92)')
    # consistency: every player's last-week row in Details equals the main table
    bad=[]
    names=[r[1].strip() for r in RW()]
    for i,nm in enumerate(names):
        p.locator('#rk-body button[data-pdet]:visible').nth(i).click()
        det=p.locator('tr.det:visible')
        rows=[x.split('\t') for x in det.locator('.wk-table tbody tr').all_inner_texts()]
        if len(rows)!=2: bad.append((nm,'weeks',rows));continue
        last=rows[-1];total=last[3].strip()
        rk=det.locator('.wk-table tbody tr').last.locator('td').last.evaluate("e=>e.lastChild.textContent.trim()")
        if total!=main[nm][1] or rk!=main[nm][0]: bad.append((nm,last,main[nm]))
        p.locator('#rk-body button[data-pdet]:visible').nth(i).click()
    ok('week table last row matches main table (points and rank) for all players, 2 weeks each',not bad,bad)
    # Nasiq: week1 5 pts, week2 W(2)+goal(3)=5 -> total 10
    i=names.index('Nasiq');p.locator('#rk-body button[data-pdet]:visible').nth(i).click()
    wk=[x.split('\t') for x in p.locator('tr.det:visible .wk-table tbody tr').all_inner_texts()]
    ok('Nasiq weekly points +5 then +5, total 5 then 10',wk[0][2].strip()=='+5' and wk[0][3].strip()=='5' and wk[1][2].strip()=='+5' and wk[1][3].strip()=='10',wk)
    ok('Details still shows calculation','total points' in p.inner_text('tr.det:visible').lower() and 'week by week' in p.inner_text('tr.det:visible').lower())
    p.locator('#rk-body button[data-pdet]:visible').nth(i).click()
    # arrow in week table for a mover agrees with its rank change
    mv=p.evaluate("""(()=>{const out=[];document.querySelectorAll('#rk-body td.ms-n').forEach(td=>{const s=td.querySelector('.mv');out.push(s?s.className+td.textContent:td.textContent)});return out})()""")
    ok('arrows carry the number of places',any('mv up' in x and any(c.isdigit() for c in x) for x in mv),mv)
    # filters keep ranks
    all_ranks=dict((k,v[0]) for k,v in main.items())
    p.select_option('#r-team',label='Scouts FC');r2=dict((a,b) for a,b in mainrank())
    ok('team filter hides rows but keeps ranks',all(all_ranks[k]==v for k,v in r2.items()) and 0<len(r2)<len(all_ranks),(r2,all_ranks))
    # all seasons: no arrows, no history
    p.select_option('#r-team','all');p.select_option('#r-season','all');p.wait_for_timeout(500)
    ok('All seasons: no arrows',p.locator('#rk-body .mv').count()==0)
    p.locator('#rk-body button[data-pdet]:visible').first.click()
    ok('All seasons: details explain week table is single-season',('single season' in p.inner_text('tr.det:visible').lower()))
    ok('no JS errors at end',not p.errs,p.errs)
print(sum(R),'/',len(R))
# --- regression: a player whose position did not change must show no arrow even when rank numbers jump (tie groups splitting)
b=base();m=b['m'];T=b['T'];P=b['P']
m(1,1,'Desi Steelers FC','Muggles FC','completed',0,0);m(1,2,'Renegades','Scouts FC','completed',0,0)
m(2,1,'Desi Steelers FC','Scouts FC','completed',1,0);m(2,2,'Renegades','Muggles FC','completed',0,0)
d=finish(b);d['match_events']=[{'id':'e0','match_id':'m2','team_id':T['Desi Steelers FC'],'player_id':P['Nasiq'],'event_type':'goal','half':1,'minute':None,'related_player_id':None,'created_at':'2026-10-07T01:00:00+00:00'}];d['match_appearances']=[]
R2=[]
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('stats.html#ranking',1500);p.click('#qa-accept')
    bad=p.evaluate("""(()=>{const ids=RK.rows.map(r=>r.id),H=RK.hist,bad=[];
      const pos=(w,id)=>1+ids.filter(o=>H.weeks[o][w].rank<H.weeks[id][w].rank).length;
      ids.forEach(id=>{const exp=pos(0,id)-pos(1,id);if(H.move[id]!==exp)bad.push([id,H.move[id],exp])});return bad})()""")
    ok('movement = change in number of players strictly ahead (not change of rank number) for every player',not bad,bad)
    jumped=p.evaluate("RK.rows.filter(r=>RK.hist.move[r.id]===0&&RK.hist.weeks[r.id][0].rank!==RK.hist.weeks[r.id][1].rank).length")
    print('players whose rank number changed but have no arrow:',jumped)
    ok('no JS errors (regression)',not p.errs,p.errs)
print(sum(R),'/',len(R))
