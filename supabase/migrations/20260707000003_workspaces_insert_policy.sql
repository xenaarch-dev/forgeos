-- Fix: workspaces (20260707000000_app_foundations.sql) only had a SELECT
-- policy for authenticated users. completeOnboarding (web/app/onboarding/
-- actions.ts) creates the single shared workspace on first onboarding via
-- the normal user-session client, not the service role — with no INSERT
-- policy, that insert was being silently denied by RLS for every user,
-- including the very first one to onboard.
--
-- Per the original migration's own documented stance (single shared
-- workspace today, per-workspace isolation explicitly out of scope until
-- a second real workspace exists), any authenticated user may create it.

create policy "workspaces_insert_authenticated"
    on workspaces for insert
    to authenticated
    with check (true);
