Offline site tests (no Supabase needed): `cd tests/site && python3 suite.py`
Uses Playwright + a fake Supabase client with fixture data. Standings SQL was
tested separately against a local Postgres.
