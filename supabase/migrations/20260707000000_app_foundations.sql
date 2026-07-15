-- App foundations: workspaces, profiles, dashboard_events, product_metrics.
-- Follows outreach_leads.sql conventions: snake_case, check-constrained
-- enums, updated_at trigger, RLS enabled with explicit policies.
--
-- Naming note: a table literally named agent_logs already exists in this
-- Supabase project with a different, incompatible schema (agent_name,
-- run_at, status, summary, error_message, duration_ms) and no application
-- code anywhere in this repo reads or writes it (verified by grep across
-- the full repo, all worktrees, and every generated build/ output). It is
-- left untouched here — this migration deliberately uses dashboard_events
-- instead of agent_logs to avoid colliding with that pre-existing table.
--
-- Multi-tenancy note (PRD v8 §6 non-goal): workspaces exists so the UI's
-- workspace switcher has a real table to point at, but RLS below grants
-- every authenticated user read access to every workspace/dashboard_events/
-- product_metrics row — there is exactly one real workspace today, and
-- isolating a second one is explicitly out of scope until it exists.

create table if not exists workspaces (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    created_at  timestamptz not null default now()
);

alter table workspaces enable row level security;

create policy "workspaces_select_authenticated"
    on workspaces for select
    to authenticated
    using (true);

-- profiles: one row per auth.users, links a founder to a workspace.
create table if not exists profiles (
    id            uuid primary key references auth.users(id) on delete cascade,
    workspace_id  uuid references workspaces(id) on delete set null,
    full_name     text,
    company_name  text,
    onboarded_at  timestamptz,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

alter table profiles enable row level security;

create policy "profiles_select_own"
    on profiles for select
    to authenticated
    using (auth.uid() = id);

create policy "profiles_insert_own"
    on profiles for insert
    to authenticated
    with check (auth.uid() = id);

create policy "profiles_update_own"
    on profiles for update
    to authenticated
    using (auth.uid() = id)
    with check (auth.uid() = id);

create trigger profiles_updated_at
    before update on profiles
    for each row execute function update_updated_at();

-- dashboard_events: every agent action. Written by the Python pipeline via the
-- service-role key; read by authenticated founders (War Room stream,
-- Agents detail drawer, Artifacts feed all read this same table).
create table if not exists dashboard_events (
    id          uuid primary key default gen_random_uuid(),
    agent       text not null,
    event_type  text not null check (event_type in ('info', 'action', 'gate', 'error')),
    message     text not null,
    metadata    jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);

alter table dashboard_events enable row level security;

create policy "dashboard_events_select_authenticated"
    on dashboard_events for select
    to authenticated
    using (true);

create index if not exists dashboard_events_created_at_idx on dashboard_events (created_at desc);

-- Required for Supabase Realtime subscriptions (War Room Activity Stream).
alter publication supabase_realtime add table dashboard_events;

-- product_metrics: MRR/signups/conversions snapshots per product.
create table if not exists product_metrics (
    id            uuid primary key default gen_random_uuid(),
    product_slug  text not null,
    mrr_inr       integer not null default 0,
    signups       integer not null default 0,
    conversions   integer not null default 0,
    recorded_at   timestamptz not null default now()
);

alter table product_metrics enable row level security;

create policy "product_metrics_select_authenticated"
    on product_metrics for select
    to authenticated
    using (true);

create index if not exists product_metrics_recorded_at_idx
    on product_metrics (product_slug, recorded_at desc);
