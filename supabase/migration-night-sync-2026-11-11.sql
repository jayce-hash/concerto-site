-- Concerto, Nov 11 2026. Run once in the Supabase SQL Editor. Safe to run twice.
--
-- 1. Your Night follows the account. The app merges each show's plan (stops, how the fan is
--    getting there, bag, Plan Your Night answers) into this column, so a new phone or a
--    reinstall keeps it. The seat, ticket, photos and notes are never sent: they stay on the
--    phone. Until this runs, the app keeps nights on the phone only, as before.
alter table public.profiles
  add column if not exists night_records jsonb not null default '{}'::jsonb;

-- 2. Saved-show changes. The daily alerts job writes one row per change it has announced
--    (new time, new date, postponed, cancelled), so a fan is never told the same thing twice.
--    Written only by the server (service role). Row level security is on with no policies,
--    so the app and website can't read or write it.
create table if not exists public.show_change_log (
  event_id text not null,
  change_key text not null,
  created_at timestamptz not null default now(),
  primary key (event_id, change_key)
);
alter table public.show_change_log enable row level security;
