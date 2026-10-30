-- Dickies Arena is now Ariat Arena (Oct 2026). Point partner listings and fans' favorites at the new slug.
update public.partner_orgs set venue_slugs = array_replace(venue_slugs, 'dickies-arena', 'ariat-arena') where 'dickies-arena' = any(venue_slugs);
update public.profiles set favorite_venues = array_replace(favorite_venues, 'dickies-arena', 'ariat-arena') where 'dickies-arena' = any(favorite_venues);
-- Check: both should return 0
select count(*) as partners_on_old_slug from public.partner_orgs where 'dickies-arena' = any(venue_slugs);
select count(*) as favorites_on_old_slug from public.profiles where 'dickies-arena' = any(favorite_venues);
