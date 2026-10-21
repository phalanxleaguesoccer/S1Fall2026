-- Injuries: an absence can be marked as caused by injury (shown on Stats > Milestones > Injury).
alter table match_appearances add column if not exists absent_reason text;
alter table match_appearances drop constraint if exists match_appearances_absent_reason_check;
alter table match_appearances add constraint match_appearances_absent_reason_check check (absent_reason is null or absent_reason in ('injury'));
