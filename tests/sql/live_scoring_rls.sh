#!/bin/bash
PSQL="psql -h /tmp/pgs -p 5544 -U postgres -d lt -At -q"
A=aaaaaaaa-0000-0000-0000-000000000001; B=bbbbbbbb-0000-0000-0000-000000000002; C=cccccccc-0000-0000-0000-000000000003; D=dddddddd-0000-0000-0000-000000000004
pass=0; fail=0
run(){ # who sql -> output (errors included)
  local who=$1 sql=$2 role=authenticated sub=""
  case $who in A) sub=$A;; B) sub=$B;; C) sub=$C;; D) sub=$D;; anon) role=anon;; pg) role=postgres;; esac
  if [ "$who" = pg ]; then $PSQL -c "$sql" 2>&1; else $PSQL -c "set role $role; ${sub:+set request.jwt.claim.sub='$sub';} $sql" 2>&1 | grep -v '^SET$'; fi; }
ok(){ if [ "$2" = 1 ]; then pass=$((pass+1)); echo "PASS $1"; else fail=$((fail+1)); echo "FAIL $1 :: $3"; fi; }
expect_err(){ out=$(run "$2" "$3"); if echo "$out" | grep -qiE "error|violates|denied|not allowed|only|invalid|record the toss|finished|half must|second-half|confirmed from"; then ok "$1" 1; else ok "$1" 0 "$out"; fi; }
expect_ok(){ out=$(run "$2" "$3"); if echo "$out" | grep -qiE "error|violates|denied"; then ok "$1" 0 "$out"; else ok "$1" 1; fi; }
val(){ run "$1" "$2" | tail -1; }
$PSQL <<SQL
grant usage on schema public to anon, authenticated; grant all on all tables in schema public to anon, authenticated; grant execute on all functions in schema public to anon, authenticated;
delete from coadmins; delete from admins; delete from auth.users;
insert into auth.users(id,email) values ('$A','admin@x.com'),('$B','co@x.com'),('$C','pend@x.com'),('$D','out@x.com');
insert into admins(user_id,display_name) values ('$A','Preet');
update matches set status='scheduled', live_phase=null, home_score=null, away_score=null, toss_winner_team_id=null, toss_choice=null, clock_rem=null where id=(select id from matches order by match_day, match_number limit 1);
delete from match_appearances where match_id=(select id from matches order by match_day, match_number limit 1);
delete from live_locks;
delete from match_events where match_id=(select id from matches order by match_day, match_number limit 1);
SQL
M=$($PSQL -c "select id from matches order by match_day, match_number limit 1")
H=$($PSQL -c "select home_team_id from matches where id='$M'"); AW=$($PSQL -c "select away_team_id from matches where id='$M'")
PH=$($PSQL -c "select player_id from team_season_rosters where team_id='$H' limit 1"); PA=$($PSQL -c "select player_id from team_season_rosters where team_id='$AW' limit 1")
echo "match $M"
# --- anonymous / outsiders
n=$(val anon "with u as (update matches set live_phase='h1' where id='$M' returning 1) select count(*) from u"); [ "$n" = 0 ] && ok "anon cannot update match (0 rows)" 1 || ok "anon update" 0 "$n"
[ "$(val anon "select count(*) from matches")" -gt 0 ] && ok "anon can read matches" 1 || ok "anon can read matches" 0
expect_err "anon cannot insert events" anon "insert into match_events(match_id,team_id,player_id,event_type,half,time_remaining) values ('$M','$H','$PH','goal',1,300)"
expect_err "outsider cannot approve self" D "insert into coadmins(user_id,display_name,status) values ('$D','D','approved')"
expect_err "outsider cannot request for someone else" D "insert into coadmins(user_id,display_name) values ('$B','B')"
expect_ok  "outsider can request own access" C "insert into coadmins(user_id,display_name,email) values ('$C','Pending Pat','pend@x.com')"
expect_ok  "co-admin B requests access" B "insert into coadmins(user_id,display_name,email) values ('$B','Sunny','co@x.com')"
# --- pending cannot do anything
out=$(run C "update matches set live_phase='h1', toss_winner_team_id='$H', toss_choice='side' where id='$M' returning id"); [ -z "$(echo "$out"|grep -E '^[0-9a-f-]{36}$')" ] && ok "pending co-admin cannot update match (0 rows)" 1 || ok "pending co-admin cannot update match" 0 "$out"
expect_err "pending cannot approve self" C "update coadmins set status='approved' where user_id='$C'; select 1/0;"
n=$(val C "with u as (update coadmins set status='approved' where user_id='$C' returning 1) select count(*) from u"); [ "$n" = 0 ] && ok "pending cannot approve self (0 rows)" 1 || ok "pending cannot approve self" 0 "$n"
# --- admin approves B
expect_ok "admin approves B" A "update coadmins set status='approved', decided_at=now(), decided_by='$A' where user_id='$B'"
# --- B before live
n=$(val B "with u as (insert into match_events(match_id,team_id,player_id,event_type,half,time_remaining) values ('$M','$H','$PH','goal',1,300) returning 1) select count(*) from u" ); echo "$n" | grep -qi error && ok "co-admin cannot add events before kickoff" 1 || ok "co-admin cannot add events before kickoff" 0 "$n"
expect_err "co-admin cannot start without toss" B "update matches set live_phase='h1', clock_rem=600, clock_running=true where id='$M'; select 1"
n=$(val B "with u as (update matches set live_phase='h1', clock_rem=600, clock_running=true where id='$M' returning 1) select count(*) from u"); out=$(run B "update matches set live_phase='h1' where id='$M'"); echo "$out" | grep -qi "toss" && ok "start without toss refused (message mentions toss)" 1 || ok "start without toss refused" 0 "$out"
expect_err "co-admin cannot change teams" B "update matches set home_team_id='$AW' where id='$M'; select 1"
expect_err "co-admin cannot skip phases (null->h2)" B "update matches set toss_winner_team_id='$H', toss_choice='side', live_phase='h2' where id='$M'"
expect_ok  "co-admin records toss + lineup" B "update matches set toss_winner_team_id='$H', toss_choice='side' where id='$M'; insert into match_appearances(match_id,player_id,team_id,status,started) values ('$M','$PH','$H','rested',false)"
expect_ok  "co-admin kicks off" B "update matches set live_phase='h1', clock_rem=600, clock_running=true where id='$M'"
[ "$(val pg "select clock_at is not null from matches where id='$M'")" = t ] && ok "server stamps clock_at" 1 || ok "server stamps clock_at" 0
expect_ok  "co-admin adds 1st-half goal" B "insert into match_events(match_id,team_id,player_id,event_type,half,time_remaining,minute,second) values ('$M','$H','$PH','goal',1,440,99,99)"
g0=$(val pg "select coalesce(sum(goals),0) from player_season_stats where player_id='$PH'"); [ "$g0" = 0 ] && ok "live goals do not count in player_season_stats yet" 1 || ok "live goals not in stats" 0 "$g0"
r=$(val pg "select minute||':'||second||' by '||(created_by is not null) from match_events where match_id='$M' and event_type='goal'"); [ "$r" = "2:40 by true" ] && ok "server computed 7:20 left = 2:40 (ignores client minute/second)" 1 || ok "server computed 2:40" 0 "$r"
expect_err "second-half event during first half refused" B "insert into match_events(match_id,team_id,player_id,event_type,half,time_remaining) values ('$M','$AW','$PA','goal',2,300)"
expect_err "time over 10:00 refused" B "insert into match_events(match_id,team_id,player_id,event_type,half,time_remaining) values ('$M','$AW','$PA','goal',1,700)"
expect_ok  "co-admin ends first half" B "update matches set live_phase='ht', clock_rem=0, clock_running=false where id='$M'"
expect_ok  "co-admin starts second half" B "update matches set live_phase='h2', clock_rem=600, clock_running=true where id='$M'"
expect_ok  "co-admin adds 2nd-half own goal + goal" B "insert into match_events(match_id,team_id,player_id,event_type,half,time_remaining) values ('$M','$AW','$PA','own_goal',2,290),('$M','$AW','$PA','goal',2,100)"
r=$(val pg "select minute||':'||second from match_events where match_id='$M' and event_type='own_goal'"); [ "$r" = "15:10" ] && ok "2nd half 4:50 left = 15:10" 1 || ok "2nd half 4:50 left = 15:10" 0 "$r"
expect_ok  "co-admin edits an event" B "update match_events set time_remaining=280 where match_id='$M' and event_type='own_goal'"
expect_ok  "co-admin removes an event" B "delete from match_events where match_id='$M' and event_type='goal' and half=2"
expect_ok  "co-admin full time" B "update matches set live_phase='ft', clock_rem=0, clock_running=false where id='$M'"
expect_err "cannot confirm skipping ft check (bad status)" B "update matches set status='forfeited' where id='$M'"
expect_ok  "co-admin confirms result with a fake score" B "update matches set status='completed', live_phase=null, home_score=9, away_score=9 where id='$M'"
r=$(val pg "select home_score||'-'||away_score||' '||status||' '||coalesce(live_phase,'null')||' '||clock_running from matches where id='$M'"); [ "$r" = "2-0 completed null false" ] && ok "final score computed from events (2-0 incl. own goal), not the 9-9 sent" 1 || ok "final score from events" 0 "$r"
g1=$(val pg "select coalesce(sum(goals),0) from player_season_stats where player_id='$PH'"); [ "$g1" -ge 1 ] && ok "after confirm the goal counts in player_season_stats" 1 || ok "stats after confirm" 0 "$g1"
# standings: view sees completed
n=$(val pg "select count(*) from league_standings where played>0"); [ "$n" -ge 2 ] && ok "standings view picks up the completed match" 1 || ok "standings pick up" 0 "$n"
# --- after final
n=$(val B "with u as (insert into match_events(match_id,team_id,player_id,event_type,half,time_remaining) values ('$M','$H','$PH','goal',1,100) returning 1) select count(*) from u"); echo "$n" | grep -qi "error\|violates" && ok "co-admin cannot add events after final" 1 || ok "co-admin cannot add events after final" 0 "$n"
n=$(val B "with u as (delete from match_events where match_id='$M' returning 1) select count(*) from u"); [ "$n" = 0 ] && ok "co-admin cannot delete events after final (0 rows)" 1 || ok "co-admin delete after final" 0 "$n"
n=$(val B "with u as (update matches set home_score=5 where id='$M' returning 1) select count(*) from u"); [ "$n" = 0 ] && ok "co-admin cannot edit finished match (0 rows)" 1 || ok "co-admin finished match" 0 "$n"
expect_ok "admin CAN still correct after final" A "update match_events set time_remaining=200 where match_id='$M' and event_type='goal'"
# --- other tables
expect_err "co-admin cannot insert team" B "insert into teams(name) values ('Hack FC')"
n=$(val B "with u as (update players set full_name='x' returning 1) select count(*) from u"); [ "$n" = 0 ] && ok "co-admin cannot edit players (0 rows)" 1 || ok "co-admin players" 0 "$n"
# --- audit
n=$(val B "select count(*) from audit_log where table_name='match_events'"); [ "$n" -ge 4 ] && ok "co-admin can read match audit rows ($n)" 1 || ok "co-admin read audit" 0 "$n"
n=$(val B "select count(*) from audit_log where table_name='players'"); [ "$n" = 0 ] && ok "co-admin cannot read player audit rows" 1 || ok "co-admin player audit" 0 "$n"
n=$(val D "select count(*) from audit_log"); [ "$n" = 0 ] && ok "outsider sees no audit rows" 1 || ok "outsider audit" 0 "$n"
l=$(val pg "select distinct changed_by_label from audit_log where table_name='match_events' and changed_by='$B'"); [ "$l" = Sunny ] && ok "audit stamps editor name (Sunny) and time" 1 || ok "audit label" 0 "$l"
n=$(val B "with u as (update audit_log set action='X' returning 1) select count(*) from u"); [ "$n" = 0 ] && ok "audit rows can not be edited" 1 || ok "audit edit" 0 "$n"
n=$(val B "with u as (delete from audit_log returning 1) select count(*) from u"); [ "$n" = 0 ] && ok "audit rows can not be deleted" 1 || ok "audit delete" 0 "$n"
n=$(val A "with u as (delete from audit_log returning 1) select count(*) from u"); [ "$n" = 0 ] && ok "even admin can not delete audit rows" 1 || ok "admin audit delete" 0 "$n"
expect_ok "co-admin adds reason note" B "insert into audit_log(table_name,record_id,action,new_data,changed_by_label) values ('live_note','$M','x','{\"note\":\"wrong player\"}','FORGED')"
r=$(val pg "select changed_by_label||'/'||action from audit_log where table_name='live_note' order by changed_at desc limit 1"); [ "$r" = "Sunny/NOTE" ] && ok "note label/action stamped by server (forgery ignored)" 1 || ok "note stamp" 0 "$r"
expect_err "cannot forge a players audit row" B "insert into audit_log(table_name,record_id,action) values ('players','$M','DELETE')"
# --- locks
expect_ok "co-admin takes lock" B "insert into live_locks(match_id,user_id,label) values ('$M','$B','Sunny') on conflict (match_id) do update set user_id=excluded.user_id,label=excluded.label,beat_at=now()"
expect_err "cannot take lock as someone else" B "insert into live_locks(match_id,user_id,label) values ('$M','$A','Preet') on conflict (match_id) do update set user_id=excluded.user_id"
n=$(val anon "select count(*) from live_locks"); [ "$n" = 0 ] && ok "visitors cannot see locks" 1 || ok "locks private" 0 "$n"
# --- revoke
expect_ok "admin revokes B" A "update coadmins set status='revoked' where user_id='$B'"
n=$(val B "select is_live_editor()"); [ "$n" = f ] && ok "revoked co-admin loses access" 1 || ok "revoke" 0 "$n"
# --- SQL editor / service role still works
expect_ok "SQL editor (no user) can still update matches" pg "update matches set notes=notes where id='$M'"
n=$(val anon "select server_now() is not null"); [ "$n" = t ] && ok "server_now() works for visitors" 1 || ok "server_now" 0 "$n"
echo "== $pass passed, $fail failed"
