-- Concerto 2.7: the $4.99 Show Pass. One row per purchase, written only by the
-- RevenueCat webhook (service role). Row level security is on with no policies,
-- so the app and website can't read or write it directly.
create table if not exists public.show_passes (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  until timestamptz not null,
  transaction_id text,
  created_at timestamptz not null default now()
);
create index if not exists show_passes_user_until on public.show_passes (user_id, until);
alter table public.show_passes enable row level security;
