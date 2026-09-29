-- Shared wheel: every visitor sees the same spin. The admin publishes the
-- spin (pool order, winner, landing offset) and each browser animates it.
alter table auction_state add column if not exists wheel_round int not null default 1;
alter table auction_state add column if not exists spin_seq int not null default 0;
alter table auction_state add column if not exists spin_pool jsonb;
alter table auction_state add column if not exists spin_winner_id uuid;
alter table auction_state add column if not exists spin_offset numeric not null default 0;
alter table auction_state add column if not exists spin_started_at timestamptz;
