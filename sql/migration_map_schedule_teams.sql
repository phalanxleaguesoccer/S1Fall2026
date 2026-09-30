-- Maps the schedule slots to the real teams:
--   Team A -> Renegades, Team B -> Muggles FC, Team C -> Scouts FC, Team D -> Desi Steelers FC
-- Every match (and anything recorded against a match) is moved to the real team,
-- then the four placeholder teams are hidden (is_active = false, nothing is deleted).
-- Safe to re-run: once the placeholders have no matches, it changes nothing.
do $$
declare
  m record;
  tbl text;
begin
  for m in
    select a.id as old_id, b.id as new_id, a.name as old_name, b.name as new_name
    from (values ('Team A','Renegades'),('Team B','Muggles FC'),('Team C','Scouts FC'),('Team D','Desi Steelers FC')) v(o,n)
    join teams a on a.name = v.o
    join teams b on b.name = v.n
  loop
    update matches set home_team_id = m.new_id where home_team_id = m.old_id;
    update matches set away_team_id = m.new_id where away_team_id = m.old_id;
    update matches set forfeited_by_team_id = m.new_id where forfeited_by_team_id = m.old_id;
    foreach tbl in array array['match_events','match_appearances','season_awards','tiebreak_shootout_order'] loop
      if to_regclass('public.' || tbl) is not null then
        execute format('update %I set team_id = $1 where team_id = $2', tbl) using m.new_id, m.old_id;
      end if;
    end loop;
    update teams set is_active = false where id = m.old_id;
    raise notice 'Mapped % -> %', m.old_name, m.new_name;
  end loop;
end $$;

-- Check: every scheduled match should now list real teams only.
select t.name, t.is_active,
  (select count(*) from matches m where m.home_team_id = t.id or m.away_team_id = t.id) as matches
from teams t order by t.is_active desc, t.name;
