import json, uuid
def i(n): return n
def base():
    S='season1'
    seasons=[{'id':S,'name':'Season 1 Fall 2026','is_current':True,'points_win':2,'points_draw':1,'points_loss':0,'created_at':'2026-01-01'}]
    names=['Team A','Team B','Team C','Team D','Desi Steelers FC','Muggles FC','Scouts FC','Renegades']
    teams=[{'id':'t'+str(k),'name':n,'is_active':True,'crest_url':None} for k,n in enumerate(names)]
    T={n:'t'+str(k) for k,n in enumerate(names)}
    pl=['Nasiq','Amritpal Singh','Bhagyesh Rane','Varun','Ayush','Bilal Yaser','Ajinkya P','Rishabh Devgon','Vignesh']
    players=[{'id':'p'+str(k),'full_name':n,'age':30+k,'preferred_position':'Mid','position_category':'Center','is_active':True,'photo_url':None,'skill_level':'Advanced','stamina_level':'Medium','skill_rating':7,'preferred_foot':'Right','jersey_size':'M','bio_notes':'','created_at':'2026-01-0'+str(k+1)} for k,n in enumerate(pl)]
    P={n:'p'+str(k) for k,n in enumerate(pl)}
    ros=[]
    def r(team,player,owner=False): ros.append({'id':'r%d'%len(ros),'season_id':S,'team_id':T[team],'player_id':P[player],'is_owner':owner,'jersey_number':len(ros)+1})
    r('Desi Steelers FC','Nasiq',True);r('Desi Steelers FC','Ayush');r('Desi Steelers FC','Vignesh')
    r('Muggles FC','Amritpal Singh',True);r('Muggles FC','Bilal Yaser')
    r('Scouts FC','Bhagyesh Rane',True);r('Scouts FC','Ajinkya P')
    r('Renegades','Varun',True);r('Renegades','Rishabh Devgon')
    matches=[]
    def m(day,num,h,a,status='scheduled',hs=None,as_=None,forf=None,k=None):
        matches.append({'id':'m%d'%len(matches),'season_id':S,'match_day':day,'match_number':num,'home_team_id':T[h],'away_team_id':T[a],'status':status,'home_score':hs,'away_score':as_,'forfeited_by_team_id':T[forf] if forf else None,'kickoff_at':'2026-10-%02dT%s:00-04:00'%(6+7*(day-1),['21:00','21:25','21:50','22:15'][num-1]) if True else None,'notes':None})
    return dict(S=S,seasons=seasons,teams=teams,T=T,players=players,P=P,rosters=ros,m=m,matches=matches)
def scenario_pre():
    b=base();m=b['m']
    m(1,1,'Team A','Team B');m(1,2,'Team C','Team D');m(2,1,'Team A','Team C');m(2,2,'Team B','Team D')
    return finish(b)
def scenario_played():
    b=base();m=b['m']
    m(1,1,'Team A','Team B','completed',3,1);m(1,2,'Team C','Team D')
    T=b['T'];P=b['P']
    ev=[]
    def e(match,team,pl,typ,half=1,minute=3): ev.append({'id':'e%d'%len(ev),'match_id':match,'team_id':T[team],'player_id':P[pl],'event_type':typ,'half':half,'minute':minute,'related_player_id':None})
    # events for players on real teams (as if drawn) attached to the completed match
    e('m0','Team A','Nasiq','goal');e('m0','Team A','Nasiq','goal',2,9);e('m0','Team A','Ayush','goal',2,11)
    e('m0','Team A','Ayush','assist');e('m0','Team B','Varun','goal',2,12);e('m0','Team A','Vignesh','save',1,5)
    e('m0','Team A','Nasiq','player_of_match',2,14);e('m0','Team B','Varun','yellow_card',1,4);e('m0','Team A','Nasiq','player_of_tournament',2,14)
    d=finish(b);d['match_events']=ev;return d
def scenario_post_tie():
    """Season complete, real teams: Desi wins all; Muggles/Scouts/Renegades level on everything."""
    b=base();m=b['m']
    m(1,1,'Desi Steelers FC','Muggles FC','completed',1,0);m(1,2,'Scouts FC','Renegades','completed',0,0)
    m(2,1,'Desi Steelers FC','Scouts FC','completed',1,0);m(2,2,'Muggles FC','Renegades','completed',0,0)
    m(3,1,'Desi Steelers FC','Renegades','completed',1,0);m(3,2,'Muggles FC','Scouts FC','completed',0,0)
    return finish(b)
def finish(b):
    db={'seasons':b['seasons'],'teams':b['teams'],'players':b['players'],'team_season_rosters':b['rosters'],'matches':b['matches'],
        'match_events':[],'match_appearances':[],'page_views':[],'season_awards':[],'suspensions':[],'player_notes_log':[],'player_rating_log':[],'admins':[{'user_id':'admin-1'}],'auction_unsold':[],'auction_state':[],'tiebreak_shootout_order':[]}
    db['_ids']={'T':b['T'],'P':b['P']}
    return db
def scenario_auction():
    d=scenario_pre()
    owners=[r for r in d['team_season_rosters'] if r['is_owner']]
    for r in owners: r['auction_price']=None; r['sold_at']='2026-10-01T00:00:00Z'
    d['team_season_rosters']=owners
    return d
