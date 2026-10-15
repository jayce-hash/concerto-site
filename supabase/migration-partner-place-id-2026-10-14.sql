-- Partner cards: store the Google place id so photos use venue-photo's 25-day cache.
alter table public.partner_orgs add column if not exists place_id text;
