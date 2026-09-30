-- PREPROD ONLY. Copies the live team rosters and auction prices (as of 30 Sep 2026)
-- into the preprod database: 4 owners + 33 auctioned players, 780 points spent.
-- Safe to re-run.
insert into team_season_rosters (season_id, team_id, player_id, is_owner, auction_price)
select s.id, t.id, p.id, v.is_owner, v.price
from (values
  ('Muggles FC', 'Amritpal Singh', true, null::int),
  ('Scouts FC', 'Bhagyesh Rane', true, null::int),
  ('Desi Steelers FC', 'Nasiq', true, null::int),
  ('Renegades', 'Varun', true, null::int),
  ('Renegades', 'Minti', false, 20),
  ('Scouts FC', 'Ketan Gaikwad', false, 10),
  ('Desi Steelers FC', 'Ketan Shilimkar', false, 4),
  ('Muggles FC', 'Preetesh Duvvuri', false, 8),
  ('Desi Steelers FC', 'Vamshi', false, 30),
  ('Renegades', 'Nuhu Okikiri', false, 24),
  ('Renegades', 'Shailesh', false, 12),
  ('Desi Steelers FC', 'Vija', false, 28),
  ('Scouts FC', 'Pradnyal Gandhi', false, 82),
  ('Muggles FC', 'Dheeraj R Vatti', false, 26),
  ('Muggles FC', 'Vishnu Mohan', false, 72),
  ('Scouts FC', 'Kishor Ghadge', false, 2),
  ('Desi Steelers FC', 'Vignesh', false, 22),
  ('Desi Steelers FC', 'Kaushik Apte', false, 40),
  ('Muggles FC', 'Dhruv', false, 44),
  ('Renegades', 'Chirag', false, 72),
  ('Scouts FC', 'Sagar SJ', false, 30),
  ('Scouts FC', 'Kartik', false, 32),
  ('Scouts FC', 'Sandeep Naik', false, 10),
  ('Renegades', 'Prajna', false, 24),
  ('Renegades', 'Sangram Ghewade', false, 14),
  ('Desi Steelers FC', 'Rishabh Devgon', false, 50),
  ('Renegades', 'Dhananjay', false, 26),
  ('Muggles FC', 'Ashu', false, 16),
  ('Scouts FC', 'Bilal Yaser', false, 24),
  ('Desi Steelers FC', 'Ajinkya P', false, 10),
  ('Muggles FC', 'Ayush', false, 8),
  ('Desi Steelers FC', 'Sagar', false, 10),
  ('Muggles FC', 'Taranjot Singh Dang', false, 10),
  ('Muggles FC', 'Rohith', false, 10),
  ('Renegades', 'Vivek', false, 2),
  ('Renegades', 'Rajeev Singh', false, 6),
  ('Scouts FC', 'Jitendra', false, 2)
) v(team, player, is_owner, price)
join seasons s on s.is_current
join teams t on t.name = v.team
join players p on p.full_name = v.player
on conflict (season_id, player_id) do update
  set team_id = excluded.team_id, is_owner = excluded.is_owner, auction_price = excluded.auction_price;
