-- outreach_leads: first-touch message queue for ContractForge outreach.
-- Status lifecycle: drafted → approved → sent
-- Nothing sends automatically. Human approval required at each step.

create table if not exists outreach_leads (
    id               uuid primary key default gen_random_uuid(),
    name             text not null,
    handle           text,
    platform         text check (platform in ('x', 'email', 'linkedin')),
    fit_context      text,
    status           text not null default 'drafted'
                       check (status in ('drafted', 'approved', 'sent')),
    draft_message    text,
    approved_at      timestamptz,
    sent_at          timestamptz,
    reply_received   boolean not null default false,
    follow_up_draft  text,
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now()
);

create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger outreach_leads_updated_at
    before update on outreach_leads
    for each row execute function update_updated_at();

-- RLS: service role only — not exposed to end users
alter table outreach_leads enable row level security;
