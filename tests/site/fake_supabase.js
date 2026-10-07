// Fake supabase-js for offline site testing. DB = window.__DB (tables as arrays).
(function(){
  var DB = window.__DB;
  var LOG = window.__LOG = [];
  var FK = {teams:'team_id',players:'player_id',seasons:'season_id',matches:'match_id'};
  var ALIAS = {home:'home_team_id',away:'away_team_id'};
  function uid(){return 'id'+Math.random().toString(36).slice(2,10);}
  function computeView(name){
    if(name==='league_standings'){
      var seasons={};DB.seasons.forEach(function(s){seasons[s.id]=s;});
      var acc={};
      DB.matches.forEach(function(m){
        var ok = m.status==='forfeited' || (m.status==='completed' && m.home_score!=null && m.away_score!=null);
        if(!ok) return;
        [[m.home_team_id,m.home_score,m.away_score],[m.away_team_id,m.away_score,m.home_score]].forEach(function(x){
          var k=m.season_id+'|'+x[0];var a=acc[k]||(acc[k]={season_id:m.season_id,team_id:x[0],played:0,wins:0,draws:0,losses:0,goals_for:0,goals_against:0,goal_difference:0,points:0});
          var res; if(m.status==='forfeited') res = m.forfeited_by_team_id===x[0]?'loss':'win'; else res = x[1]>x[2]?'win':x[1]<x[2]?'loss':'draw';
          a.played++; a[res==='win'?'wins':res==='draw'?'draws':'losses']++;
          a.goals_for+=(x[1]||0); a.goals_against+=(x[2]||0);
          var s=seasons[m.season_id]; a.points += res==='win'?s.points_win:res==='draw'?s.points_draw:s.points_loss;
        });
      });
      return Object.values(acc).map(function(a){a.goal_difference=a.goals_for-a.goals_against;return a;});
    }
    if(name==='player_season_stats'){
      return DB.team_season_rosters.map(function(r){
        var p=DB.players.find(function(x){return x.id===r.player_id;})||{};
        var ms=DB.matches.filter(function(m){return m.season_id===r.season_id;});
        var mids={};ms.forEach(function(m){mids[m.id]=m;});
        var ev=DB.match_events.filter(function(e){return mids[e.match_id]&&e.player_id===r.player_id;});
        function c(t){return ev.filter(function(e){return e.event_type===t;}).length;}
        var done=ms.filter(function(m){return m.status==='completed'&&(m.home_team_id===r.team_id||m.away_team_id===r.team_id);});
        var gp=0,rest=0,abs=0;
        done.forEach(function(m){
          var mine=DB.match_appearances.find(function(a){return a.match_id===m.id&&a.player_id===r.player_id;});
          var teamHas=DB.match_appearances.some(function(a){return a.match_id===m.id&&a.team_id===r.team_id;});
          var st=mine?(mine.status||'played'):null;
          if(st==='played'||(!mine&&!teamHas))gp++; if(st==='rested')rest++; if(st==='absent')abs++;
        });
        var app=gp;gp=0;
        return {player_id:r.player_id,full_name:p.full_name,season_id:r.season_id,team_id:r.team_id,games_played:app,rested:rest,absent:abs,goals:c('goal'),assists:c('assist'),yellow_cards:c('yellow_card'),red_cards:c('red_card'),potm_awards:c('player_of_match'),saves:c('save'),tournament_awards:c('player_of_tournament'),clean_sheets:0};
      });
    }
    return null;
  }
  function table(name){ var v=computeView(name); return v||DB[name]||(DB[name]=[]); }
  function splitTop(s){var out=[],d=0,cur='';for(var i=0;i<s.length;i++){var ch=s[i];if(ch==='(')d++;if(ch===')')d--;if(ch===','&&d===0){out.push(cur.trim());cur='';}else cur+=ch;}if(cur.trim())out.push(cur.trim());return out;}
  function embed(row,sel,tname){
    var parts=splitTop(sel);var out=Object.assign({},row);
    parts.forEach(function(p){
      var m=p.match(/^(?:(\w+):)?(\w+)(?:!\w+)?\((.*)\)$/);
      if(!m) return;
      var alias=m[1],rel=m[2];var fk=alias&&ALIAS[alias]?ALIAS[alias]:FK[rel];
      var key=alias||rel;
      if(fk&&row[fk]!==undefined){out[key]=(table(rel).find(function(x){return x.id===row[fk];}))||null;}
      else out[key]=null;
    });
    return out;
  }
  function Q(name){
    var q={tname:name,filters:[],orders:[],lim:null,mode:'select',payload:null,sel:'*',opts:{},single:null};
    function run(){
      var t=table(name);var rows;
      LOG.push({t:name,mode:q.mode,f:q.filters.map(function(f){return f[0]+':'+f[1]+':'+JSON.stringify(f[2]);})});
      function match(r){return q.filters.every(function(f){var v=r[f[1]];
        if(f[0]==='or')return f[2].split(',').some(function(c){var p=c.split('.');return r[p[0]]===p[2];}); if(f[0]==='eq')return v===f[2]; if(f[0]==='in')return f[2].indexOf(v)>=0; if(f[0]==='neq')return v!==f[2];
        if(f[0]==='or')return f[2].split(',').some(function(c){var p=c.split('.');return p[1]==='eq'&&r[p[0]]===p[2];}); if(f[0]==='is')return v===f[2]||(f[2]===null&&v==null); return true;});}
      if(q.mode==='select'){
        rows=t.filter(match);
        q.orders.forEach(function(o){rows=rows.slice().sort(function(a,b){var x=a[o[0]],y=b[o[0]];if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x<y?-1:x>y?1:0)*(o[1]?1:-1);});});
        // stable multi-key: apply orders in reverse
        if(q.orders.length>1){rows=t.filter(match);q.orders.slice().reverse().forEach(function(o){rows=rows.slice().sort(function(a,b){var x=a[o[0]],y=b[o[0]];if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x<y?-1:x>y?1:0)*(o[1]?1:-1);});});}
        if(q.lim!=null)rows=rows.slice(0,q.lim);
        var count=rows.length;
        rows=rows.map(function(r){return embed(r,q.sel,name);});
        if(q.opts.head)rows=[];
        if(q.single==='single'){ if(rows.length!==1)return {data:null,error:{message:'single row expected, got '+count},count:count}; return {data:rows[0],error:null,count:count}; }
        if(q.single==='maybe'){ return {data:rows[0]||null,error:null,count:count}; }
        return {data:rows,error:null,count:count};
      }
      if(DB.__readonly_views && (name==='league_standings'||name==='player_season_stats')) return {data:null,error:{message:'view not writable'}};
      if(DB.__missing && DB.__missing.indexOf(name)>=0) return {data:null,error:{message:'relation "'+name+'" does not exist'}};
      var tt=DB[name]||(DB[name]=[]);
      if(q.mode==='insert'){ if(name==='team_season_rosters'&&[].concat(q.payload).some(function(x){return tt.some(function(r){return r.season_id===x.season_id&&r.player_id===x.player_id;});}))return {data:null,error:{message:'duplicate key value violates unique constraint'}}; var arr=[].concat(q.payload).map(function(x){return Object.assign({id:uid()},x);});
        // unique checks
        if(name==='tiebreak_shootout_order'){for(var i=0;i<arr.length;i++){if(tt.concat(arr.slice(0,i)).some(function(r){return r.season_id===arr[i].season_id&&r.position===arr[i].position;}))return {data:null,error:{message:'duplicate key value violates unique constraint'}};}}
        arr.forEach(function(x){tt.push(x);});return {data:arr,error:null};}
      if(q.mode==='update'){tt.filter(match).forEach(function(r){Object.assign(r,q.payload);});return {data:null,error:null};}
      if(q.mode==='delete'){var keep=tt.filter(function(r){return !match(r);});tt.length=0;keep.forEach(function(r){tt.push(r);});return {data:null,error:null};}
      if(q.mode==='upsert'){[].concat(q.payload).forEach(function(x){var keys=q.onConflict?q.onConflict.split(','):null;var ex=keys&&tt.find(function(r){return keys.every(function(k){return r[k]===x[k];});});if(ex)Object.assign(ex,x);else tt.push(Object.assign({id:uid()},x));});return {data:null,error:null};}
    }
    var api={
      select:function(s,o){ if(q.mode==='select'){q.sel=s||'*';q.opts=o||{};} return api;},
      insert:function(p){q.mode='insert';q.payload=p;return api;},
      update:function(p){q.mode='update';q.payload=p;return api;},
      delete:function(){q.mode='delete';return api;},
      upsert:function(p,o){q.mode='upsert';q.payload=p;q.onConflict=(o&&o.onConflict)||null;return api;},
      eq:function(c,v){q.filters.push(['eq',c,v]);return api;},
      neq:function(c,v){q.filters.push(['neq',c,v]);return api;},
      or:function(x){q.filters.push(['or',null,x]);return api;},
      in:function(c,v){q.filters.push(['in',c,v]);return api;},
      is:function(c,v){q.filters.push(['is',c,v]);return api;},
      order:function(c,o){q.orders.push([c,!(o&&o.ascending===false)]);return api;},
      limit:function(n){q.lim=n;return api;},
      single:function(){q.single='single';return api;},
      maybeSingle:function(){q.single='maybe';return api;},
      then:function(res,rej){return Promise.resolve(run()).then(res,rej);}
    };
    return api;
  }
  window.supabase={createClient:function(){
    return {
      from:Q,
      rpc:function(fn,args){
        if(fn==='increment_page_view'){var pv=DB.page_views||(DB.page_views=[]);var r=pv.find(function(x){return x.page_key===args.p_key;});if(!r){r={page_key:args.p_key,view_count:0};pv.push(r);}r.view_count++;return Promise.resolve({data:r.view_count,error:null});}
        return Promise.resolve({data:null,error:{message:'no rpc '+fn}});
      },
      auth:{
        getSession:function(){return Promise.resolve({data:{session:DB.__admin?{user:{id:'admin-1'}}:null}});},
        signOut:function(){return Promise.resolve({});},
        signInWithPassword:function(){return Promise.resolve({data:{user:{id:'admin-1'}},error:null});}
      }
    };
  }};
})();
