-- Undoes the earlier merge of "Desi Steelers FC" into the schedule's Team A
-- slot. No draw has happened yet to decide which real team identity plays
-- as Team A/B/C/D, so Desi Steelers FC (name, crest, and Nasiq as owner)
-- becomes its own standalone team entity — same as Muggles FC and Scouts FC
-- — while the actual schedule slot reverts to a plain, unassigned "Team A".

-- Step 1: revert the schedule's team back to a plain, unbranded slot.
update teams set name = 'Team A', crest_url = null where name = 'Desi Steelers FC';

-- Step 2: create Desi Steelers FC as its own standalone team, not tied to
-- any scheduled match.
insert into teams (name, crest_url) values ('Desi Steelers FC', 'assets/teams/desi-steelers-fc.png');

-- Step 3: move Nasiq's owner assignment off the (now reverted) Team A and
-- onto the new standalone Desi Steelers FC team.
update team_season_rosters
set team_id = (select id from teams where name = 'Desi Steelers FC')
where player_id = (select id from players where full_name = 'Nasiq')
  and is_owner = true;
