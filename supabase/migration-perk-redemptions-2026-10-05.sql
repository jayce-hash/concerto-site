-- Perk redemptions (Oct 5, 2026). Paste into Supabase > SQL Editor > New query > Run. Safe to run twice.
create table if not exists public.perk_redemptions (
  id uuid primary key default gen_random_uuid(),
  perk_id uuid not null references public.perks(id) on delete cascade,
  org_id uuid references public.partner_orgs(id) on delete cascade,
  fan_key text not null,
  redeemed_day date not null default current_date,
  redeemed_at timestamptz not null default now()
);
create unique index if not exists perk_redemptions_once_a_day on public.perk_redemptions (perk_id, fan_key, redeemed_day);
create index if not exists perk_redemptions_org on public.perk_redemptions (org_id, redeemed_at);
alter table public.perk_redemptions enable row level security;   -- only the site's server functions can read or write

alter table public.partner_orgs add column if not exists redeem_code_hash text;
