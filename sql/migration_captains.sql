-- Captains: who captained each team in each match.
-- Uses the existing match_appearances.is_captain column and adds captain_stand_in
-- (true when the regular captain was unavailable and someone stood in for that match).
-- Only one captain per team per match is allowed.
alter table match_appearances add column if not exists captain_stand_in boolean not null default false;
create unique index if not exists one_captain_per_team_match on match_appearances (match_id, team_id) where is_captain;
