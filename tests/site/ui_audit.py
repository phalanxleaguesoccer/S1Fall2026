# Layout audit: no sideways page scroll, nothing wider than its card, on every page at 375/768/1280/1600px.
import os
HERE=os.path.dirname(os.path.abspath(__file__))
src=open(HERE+'/records_tests.py').read().split('with sync_playwright() as pw:')[0]
src=src.replace("open(__file__.replace('records_tests.py','captain_tests.py'))","open(HERE+'/captain_tests.py')")
exec(src)
JS='''()=>{
 const out=[];const W=window.innerWidth;
 if(document.documentElement.scrollWidth>W+1) out.push('PAGE scrolls sideways: '+document.documentElement.scrollWidth+' > '+W);
 const scrolls=e=>{for(let a=e.parentElement;a;a=a.parentElement){const o=getComputedStyle(a).overflowX;if(o==='auto'||o==='scroll'||o==='hidden')return a;}return null};
 document.querySelectorAll('body *').forEach(e=>{
  const cs=getComputedStyle(e); if(cs.display==='none'||cs.visibility==='hidden'||e.closest('[style*="display: none"],[style*="display:none"]')) return;
  const r=e.getBoundingClientRect(); if(!r.width||!r.height) return;
  const sc=scrolls(e);
  const card=e.closest('.card,.rc,.tc,.av-card,.m-card');
  if(card&&card!==e){const c=card.getBoundingClientRect(); if(r.right>c.right+2&&(!sc||!card.contains(sc)||sc===card)&&!(sc&&sc!==card&&card.contains(sc))) out.push('OVERFLOWS CARD: <'+e.tagName.toLowerCase()+' class="'+e.className+'"> '+(e.innerText||'').slice(0,30).replace(/\\n/g,' ')+' right='+Math.round(r.right)+' card='+Math.round(c.right));}
  else if(r.right>W+2&&!sc) out.push('OFFSCREEN: <'+e.tagName.toLowerCase()+' class="'+e.className+'"> '+(e.innerText||'').slice(0,30).replace(/\\n/g,' ')+' right='+Math.round(r.right));
 });
 document.querySelectorAll('.card,.container,main').forEach(c=>{if(c.scrollWidth>c.clientWidth+1&&getComputedStyle(c).display!=='none')out.push('CARD CONTENT WIDER THAN CARD: '+(c.id||c.className)+' '+c.scrollWidth+'>'+c.clientWidth)});
 return [...new Set(out)].slice(0,8);
}'''
pages=[('index.html',None),('matches.html#upcoming',None),('matches.html#recent',None),('matches.html#previous',None),('matches.html#all',None),('match.html?id=m0',None),('team.html?id='+T['Renegades'],None),('teams.html',None),('player.html?id='+P['Amritpal Singh'],None),('players.html',None),('stats.html#ranking',None),('stats.html#season',None),('auction.html',None),('sponsors.html',None)]
tabs=['goals','assists','yellow','red','owngoals','fouls','availability','captains','injury']
views=['hub','goals','assists','contrib','potm','discipline','avail','teams','teamdisc','matchrec','captains']
bad=0
with sync_playwright() as pw:
    s=Site(pw,d)
    for w in (375,768,1280,1600):
        def chk(p,name):
            global bad
            r=p.evaluate(JS)
            if r: bad+=1;print('--',w,name);[print('   ',x) for x in r]
        for path,_ in pages:
            p=s.page(path,1200);p.set_viewport_size({'width':w,'height':900});p.wait_for_timeout(300)
            if path.startswith('player.html'):
                try: p.click('text=Maximize',timeout=800)
                except Exception: pass
                p.wait_for_timeout(300)
            chk(p,path);p.close()
        p=s.page('stats.html#milestones',1200);p.set_viewport_size({'width':w,'height':900})
        for t in tabs:
            p.click('#tabs button[data-tab=%s]'%t);p.wait_for_timeout(250)
            chk(p,'milestones:'+t)
            if t=='goals':
                try: p.click('#ms-body [data-det]',timeout=500);p.wait_for_timeout(200);chk(p,'milestones:goals details')
                except Exception: pass
        p.close()
        p=s.page('stats.html#records',1500);p.set_viewport_size({'width':w,'height':900})
        for v in views:
            p.evaluate("recGo('%s')"%v);p.wait_for_timeout(200);chk(p,'records:'+v)
        p.close()
        for a,b2 in [('Muggles FC','Scouts FC'),('Renegades','Desi Steelers FC')]:
            p=s.page('stats.html#rivalry/%s/%s'%(T[a],T[b2]),1500);p.set_viewport_size({'width':w,'height':900});p.wait_for_timeout(200);chk(p,'rivalry:'+a+' v '+b2);p.close()
# ---- live scoring screens: public live views + the admin Live desk (pre-match and live)
import datetime
_ls=open(HERE+'/live_public_tests.py').read()
exec(_ls[_ls.index('UTC=datetime'):_ls.index('def page(')])
with sync_playwright() as pw:
    dl,Tl,Pl=scen();sl=Site(pw,dl)
    dp,_,_=scen();dp['matches'][1].update({'live_phase':None,'clock_rem':None,'clock_running':False});sa=Site(pw,dp,True)
    dv,_,_=scen();sv=Site(pw,dv,True)
    for w in (375,768,1280):
        def chk2(p,name):
            global bad
            r=p.evaluate(JS)
            if r: bad+=1;print('--',w,name);[print('   ',x) for x in r]
        for site,path in [(sl,'match.html?id=m1'),(sl,'matches.html'),(sl,'index.html'),(sa,'admin/live.html?match=m1'),(sv,'admin/live.html?match=m1')]:
            p=site.page(path,1500);p.set_viewport_size({'width':w,'height':900});p.wait_for_timeout(300);chk2(p,'live:'+path+(' (pre)' if site is sa else ''))
            if site is sv:
                p.click('[data-add="goal|H"]');p.wait_for_timeout(300);chk2(p,'live:desk event sheet');p.click('#sheet [data-s-player] >> nth=0');p.wait_for_timeout(200);chk2(p,'live:desk event sheet (assist step)')
                p.click('[data-s-cancel]');p.click('#t-audit');p.wait_for_timeout(500);chk2(p,'live:desk audit tab')
            p.close()
print('issues:',bad)
