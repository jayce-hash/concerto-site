-- My Shows cloud sync: run once in the Supabase SQL Editor.
-- Adds the column the app merges saved shows into. Until this runs,
-- the app stays local-only (by design, sync is additive).
alter table public.profiles
  add column if not exists saved_events jsonb not null default '[]'::jsonb;
