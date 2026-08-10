-- Agent mesh persistence: command_threads + artifacts.
-- Follows outreach_leads.sql / app_foundations.sql conventions: snake_case,
-- check-constrained enums, update_updated_at trigger, RLS enabled with
-- explicit policies.
--
-- Multi-tenancy note: same single-workspace posture as app_foundations.sql
-- (SPEC_AgentMesh.md §2 non-goals). RLS grants every authenticated user read
-- access to every row. There is exactly one real workspace today and
-- isolating a second one is out of scope until it exists. Writes come from
-- the Python mesh via the service-role key, which bypasses RLS entirely —
-- so no insert/update policies are defined here on purpose.
--
-- The check constraints below are the SQL mirror of mesh/models.py:
--   routed_capability  <- Capability          (closed routing enum, §3a)
--   artifacts.status   <- ArtifactStatus      (§7a)
--   artifact_type      <- ArtifactType        (§7a)
-- Keep them in step: a value legal in one and not the other is a bug.

-- command_threads: one row per founder command, created on submit and
-- updated as routing and execution progress.
create table if not exists command_threads (
    id                 uuid primary key default gen_random_uuid(),
    command_id         text not null unique,
    user_id            uuid references auth.users(id) on delete set null,
    input_text         text not null,
    routed_capability  text check (routed_capability in
                           ('contract', 'outreach', 'spec', 'build',
                            'clarify', 'unsupported')),
    confidence         numeric check (confidence >= 0 and confidence <= 1),
    status             text not null default 'running'
                         check (status in ('running', 'success', 'failed',
                                           'clarify', 'unsupported', 'unwired')),
    workdir            text,
    detail             text,
    error              text,
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now()
);

alter table command_threads enable row level security;

create policy "command_threads_select_authenticated"
    on command_threads for select
    to authenticated
    using (true);

create trigger command_threads_updated_at
    before update on command_threads
    for each row execute function update_updated_at();

create index if not exists command_threads_created_at_idx
    on command_threads (created_at desc);

create index if not exists command_threads_command_id_idx
    on command_threads (command_id);

-- artifacts: the reviewable output of a capability run. Schema is §7a
-- verbatim, with command_id pointing at command_threads.
-- parent_artifact_id carries revision lineage (§7d): a revision is a new row
-- whose parent moves to 'revision_requested', so history is preserved rather
-- than overwritten.
create table if not exists artifacts (
    id                  uuid primary key default gen_random_uuid(),
    command_id          uuid not null references command_threads(id) on delete cascade,
    parent_artifact_id  uuid references artifacts(id) on delete set null,
    agent               text not null,
    artifact_type       text not null check (artifact_type in
                            ('CONTRACT', 'SPEC', 'EMAIL', 'PROPOSAL')),
    title               text not null,
    body                text not null,
    status              text not null default 'pending'
                        check (status in ('pending', 'approved',
                                          'revision_requested', 'rejected')),
    workdir_path        text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

alter table artifacts enable row level security;

create policy "artifacts_select_authenticated"
    on artifacts for select
    to authenticated
    using (true);

create trigger artifacts_updated_at
    before update on artifacts
    for each row execute function update_updated_at();

create index if not exists artifacts_command_id_idx
    on artifacts (command_id, created_at desc);

create index if not exists artifacts_status_idx
    on artifacts (status, created_at desc);
