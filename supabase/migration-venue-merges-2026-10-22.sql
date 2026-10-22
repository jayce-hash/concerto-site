-- One page per building (Oct 22, 2026): five venues listed twice under an old and a new name were merged.
-- Point partner listings and fans' favorite venues at the slug that remains. Safe to run more than once.

create temporary table venue_renames (old text primary key, new text not null);
insert into venue_renames values
  ('amalie-arena', 'benchmark-international-arena'),
  ('xcel-energy-center', 'grand-casino-arena'),
  ('phx-arena', 'mortgage-matchup-center'),
  ('thompson-boling-arena', 'food-city-center'),
  ('rocket-mortgage-fieldhouse', 'rocket-arena');

-- Partner listings (venue_slugs text[])
update public.partner_orgs p
set venue_slugs = (
  select coalesce(array_agg(distinct coalesce(r.new, s)), '{}')
  from unnest(p.venue_slugs) s left join venue_renames r on r.old = s
)
where p.venue_slugs && (select array_agg(old) from venue_renames);

-- Fans' favorite venues (favorite_venues text[])
update public.profiles p
set favorite_venues = (
  select coalesce(array_agg(distinct coalesce(r.new, s)), '{}')
  from unnest(p.favorite_venues) s left join venue_renames r on r.old = s
)
where p.favorite_venues && (select array_agg(old) from venue_renames);

-- Check: both should return 0
select count(*) as partners_on_old_slugs from public.partner_orgs where venue_slugs && (select array_agg(old) from venue_renames);
select count(*) as favorites_on_old_slugs from public.profiles where favorite_venues && (select array_agg(old) from venue_renames);
