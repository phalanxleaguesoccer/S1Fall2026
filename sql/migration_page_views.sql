-- Migration: adds page-view tracking (total site views + per-page views,
-- including individual player/team/match pages).
--
-- Design: a narrow table (page_views) holds one row per tracked page, plus
-- one row keyed 'site' for the running total-site-views count. Public reads
-- are allowed directly (so the count can be displayed), but public WRITES
-- go only through the increment_page_view() function below, not directly
-- against the table — this keeps the counts from being trivially
-- overwritten/reset by anyone with the publishable key, while still letting
-- anonymous visitors trigger a view increment without needing to log in.

create table if not exists page_views (
  page_key text primary key,
  view_count bigint not null default 0,
  updated_at timestamptz not null default now()
);

alter table page_views enable row level security;

create policy "public read page views" on page_views for select using (true);
-- Intentionally NO public insert/update/delete policy — all writes happen
-- through the SECURITY DEFINER function below instead.

create or replace function increment_page_view(p_key text)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
  new_count bigint;
begin
  insert into page_views (page_key, view_count, updated_at)
  values (p_key, 1, now())
  on conflict (page_key) do update
    set view_count = page_views.view_count + 1,
        updated_at = now()
  returning view_count into new_count;
  return new_count;
end;
$$;

-- Anyone (including anonymous/public-key visitors) may call the function,
-- since it only ever adds 1 and cannot be used to read or modify anything
-- else in the database.
grant execute on function increment_page_view(text) to anon, authenticated;

insert into page_views (page_key, view_count) values ('site', 0)
on conflict (page_key) do nothing;
