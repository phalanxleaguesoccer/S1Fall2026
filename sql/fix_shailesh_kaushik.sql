-- Fix: Shailesh's skill rating (was left blank, now set to 3) and
-- Kaushik's full name (was using just the jersey name "Kaushik", now his
-- full name "Kaushik Apte").

update players set skill_rating = 3
where full_name = 'Shailesh';

update players set full_name = 'Kaushik Apte'
where full_name = 'Kaushik';
