-- Points: Win 2, Draw 1, Loss 0 (standings recalculate automatically from
-- completed matches, so nothing else is needed after a result is saved).
alter table seasons alter column points_win set default 2;
alter table seasons alter column points_draw set default 1;
alter table seasons alter column points_loss set default 0;
update seasons set points_win = 2, points_draw = 1, points_loss = 0;

-- Last tie-break: penalty shoot-out winner (only filled for drawn matches
-- that were settled by a shoot-out).
alter table matches add column if not exists shootout_winner_team_id uuid references teams(id);
