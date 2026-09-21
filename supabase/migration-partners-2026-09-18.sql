-- Concerto Partner Console: venues own their page, partners publish Perks.
-- Run once in Supabase SQL editor. Additive; touches nothing existing.

create extension if not exists pgcrypto;

-- Who can act for a venue or a business. One row per (user, org).
create table if not exists partner_orgs (
  id uuid primary key default gen_random_uuid(),
  kind text not null check (kind in ('venue','restaurant','hotel','artist')),
  name text not null,
  venue_slug text,                      -- for kind = 'venue': the catalogue slug they own
  email_domain text,                    -- claimed via a work email on this domain
  plan text not null default 'founding' check (plan in ('founding','paid','trial','cancelled')),
  plan_until date,                      -- founding partners: free until this date
  stripe_customer_id text,
  created_at timestamptz not null default now()
);
create table if not exists partner_members (
  org_id uuid references partner_orgs(id) on delete cascade,
  user_id uuid not null,                -- auth.users.id (magic link)
  role text not null default 'owner',
  created_at timestamptz not null default now(),
  primary key (org_id, user_id)
);

-- A venue's own words for any of the eight sections. Read model merges these
-- over venue_info.json and stamps "Verified by the venue" with the date.
create table if not exists venue_overrides (
  venue_slug text not null,
  section text not null check (section in ('bagPolicy','parking','rideshare','concessions','accessibility','reEntry','ticketPickup','gates')),
  content jsonb not null,               -- same shape as venue_info.json's section
  verified_at date not null default current_date,
  updated_by uuid,
  updated_at timestamptz not null default now(),
  primary key (venue_slug, section)
);

-- Stage times a venue sets per event. Flows to Your Night and the website.
create table if not exists stage_times (
  id uuid primary key default gen_random_uuid(),
  venue_slug text not null,
  event_date date not null,
  tm_event_id text,                     -- Ticketmaster id when known
  doors time, opener time, headliner time,
  note text,
  source text not null default 'venue' check (source in ('venue','setlistfm','fan')),
  updated_at timestamptz not null default now()
);
create index if not exists stage_times_lookup on stage_times (venue_slug, event_date);

-- Perks: a partner's offer, tied to venues. Read model feeds PerkSlot + site.
create table if not exists perks (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references partner_orgs(id) on delete cascade,
  kind text not null check (kind in ('restaurant','hotel','venue','artist')),
  partner_name text not null,
  offer text not null,                  -- "Free espresso with any pre-show order"
  details text,                         -- how to redeem, walking time, etc.
  url text,                             -- reservation / booking / code link
  venue_slugs text[] not null default '{}',
  tour_slug text,                       -- artist perks
  starts_on date, ends_on date,
  status text not null default 'draft' check (status in ('draft','live','paused')),
  address text, lat double precision, lng double precision,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists perks_live on perks (status) where status = 'live';

-- Claims in flight: a venue proves it owns its page with a work-domain email.
create table if not exists venue_claims (
  id uuid primary key default gen_random_uuid(),
  venue_slug text not null,
  email text not null,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at timestamptz not null default now()
);

-- Row level security: members read/write their org's rows; public reads happen
-- through the partner-content function with the service key, never directly.
alter table partner_orgs enable row level security;
alter table partner_members enable row level security;
alter table venue_overrides enable row level security;
alter table stage_times enable row level security;
alter table perks enable row level security;
alter table venue_claims enable row level security;

create policy "members see own orgs" on partner_orgs for select using (id in (select org_id from partner_members where user_id = auth.uid()));
create policy "members see memberships" on partner_members for select using (user_id = auth.uid());
create policy "venue members edit overrides" on venue_overrides for all using (venue_slug in (select o.venue_slug from partner_orgs o join partner_members m on m.org_id=o.id where m.user_id=auth.uid()));
create policy "venue members edit stage times" on stage_times for all using (venue_slug in (select o.venue_slug from partner_orgs o join partner_members m on m.org_id=o.id where m.user_id=auth.uid()));
create policy "org members edit perks" on perks for all using (org_id in (select org_id from partner_members where user_id = auth.uid()));
create policy "anyone can file a claim" on venue_claims for insert with check (true);
create policy "claimant sees own claim" on venue_claims for select using (email = auth.jwt()->>'email');

-- Reporting view: what happened at a venue / on a perk, from analytics_events.
create or replace view partner_report_monthly as
select
  coalesce(props->>'venue', '') as venue_slug,
  coalesce(props->>'partner', '') as partner,
  date_trunc('month', created_at) as month,
  count(*) filter (where event = 'show_saved') as shows_saved,
  count(*) filter (where event = 'venue_opened') as guide_opens,
  count(*) filter (where event = 'bagcheck_run') as bag_checks,
  count(*) filter (where event in ('parking_tap','rideshare_tap')) as arrival_taps,
  count(*) filter (where event = 'partner_impression') as perk_impressions,
  count(*) filter (where event in ('perks_opened','perk_tap')) as perk_taps
from analytics_events
group by 1,2,3;

-- Accuracy: fans and venues report a wrong fact with one tap. Read on Mondays.
create table if not exists info_reports (
  id uuid primary key default gen_random_uuid(),
  venue_slug text, tour_slug text, tm_event_id text,
  field text not null,            -- bagPolicy | parking | rideshare | ... | showTime | doors | headliner | setlist | distance | other
  message text,                   -- optional, 240 chars
  surface text not null default 'app',   -- app | web | console
  device_hash text,
  status text not null default 'open' check (status in ('open','fixed','dismissed')),
  created_at timestamptz not null default now()
);
create index if not exists info_reports_open on info_reports (status, created_at desc);
alter table info_reports enable row level security;
create policy "anyone can report" on info_reports for insert with check (true);

-- 2.6: fans report a wrong fact in one tap. Read on Mondays.
create table if not exists accuracy_reports (
  id uuid primary key default gen_random_uuid(),
  field text not null,
  venue_slug text, tour_slug text, event_id text,
  detail text, reason text not null check (reason in ('outdated','wrong','missing')),
  platform text,
  status text not null default 'open' check (status in ('open','fixed','dismissed')),
  created_at timestamptz not null default now()
);
alter table accuracy_reports enable row level security;
create policy "anyone can file an accuracy report" on accuracy_reports for insert with check (true);
