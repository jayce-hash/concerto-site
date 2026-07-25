-- Tier 1 push pipeline: run once in the Supabase SQL Editor.
-- Insert/upsert-only from clients (same posture as analytics_events):
-- the public anon key can register a token but never read the list.
create table if not exists public.push_tokens (
  token      text primary key,
  user_id    uuid references auth.users(id) on delete set null,
  platform   text,
  updated_at timestamptz not null default now()
);

alter table public.push_tokens enable row level security;

drop policy if exists "clients may register tokens" on public.push_tokens;
create policy "clients may register tokens"
  on public.push_tokens for insert
  to anon, authenticated
  with check (true);

drop policy if exists "clients may refresh their token row" on public.push_tokens;
create policy "clients may refresh their token row"
  on public.push_tokens for update
  to anon, authenticated
  using (true)
  with check (true);
-- No select/delete for clients. The sender function uses the service key.
