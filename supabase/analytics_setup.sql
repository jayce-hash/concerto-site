-- Concerto analytics: run this once in the Supabase SQL Editor
-- (Dashboard -> SQL Editor -> New query -> paste -> Run).
--
-- Security note that matters: the app ships a PUBLIC anon key, so
-- this table allows INSERT only. There is deliberately NO select
-- policy, which means nobody can read your analytics through the
-- API even with the anon key. You read it here in the SQL Editor,
-- where you're authenticated as the owner.

create table if not exists public.analytics_events (
  id          bigserial primary key,
  device_id   text not null,
  user_id     uuid references auth.users(id) on delete set null,
  event       text not null,
  props       jsonb not null default '{}'::jsonb,
  app_version text,
  platform    text,
  created_at  timestamptz not null default now()
);

create index if not exists analytics_events_event_idx   on public.analytics_events (event, created_at desc);
create index if not exists analytics_events_device_idx  on public.analytics_events (device_id, created_at desc);

alter table public.analytics_events enable row level security;

drop policy if exists "clients may insert events" on public.analytics_events;
create policy "clients may insert events"
  on public.analytics_events for insert
  to anon, authenticated
  with check (true);

-- No SELECT/UPDATE/DELETE policies on purpose. Read below instead.


-- ============================================================
-- THE QUERIES THAT ANSWER REAL QUESTIONS
-- Paste any of these into the SQL Editor whenever you want.
-- ============================================================

-- 1. Daily active devices, last 30 days. The headline number.
-- select date_trunc('day', created_at)::date as day,
--        count(distinct device_id) as active_devices
-- from analytics_events
-- where created_at > now() - interval '30 days'
-- group by 1 order by 1 desc;

-- 2. ACTIVATION: what share of people who open the app save a show?
--    This is the single most important number you have, because
--    saving a show is what turns Concerto into a habit.
-- with opens as (select distinct device_id from analytics_events where event = 'app_open'),
--      savers as (select distinct device_id from analytics_events where event = 'show_saved')
-- select (select count(*) from opens) as opened,
--        (select count(*) from savers) as saved_a_show,
--        round(100.0 * (select count(*) from savers) / nullif((select count(*) from opens),0), 1) as activation_pct;

-- 3. RETENTION: devices that came back on a later day.
-- select days_active, count(*) as devices from (
--   select device_id, count(distinct date_trunc('day', created_at)) as days_active
--   from analytics_events group by 1
-- ) t group by 1 order by 1;

-- 4. Which venues actually get opened (tells you where to invest
--    in verified data and photography).
-- select props->>'slug' as venue, count(*) as views
-- from analytics_events where event = 'venue_viewed'
-- group by 1 order by 2 desc limit 25;

-- 5. Are the paid features being used, and do they work?
-- select event, count(*) from analytics_events
-- where event in ('bag_check_completed','plan_generated') group by 1;
-- select props->>'verdict' as verdict, count(*) from analytics_events
-- where event = 'bag_check_completed' group by 1;

-- 6. Housekeeping: keep the table small (run occasionally).
-- delete from analytics_events where created_at < now() - interval '180 days';
