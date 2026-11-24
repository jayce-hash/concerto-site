-- Fan-stream alerts: run once in the Supabase SQL Editor.
-- One row per stream and fan, so nobody is told about the same stream twice.
-- Only the site's alert job reads or writes it; the apps cannot see it.
create table if not exists public.medley_stream_alerts (
  stream_id uuid not null references public.medley_streams (id) on delete cascade,
  user_id   uuid not null references auth.users (id) on delete cascade,
  sent_at   timestamptz not null default now(),
  primary key (stream_id, user_id)
);
alter table public.medley_stream_alerts enable row level security;
