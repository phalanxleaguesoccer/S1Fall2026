-- Week 2 fields: toss on each match, exact time (seconds) and penalty flag on each event.
alter table matches add column if not exists toss_winner_team_id uuid references teams(id);
alter table matches add column if not exists toss_choice text;
alter table matches drop constraint if exists matches_toss_choice_check;
alter table matches add constraint matches_toss_choice_check check (toss_choice is null or toss_choice in ('side','kickoff'));
alter table match_events add column if not exists second int;
alter table match_events add column if not exists is_penalty boolean not null default false;
