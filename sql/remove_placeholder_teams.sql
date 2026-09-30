-- Permanently removes the placeholder teams Team A, Team B, Team C, Team D.
-- SAFETY: run sql/migration_map_schedule_teams.sql FIRST. This script checks EVERY table that
-- references teams(id) (matches, events, appearances, awards, rosters, shoot-out order, ...).
-- If any placeholder is still used anywhere, it deletes NOTHING and tells you where.
-- The four real teams and the schedule are never touched.
do $$
declare
  ids uuid[];
  fk record;
  n bigint;
  blockers text := '';
begin
  select array_agg(id) into ids from teams where name in ('Team A','Team B','Team C','Team D');
  if ids is null then raise notice 'No placeholder teams found - nothing to do.'; return; end if;

  for fk in
    select c.conrelid::regclass::text as tbl, a.attname as col
    from pg_constraint c
    join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
    where c.contype = 'f' and c.confrelid = 'public.teams'::regclass
  loop
    execute format('select count(*) from %s where %I = any($1)', fk.tbl, fk.col) into n using ids;
    if n > 0 then blockers := blockers || format(E'\n  %s.%s: %s row(s)', fk.tbl, fk.col, n); end if;
  end loop;

  if blockers <> '' then
    raise exception 'NOT deleted - placeholders are still referenced:%', blockers;
  end if;

  delete from teams where id = any(ids);
  raise notice 'Deleted % placeholder team(s).', array_length(ids, 1);
end $$;

-- Check: only the four real teams remain, each with 12 matches.
select t.name, t.is_active,
  (select count(*) from matches m where m.home_team_id = t.id or m.away_team_id = t.id) as matches
from teams t order by t.name;
