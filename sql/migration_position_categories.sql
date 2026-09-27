-- Migration: adds a standardized position_category column (Forward / Center /
-- Defense / Flex / Goalkeeper) used for the Players page filter, and
-- categorizes all 22 players currently on file per your answers.
--
-- The original detailed position (e.g. "Mid-field/Defence", "LM/CDM/CM/Wing/LB")
-- stays exactly as-is in preferred_position — position_category is a new,
-- separate column just for filtering; nothing is overwritten or lost.

alter table players add column if not exists position_category text
  check (position_category in ('Forward', 'Center', 'Defense', 'Flex', 'Goalkeeper'));

update players set position_category = 'Defense'    where full_name = 'Minti';
update players set position_category = 'Flex'       where full_name = 'Ketan Shilimkar';
update players set position_category = 'Flex'       where full_name = 'Preetesh Duvvuri';
update players set position_category = 'Flex'       where full_name = 'Rohith';
update players set position_category = 'Defense'    where full_name = 'Sangram Ghewade';
update players set position_category = 'Flex'       where full_name = 'Taranjot Singh Dang';
update players set position_category = 'Forward'    where full_name = 'Jitendra';
update players set position_category = 'Flex'       where full_name = 'Vivek';
update players set position_category = 'Forward'    where full_name = 'Sagar SJ';
update players set position_category = 'Goalkeeper' where full_name = 'Vignesh';
update players set position_category = 'Flex'       where full_name = 'Vija';
update players set position_category = 'Flex'       where full_name = 'Kishor Ghadge';
update players set position_category = 'Flex'       where full_name = 'Vamshi';
update players set position_category = 'Flex'       where full_name = 'Pradnyal Gandhi';
update players set position_category = 'Flex'       where full_name = 'Vishnu Mohan';
update players set position_category = 'Flex'       where full_name = 'Sagar';
update players set position_category = 'Defense'    where full_name = 'Ketan Gaikwad';
update players set position_category = 'Center'     where full_name = 'Dheeraj R Vatti';
update players set position_category = 'Center'     where full_name = 'Kartik';
update players set position_category = 'Forward'    where full_name = 'Nuhu Okikiri';
update players set position_category = 'Defense'    where full_name = 'Rajeev Singh';
update players set position_category = 'Center'     where full_name = 'Nasiq';
