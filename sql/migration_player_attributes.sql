-- Migration: adds real columns for the attributes needed by the Players
-- page "Sort & Filter" feature. Run this once in the Supabase SQL editor.
-- Safe to run even if some columns already exist (uses IF NOT EXISTS).

alter table players add column if not exists stamina_level text;      -- 'Low' | 'Medium' | 'High'
alter table players add column if not exists stamina_rank int;        -- 1=Low, 2=Medium, 3=High (drives sort order)
alter table players add column if not exists skill_rating int;        -- numeric rating out of 10
alter table players add column if not exists skill_level text;        -- 'Beginner' | 'Intermediate' | 'Advanced' | 'Pro'
alter table players add column if not exists skill_level_rank int;    -- 1=Beginner..4=Pro (drives sort order)
alter table players add column if not exists playing_experience text; -- free text, filter-only
alter table players add column if not exists fitness_notes text;      -- free text, filter-only
alter table players add column if not exists leave_plan text;         -- free text, filter-only

-- Keep the two rank columns in sync automatically whenever stamina_level /
-- skill_level is set or changed via the admin dashboard, so you never have
-- to remember to update the rank by hand.
create or replace function set_player_attribute_ranks()
returns trigger as $$
begin
  new.stamina_rank := case lower(coalesce(new.stamina_level, ''))
    when 'low' then 1
    when 'medium' then 2
    when 'high' then 3
    else null
  end;
  new.skill_level_rank := case lower(coalesce(new.skill_level, ''))
    when 'beginner' then 1
    when 'intermediate' then 2
    when 'advanced' then 3
    when 'pro' then 4
    else null
  end;
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_set_player_attribute_ranks on players;
create trigger trg_set_player_attribute_ranks
  before insert or update on players
  for each row execute function set_player_attribute_ranks();

-- ============ RE-ENTER THE 3 EXISTING PLAYERS' DATA INTO THE NEW COLUMNS ============
-- (Previously bundled into one bio_notes text blob — now split out. bio_notes
-- itself is left as-is/untouched so nothing is lost.)

update players set
  stamina_level = 'Medium',
  skill_rating = 4,
  skill_level = 'Intermediate',
  playing_experience = 'Exposure to corporate league, practice matches.',
  fitness_notes = 'None that will affect game.',
  leave_plan = 'None.'
where full_name = 'Minti';

update players set
  stamina_level = 'Medium',
  skill_rating = 5,
  skill_level = 'Beginner',
  playing_experience = 'Beginner.',
  fitness_notes = null,
  leave_plan = 'NA'
where full_name = 'Ketan Shilimkar';

update players set
  stamina_level = 'Low',
  skill_rating = 3,
  skill_level = 'Beginner',
  playing_experience = 'Recreational.',
  fitness_notes = null,
  leave_plan = 'No leave plan.'
where full_name = 'Preetesh Duvvuri';
