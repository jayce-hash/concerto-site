-- Concerto Partners monthly report. Run once in the Supabase SQL Editor
-- (Dashboard -> SQL Editor -> New query -> paste -> Run).
--
-- What partners are promised (partner pages, deck, privacy policy): each month, how many
-- fans saw their card, how many tapped it, and how many opened their Perk. Aggregate
-- counts only, never anything about a person.
--
-- Where the numbers come from (public.analytics_events):
--   partner_impression  card shown: venue rows, Your Night, Concerto AI, Plan My Night (app + web)
--   partner_tap         action = 'reserve' (Reserve or Book), 'directions', 'perk' (gold star)
--   perks_opened        a Perk opened from Your Night (app)
-- The app writes these directly; the website sends them through netlify/functions/track.js.
-- Older app builds named the partner id `perk_id` on Your Night events; both are read.

-- Devices left out of every report (Jayce's own test phone, etc.).
create table if not exists public.report_excluded_devices (device_id text primary key);
alter table public.report_excluded_devices enable row level security;

create index if not exists analytics_events_partner_idx
  on public.analytics_events ((coalesce(props->>'partner_id', props->>'perk_id')), created_at)
  where event in ('partner_impression', 'partner_tap', 'perks_opened');

create or replace function public.partner_monthly_report(p_month date default date_trunc('month', now() - interval '1 month')::date)
returns table (
  partner_id     text,
  partner        text,
  venue          text,
  views          bigint,
  fans_reached   bigint,
  app_views      bigint,
  web_views      bigint,
  taps           bigint,
  reserve_taps   bigint,
  direction_taps bigint,
  perk_opens     bigint
)
language sql stable
as $$
  with e as (
    select event, platform, device_id,
           coalesce(props->>'partner_id', props->>'perk_id') as pid,
           props->>'partner' as name,
           nullif(props->>'venue', '') as venue,
           props->>'action' as action
    from public.analytics_events
    where event in ('partner_impression', 'partner_tap', 'perks_opened')
      and created_at >= date_trunc('month', p_month)
      and created_at <  date_trunc('month', p_month) + interval '1 month'
      and device_id not in (select device_id from public.report_excluded_devices)
  )
  select pid,
         max(name),
         coalesce(venue, '(all venues)'),
         count(*) filter (where event = 'partner_impression'),
         count(distinct device_id) filter (where event = 'partner_impression'),
         count(*) filter (where event = 'partner_impression' and platform <> 'web'),
         count(*) filter (where event = 'partner_impression' and platform = 'web'),
         count(*) filter (where event = 'partner_tap'),
         count(*) filter (where event = 'partner_tap' and action in ('reserve', 'book')),
         count(*) filter (where event = 'partner_tap' and action = 'directions'),
         count(*) filter (where (event = 'partner_tap' and action = 'perk') or event = 'perks_opened')
  from e
  where pid is not null and pid <> '' and pid not like 'demo-%'
  group by pid, coalesce(venue, '(all venues)')
  order by max(name), 3;
$$;

-- Owner-only, like analytics_events itself: nobody can call this through the public API.
revoke all on function public.partner_monthly_report(date) from public, anon, authenticated;

-- ============================================================
-- HOW TO USE IT (first week of each month)
-- ============================================================
-- Last month, every partner, one row per venue:
--   select * from partner_monthly_report();
-- A specific month:
--   select * from partner_monthly_report('2026-11-01');
-- One partner (id from partner_orgs), totals across venues:
--   select partner, sum(views) views, sum(taps) taps, sum(reserve_taps) reserve, sum(direction_taps) directions, sum(perk_opens) perk_opens
--   from partner_monthly_report() where partner_id = '<id>' group by partner;
-- Then email each partner their row from partners@concertocity.com.
