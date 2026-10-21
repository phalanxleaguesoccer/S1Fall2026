from harness import *; from fixtures import *
serve();R=[]
def ok(n,c,d=''):
    R.append(bool(c));print(('PASS ' if c else 'FAIL ')+n+('' if c else '  -> '+str(d)))
b=base();m=b['m'];T=b['T'];P=b['P']
m(1,1,'Muggles FC','Scouts FC','completed',1,2);m(1,2,'Renegades','Desi Steelers FC','completed',0,0)
d=finish(b);ev=[]
def e(match,team,pl,typ,half=None,minute=None):
    ev.append({'id':'e%02d'%len(ev),'match_id':match,'team_id':T[team],'player_id':P[pl],'event_type':typ,'half':half,'minute':minute,'related_player_id':None,'created_at':'2026-10-07T01:00:%02d.%03d+00:00'%(len(ev),0)})
e('m0','Muggles FC','Vignesh','goal',1)
e('m0','Muggles FC','Amritpal Singh','foul',1)            # foul, no card
e('m0','Scouts FC','Bilal Yaser','foul',1);e('m0','Scouts FC','Bilal Yaser','yellow_card',1)   # foul + yellow
e('m0','Scouts FC','Bhagyesh Rane','goal',2);e('m0','Scouts FC','Bilal Yaser','goal',2)
d['match_events']=ev
with sync_playwright() as pw:
    s=Site(pw,d);p=s.page('match.html?id=m0',1500);t=p.inner_text('#match-root')
    ok('no JS errors',not p.errs,p.errs)
    ok('standalone foul shows FOUL chip "Foul committed"','FOUL' in t and 'Foul committed' in t,t)
    ok('a card is NOT a foul: foul rows and the yellow-card row are separate',p.locator('.m-chip.fl').count()==2 and p.locator('.m-chip.yc').count()==1 and 'Foul · ' not in t,t)
    ok('Fouls stat row: 1 vs 1... Muggles 1, Scouts 1',p.locator('.m-stat',has_text='Fouls').inner_text().replace('\n',' ').split()[0]=='1' ,p.locator('.m-stat',has_text='Fouls').inner_text())
    rows=[r.split('\t') for r in p.locator('.m-ptable tbody tr').all_inner_texts()]
    bil=[r for r in rows if 'Bilal' in r[0]][0]
    ok('player table has FL then YC: Bilal FL 1, YC 1','FL' in p.inner_text('.m-ptable thead') and bil[-3:-1]==['1','1'],bil)
    ok('who-played line says "1 foul"','1 foul' in t,t)
    st=s.page('stats.html#milestones',1500);st.click('[data-tab=fouls]');st.wait_for_timeout(300)
    rw=[r.split('\t') for r in st.locator('#ms-body tbody tr:not(.det)').all_inner_texts()]
    ok('Fouls tab lists both fouls (carded or not) in order',[r[1] for r in rw]==['Amritpal Singh','Bilal Yaser'],rw)
    st.locator('[data-det]').nth(0).click();d0=st.inner_text('tr.det:visible')
    st.locator('[data-det]').nth(1).click();d1=st.locator('tr.det:visible').last.inner_text()
    ok('details: ordinals, no "card given" line (a card is not a foul)','Foul number in tournament' in d1 and 'Card given' not in d1 and 'Card given' not in d0,(d0,d1))
    ss=s.page('stats.html#season',1500);H=[h.strip().lower() for h in ss.locator('#ss-body thead th').all_inner_texts()]
    ok('Season Stats has Fouls and OG columns, no effect on ranking',H.count('fouls')==1 and H.count('og')==1,H)
    ix=H.index('fouls');rr=[r.split('\t') for r in ss.locator('#ss-body tbody tr').all_inner_texts()]
    ok('Season Stats: Bilal fouls 1, Amritpal 1, Vignesh 0',[r[ix] for r in rr if r[1].strip() in('Bilal Yaser','Amritpal Singh')]==['1','1'] or sorted([r[ix].strip() for r in rr if r[1].strip() in('Bilal Yaser','Amritpal Singh')])==['1','1'],rr[:4])
    pp=s.page('player.html?id='+P['Bilal Yaser'],1200);pp.click('#history-toggle');pp.wait_for_timeout(600)
    ct=pp.locator('#career-totals-body td').all_inner_texts();hd=[x.strip().lower() for x in pp.locator('#history-body thead').first.inner_text().split()]
    ok('profile career totals: Fouls 1 and Yellow 1 (no errors)',ct[hd.index('fouls')]=='1' and ct[hd.index('yellow')]=='1' and not pp.errs,(hd,ct,pp.errs))
    cur=pp.locator('#stats-body td').all_inner_texts();ok('profile current season row has Fouls 1',cur[8]=='1',cur)
    tp=s.page('team.html?id='+T['Muggles FC'],1500)
    ok('team page totals have Fouls column (Muggles roster: 2 fouls)',tp.inner_text('#squad-totals-body').split()[4]=='2' if 'fouls' in tp.inner_text('body').lower() else False,(tp.inner_text('#squad-totals-body'),tp.errs))
    ad=s.page('admin/dashboard.html',1500) if False else None
    d2=dict(d);d2['match_appearances']=[{'id':'a0','match_id':'m0','team_id':T['Muggles FC'],'player_id':P['Amritpal Singh'],'status':'played','started':True},{'id':'a1','match_id':'m0','team_id':T['Scouts FC'],'player_id':P['Ajinkya P'],'status':'played','started':True}]
    q=Site(pw,d2).page('match.html?id=m0',1500);tt=q.inner_text('#match-root')
    ash=[r for r in q.locator('.m-ptable tbody tr').all_inner_texts() if r.startswith('Ajinkya')]
    ok('player with no events in the match: zeros, never "undefined"/NaN',ash and 'undefined' not in tt and 'NaN' not in tt and all(x in ('0',) for x in ash[0].split('\t')[2:]),(ash,))
    mp=Site(pw,d).page('match.html?id=m0',1200);mp.set_viewport_size({'width':390,'height':800});mp.wait_for_timeout(300)
    ok('phone: no sideways scroll',mp.evaluate('document.documentElement.scrollWidth')<=390)
print(sum(R),'passed',len(R)-sum(R),'failed')
