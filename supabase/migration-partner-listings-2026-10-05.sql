-- Partner listings: a paying restaurant or hotel appears in Concerto (Perks page,
-- venue pages, badges in Your Night) whether or not it has a live Perk.
-- Apply after migration-perk-review-2026-09-21.sql. Additive and safe to re-run.
-- Only an administrator (service role / SQL editor) sets listed, plan, and dates;
-- the existing member policies do not allow members to update partner_orgs.
begin;
alter table public.partner_orgs add column if not exists venue_slugs text[] not null default '{}';
alter table public.partner_orgs add column if not exists address text;
alter table public.partner_orgs add column if not exists url text;          -- website or reservation link
alter table public.partner_orgs add column if not exists blurb text;
alter table public.partner_orgs add column if not exists lat double precision;  -- for the card photo
alter table public.partner_orgs add column if not exists lng double precision;        -- one line for fans, e.g. "Wood-fired Latin kitchen, 4 min walk"
alter table public.partner_orgs add column if not exists listed boolean not null default false;
alter table public.partner_orgs add column if not exists listed_from date;
alter table public.partner_orgs add column if not exists listed_until date; -- end of the paid period; extend on each renewal
create index if not exists partner_orgs_listed on public.partner_orgs (listed) where listed;
commit;

-- Example: list a restaurant partner at one venue for a paid month.
-- update public.partner_orgs
--    set kind = 'restaurant', plan = 'paid', listed = true,
--        venue_slugs = array['american-airlines-center'],
--        address = '2700 Olive St, Dallas, TX 75201',
--        url = 'https://www.tedeseo.com/',
--        blurb = 'Latin kitchen with a rooftop, a short walk from the arena',
--        lat = 32.7884, lng = -96.8058,
--        listed_from = current_date, listed_until = current_date + 31
--  where name = 'Te Deseo';
