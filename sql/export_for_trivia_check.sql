-- READ-ONLY. Paste into Supabase SQL editor and run. Copy the whole "line" column (all rows) and send it to Claude.
-- It lists, in plain text, every completed match, goal/assist/card/POTM event, captain and lineup of the current season.
with s as (select id from seasons where is_current limit 1),
mm as (select m.*, h.name hn, a.name an, tw.name twn from matches m join s on s.id = m.season_id join teams h on h.id = m.home_team_id join teams a on a.id = m.away_team_id left join teams tw on tw.id = m.toss_winner_team_id)
select line from (
  select 1 o, match_day*10+match_number k, 'M|D'||match_day||'M'||match_number||'|'||hn||' '||coalesce(home_score::text,'?')||'-'||coalesce(away_score::text,'?')||' '||an||'|'||status||'|toss:'||coalesce(twn,'-')||'/'||coalesce(toss_choice,'-') as line from mm
  union all
  select 2, m.match_day*10+m.match_number, 'E|D'||m.match_day||'M'||m.match_number||'|'||t.name||'|'||p.full_name||'|'||e.event_type||'|h'||coalesce(e.half::text,'-')||'|min'||coalesce(e.minute::text,'-')||':'||coalesce(e.second::text,'-')||'|rem'||coalesce(e.time_remaining::text,'-')||case when e.is_penalty then '|pen' else '' end||coalesce('|rel:'||rp.full_name,'')
  from match_events e join mm m on m.id = e.match_id join teams t on t.id = e.team_id join players p on p.id = e.player_id left join players rp on rp.id = e.related_player_id
  union all
  select 3, m.match_day*10+m.match_number, 'C|D'||m.match_day||'M'||m.match_number||'|'||t.name||'|'||p.full_name||'|'||a.status
  from match_appearances a join mm m on m.id = a.match_id join teams t on t.id = a.team_id join players p on p.id = a.player_id where a.is_captain
  union all
  select 4, m.match_day*10+m.match_number, 'L|D'||m.match_day||'M'||m.match_number||'|'||t.name||'|played:'||string_agg(p.full_name, ';' order by p.full_name)
  from match_appearances a join mm m on m.id = a.match_id join teams t on t.id = a.team_id join players p on p.id = a.player_id where a.status = 'played' group by m.match_day, m.match_number, t.name
) x order by o, k, line;
