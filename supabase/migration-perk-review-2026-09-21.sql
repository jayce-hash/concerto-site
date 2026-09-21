-- Apply after migration-partners-2026-09-18.sql.
-- Members submit drafts; only a trusted administrator/service role publishes.
-- Existing offers are retained. Re-running this migration is safe.
begin;
drop policy if exists "org members edit perks" on public.perks;
drop policy if exists "members read own perks" on public.perks;
drop policy if exists "members submit draft perks" on public.perks;
drop policy if exists "members revise draft perks" on public.perks;
create policy "members read own perks" on public.perks for select to authenticated
using (org_id in (select org_id from public.partner_members where user_id = auth.uid()));
create policy "members submit draft perks" on public.perks for insert to authenticated
with check (status = 'draft' and org_id in (
  select m.org_id from public.partner_members m join public.partner_orgs o on o.id = m.org_id
  where m.user_id = auth.uid() and o.plan <> 'cancelled'
) and length(trim(offer)) > 0 and length(trim(details)) > 0
  and starts_on is not null and ends_on is not null and starts_on <= ends_on
  and (cardinality(venue_slugs) > 0 or nullif(trim(tour_slug), '') is not null));
create policy "members revise draft perks" on public.perks for update to authenticated
using (status = 'draft' and org_id in (select org_id from public.partner_members where user_id = auth.uid()))
with check (status = 'draft' and org_id in (
  select m.org_id from public.partner_members m join public.partner_orgs o on o.id = m.org_id
  where m.user_id = auth.uid() and o.plan <> 'cancelled'
) and length(trim(offer)) > 0 and length(trim(details)) > 0
  and starts_on is not null and ends_on is not null and starts_on <= ends_on
  and (cardinality(venue_slugs) > 0 or nullif(trim(tour_slug), '') is not null));
commit;
