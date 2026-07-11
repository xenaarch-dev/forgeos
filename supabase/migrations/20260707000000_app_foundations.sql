-- App foundations: workspaces, profiles, agent_logs, product_metrics.
-- Follows outreach_leads.sql conventions: snake_case, check-constrained
-- enums, updated_at trigger, RLS enabled with explicit policies.
--
-- Multi-tenancy note (PRD v8 §6 non-goal): workspaces exists so the UI's
-- workspace switcher has a real table to point at, but RLS below grants
-- every authenticated user read access to every workspace/agent_logs/
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

-- agent_logs: every agent action. Written by the Python pipeline via the
-- service-role key; read by authenticated founders (War Room stream,
-- Agents detail drawer, Artifacts feed all read this same table).
create table if not exists agent_logs (
    id          uuid primary key default gen_random_uuid(),
    agent       text not null,
    event_type  text not null check (event_type in ('info', 'action', 'gate', 'error')),
    message     text not null,
    metadata    jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);

alter table agent_logs enable row level security;

create policy "agent_logs_select_authenticated"
    on agent_logs for select
    to authenticated
    using (true);

create index if not exists agent_logs_created_at_idx on agent_logs (created_at desc);

-- Required for Supabase Realtime subscriptions (War Room Activity Stream).
alter publication supabase_realtime add table agent_logs;

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
