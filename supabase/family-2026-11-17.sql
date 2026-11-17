-- Concerto, Reprise and Medley: one account. Nov 17 2026.
-- Run once in the Supabase SQL Editor. Safe to run twice. It only adds columns to the
-- profiles table; it does not change or remove anything that is there.

-- The shows saved in Concerto. Already there if the earlier My Shows step was run.
alter table public.profiles
  add column if not exists saved_events jsonb not null default '[]'::jsonb;

-- The setlists saved in Medley, so they follow the account to a new phone.
alter table public.profiles
  add column if not exists medley_saved jsonb not null default '[]'::jsonb;

-- One pass for one show: a Show Pass bought in Concerto and an Album Pass bought in Reprise
-- each note the show here, so the pass counts in the other app too.
alter table public.profiles
  add column if not exists family_passes jsonb not null default '{}'::jsonb;

-- Reprise albums, without their photos (those stay in the phone's photo library), so the
-- albums are there on a new phone.
alter table public.profiles
  add column if not exists reprise_albums jsonb not null default '[]'::jsonb;
