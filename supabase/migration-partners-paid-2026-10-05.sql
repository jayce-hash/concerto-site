-- Concerto Partners: paid only. Apply after migration-perk-review-2026-09-21.sql.
-- Safe to re-run. Nothing here deletes data.
--
-- What it does:
--   1. Adds what a partner card needs (venues, address, link, blurb, location).
--   2. Adds 'pending' (signed up, not paid) as the default plan. Nothing is
--      public unless plan = 'paid'; Stripe sets that automatically on payment.
--   3. Stores the Stripe subscription so renewals and cancellations update the
--      partner on their own.
begin;
alter table public.partner_orgs add column if not exists venue_slugs text[] not null default '{}';
alter table public.partner_orgs add column if not exists address text;
alter table public.partner_orgs add column if not exists url text;            -- reservation or website link
alter table public.partner_orgs add column if not exists blurb text;          -- one line for fans
alter table public.partner_orgs add column if not exists lat double precision;
alter table public.partner_orgs add column if not exists lng double precision;
alter table public.partner_orgs add column if not exists listed boolean not null default false;
alter table public.partner_orgs add column if not exists listed_from date;
alter table public.partner_orgs add column if not exists listed_until date;   -- set by Stripe: end of paid period + 3 days
alter table public.partner_orgs add column if not exists stripe_subscription_id text;
alter table public.partner_orgs add column if not exists billing_interval text; -- 'month' or 'year'

alter table public.partner_orgs drop constraint if exists partner_orgs_plan_check;
alter table public.partner_orgs add constraint partner_orgs_plan_check
  check (plan in ('pending','paid','cancelled','founding','trial'));
alter table public.partner_orgs alter column plan set default 'pending';

create index if not exists partner_orgs_listed on public.partner_orgs (listed) where listed;
create unique index if not exists partner_orgs_stripe_sub on public.partner_orgs (stripe_subscription_id) where stripe_subscription_id is not null;
commit;

-- STEP 2 (run on its own after reviewing): see every existing partner first.
--   select id, kind, name, plan, plan_until, venue_slug, created_at from public.partner_orgs order by created_at;
--
-- STEP 3: end free plans. Founding/trial partners keep their Console login and
-- their drafts, but nothing of theirs is public until they pay.
--   update public.partner_orgs set plan = 'pending', plan_until = null where plan in ('founding','trial');
