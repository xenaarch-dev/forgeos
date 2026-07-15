# ForgeOS App Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the prerequisites every other PRD v8 screen depends on — Supabase schema, auth, onboarding, and the app shell — and ship the first real screen (`/app`, the War Room Dashboard) wired to live data, so `/app/products`, `/app/agents`, etc. have something to be nested inside.

**Architecture:** Next.js 14 App Router inside `web/` (the live, deployed app — confirmed target, not the abandoned `forgeos-ui/`). Auth via Supabase Auth (email magic link, `@supabase/ssr` for cookie-based SSR sessions). A `middleware.ts` gate protects `/app/*` and `/onboarding`, driven by a pure, unit-tested redirect-decision function. New Supabase tables (`workspaces`, `profiles`, `dashboard_events`, `product_metrics`) follow the existing `outreach_leads` migration's conventions exactly (snake_case, `check` constraints for enums, `updated_at` triggers, RLS). The dashboard ports the *structure* of `ForgeOS_War_Room_dc.html` (glass panel recipe, sigil rig, bot-avatar rig, roster/stream/metrics layout) but retints every color to the live, locked Cosmic Garden tokens in `web/app/globals.css` — never the ice-blue values from the source file.

**Tech Stack:** Next.js 14.2.35 (App Router), React 18, TypeScript, Tailwind, `@supabase/supabase-js` + `@supabase/ssr` (new), Vitest (new — this repo has zero JS test tooling today; added here for pure-logic units only). Package manager is **pnpm** (confirmed via `web/pnpm-lock.yaml` — no `package-lock.json` in `web/`, despite `forgeos-ui/` and CLAUDE.md defaulting to npm elsewhere).

**Testing philosophy for this plan:** `web/` has no automated JS tests today — this project's own convention (see STATE.md Day 174-176) verifies UI via `pnpm build` (type-check) plus manual/browser walkthrough, not unit tests. This plan keeps that convention for UI components and thin SDK wrappers (no test would exercise real logic), but adds real TDD-with-Vitest for the handful of files that contain actual branching logic: the auth-redirect decision, the onboarding-step validator, and the agent status→color mapping. Don't add tests to files that are pure JSX/markup — that's test theater, not coverage.

---

## Scope note

The full PRD v8 covers ~10 independent screens (Dashboard, Products, Pipeline, Agents, Artifacts, Command, Billing, Settings, workspace switcher) plus auth. Per the writing-plans scope check, that's multiple independent subsystems and shouldn't be forced into one plan. **This plan covers only the foundation layer**: schema, auth, onboarding, app shell, and the Dashboard screen (the one screen that has no dependencies on any other screen). Each of the remaining screens gets its own plan, written just before it's built, once you've seen how the foundation actually turned out. A rough shape of what's left is sketched at the bottom of this file — not detailed, not to be executed as-is.

---

## Task 1: Database schema — workspaces, profiles, dashboard_events, product_metrics

**Files:**
- Create: `supabase/migrations/20260707000000_app_foundations.sql`

- [ ] **Step 1: Write the migration**

```sql
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
```

- [ ] **Step 2: Apply the migration**

This repo has no linked Supabase CLI (`supabase/config.toml` doesn't exist) — `outreach_leads.sql` was applied the same way this one should be: paste into the Supabase Dashboard's SQL editor for the project and run it. There is no local command that applies this automatically.

Verify by running in the SQL editor afterward:
```sql
select table_name from information_schema.tables
where table_schema = 'public'
  and table_name in ('workspaces', 'profiles', 'dashboard_events', 'product_metrics');
```
Expected: all 4 rows returned.

**Follow-up fix (found during Task 5 review):** this migration only grants `workspaces` a SELECT policy for `authenticated` — no INSERT. Task 5's `completeOnboarding` creates the shared workspace on first onboarding via the normal user-session client, so that insert was being silently denied by RLS for every user. Fixed in a separate migration, `20260707000003_workspaces_insert_policy.sql`:

```sql
create policy "workspaces_insert_authenticated"
    on workspaces for insert
    to authenticated
    with check (true);
```

Apply this one too via the Supabase SQL editor, same as the rest.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/20260707000000_app_foundations.sql
git commit -m "feat(db): add workspaces, profiles, dashboard_events, product_metrics tables"
```

---

## Task 2: Vitest + pure logic units (redirect decision, onboarding validation, agent roster)

**Files:**
- Modify: `web/package.json`
- Create: `web/vitest.config.ts`
- Create: `web/lib/auth/redirect.ts`
- Test: `web/lib/auth/redirect.test.ts`
- Create: `web/lib/onboarding/validate.ts`
- Test: `web/lib/onboarding/validate.test.ts`
- Create: `web/lib/agents/roster.ts`
- Test: `web/lib/agents/roster.test.ts`

- [ ] **Step 1: Add Vitest**

```bash
cd web
pnpm add -D vitest
```

- [ ] **Step 2: Add the test script and Vitest config**

Edit `web/package.json` scripts block:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  }
}
```

Create `web/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
  },
})
```

- [ ] **Step 3: Write the failing test for the auth redirect decision**

```ts
// web/lib/auth/redirect.test.ts
import { describe, expect, it } from 'vitest'
import { getRedirectPath } from './redirect'

describe('getRedirectPath', () => {
  it('sends unauthenticated users hitting /app to /login', () => {
    expect(getRedirectPath({ session: false, onboarded: false, pathname: '/app' })).toBe('/login')
  })

  it('sends unauthenticated users hitting /onboarding to /login', () => {
    expect(getRedirectPath({ session: false, onboarded: false, pathname: '/onboarding' })).toBe('/login')
  })

  it('does not redirect unauthenticated users on public marketing pages', () => {
    expect(getRedirectPath({ session: false, onboarded: false, pathname: '/' })).toBeNull()
  })

  it('sends authenticated, un-onboarded users hitting /app to /onboarding', () => {
    expect(getRedirectPath({ session: true, onboarded: false, pathname: '/app/products' })).toBe('/onboarding')
  })

  it('sends authenticated, onboarded users away from /login to /app', () => {
    expect(getRedirectPath({ session: true, onboarded: true, pathname: '/login' })).toBe('/app')
  })

  it('does not redirect authenticated, onboarded users already inside /app', () => {
    expect(getRedirectPath({ session: true, onboarded: true, pathname: '/app/agents' })).toBeNull()
  })
})
```

- [ ] **Step 4: Run it to verify it fails**

Run: `pnpm --dir web test`
Expected: FAIL — `Cannot find module './redirect'`

- [ ] **Step 5: Implement**

```ts
// web/lib/auth/redirect.ts
const PUBLIC_ONLY_PATHS = ['/login', '/signup']
const GATED_PREFIXES = ['/app', '/onboarding']

export type RedirectInput = {
  session: boolean
  onboarded: boolean
  pathname: string
}

export function getRedirectPath({ session, onboarded, pathname }: RedirectInput): string | null {
  const isGated = GATED_PREFIXES.some((p) => pathname.startsWith(p))
  const isPublicOnly = PUBLIC_ONLY_PATHS.some((p) => pathname.startsWith(p))

  if (!session) {
    return isGated ? '/login' : null
  }
  if (isPublicOnly) {
    return '/app'
  }
  if (pathname.startsWith('/app') && !onboarded) {
    return '/onboarding'
  }
  return null
}
```

- [ ] **Step 6: Run it to verify it passes**

Run: `pnpm --dir web test`
Expected: PASS (6/6)

- [ ] **Step 7: Write the failing test for onboarding step validation**

```ts
// web/lib/onboarding/validate.test.ts
import { describe, expect, it } from 'vitest'
import { validateStep } from './validate'

describe('validateStep', () => {
  it('rejects an empty name', () => {
    expect(validateStep('name', '  ')).toBe('This field is required.')
  })

  it('accepts a normal name', () => {
    expect(validateStep('name', 'Xena')).toBeNull()
  })

  it('rejects a name over 120 characters', () => {
    expect(validateStep('name', 'a'.repeat(121))).toBe('Keep it under 120 characters.')
  })

  it('never rejects the idea step, including empty (skip covers it)', () => {
    expect(validateStep('idea', '')).toBeNull()
  })
})
```

- [ ] **Step 8: Run it to verify it fails**

Run: `pnpm --dir web test`
Expected: FAIL — `Cannot find module './validate'`

- [ ] **Step 9: Implement**

```ts
// web/lib/onboarding/validate.ts
export type OnboardingStep = 'name' | 'company' | 'idea'

export function validateStep(step: OnboardingStep, value: string): string | null {
  if (step === 'idea') return null
  const trimmed = value.trim()
  if (trimmed.length === 0) return 'This field is required.'
  if (trimmed.length > 120) return 'Keep it under 120 characters.'
  return null
}
```

- [ ] **Step 10: Run it to verify it passes**

Run: `pnpm --dir web test`
Expected: PASS (4/4)

- [ ] **Step 11: Write the failing test for agent status→dot-color mapping**

```ts
// web/lib/agents/roster.test.ts
import { describe, expect, it } from 'vitest'
import { AGENT_ROSTER, statusDotColor } from './roster'

describe('statusDotColor', () => {
  it('returns the agent accent when running', () => {
    expect(statusDotColor('running', '#00E5CC')).toBe('#00E5CC')
  })

  it('returns a dim neutral when queued', () => {
    expect(statusDotColor('queued', '#00E5CC')).toBe('rgba(240,237,232,0.35)')
  })

  it('returns a dimmer neutral when idle', () => {
    expect(statusDotColor('idle', '#00E5CC')).toBe('rgba(240,237,232,0.15)')
  })
})

describe('AGENT_ROSTER', () => {
  it('has exactly 7 agents, matching the PRD roster', () => {
    expect(AGENT_ROSTER).toHaveLength(7)
  })

  it('uses only Cosmic Garden accents, no ice-blue leftover from the mockup', () => {
    const iceBlue = '#A4D8FF'
    expect(AGENT_ROSTER.some((a) => a.accent === iceBlue)).toBe(false)
  })
})
```

- [ ] **Step 12: Run it to verify it fails**

Run: `pnpm --dir web test`
Expected: FAIL — `Cannot find module './roster'`

- [ ] **Step 13: Implement**

```ts
// web/lib/agents/roster.ts
export type AgentStatus = 'running' | 'idle' | 'queued'

export type AgentDefinition = {
  slug: string
  name: string
  accent: string
  defaultStatus: AgentStatus
}

// Cosmic Garden accents only (teal/gold/violet/azure family) — never the
// ice-blue (#A4D8FF) values from ForgeOS_War_Room_dc.html's source markup.
export const AGENT_ROSTER: AgentDefinition[] = [
  { slug: 'outreach',   name: 'OutreachForge',   accent: '#00E5CC', defaultStatus: 'running' },
  { slug: 'contract',   name: 'ContractForge',   accent: '#3B82F6', defaultStatus: 'running' },
  { slug: 'core',       name: 'ForgeOS Core',    accent: '#7C3AED', defaultStatus: 'running' },
  { slug: 'spec',       name: 'SpecForge',       accent: '#00C2AB', defaultStatus: 'idle' },
  { slug: 'reputation', name: 'ReputationForge', accent: '#5B8DEF', defaultStatus: 'queued' },
  { slug: 'nightly',    name: 'NightlyAgent',    accent: '#9061E0', defaultStatus: 'queued' },
  { slug: 'client',     name: 'ClientForge',     accent: '#E8961F', defaultStatus: 'idle' },
]

export function statusDotColor(status: AgentStatus, accent: string): string {
  if (status === 'running') return accent
  if (status === 'queued') return 'rgba(240,237,232,0.35)'
  return 'rgba(240,237,232,0.15)'
}
```

- [ ] **Step 14: Run it to verify it passes**

Run: `pnpm --dir web test`
Expected: PASS (5/5)

- [ ] **Step 15: Commit**

```bash
git add web/package.json web/pnpm-lock.yaml web/vitest.config.ts web/lib/auth/redirect.ts web/lib/auth/redirect.test.ts web/lib/onboarding/validate.ts web/lib/onboarding/validate.test.ts web/lib/agents/roster.ts web/lib/agents/roster.test.ts
git commit -m "test(web): add vitest + TDD units for auth redirect, onboarding validation, agent roster"
```

---

## Task 3: Supabase clients + auth middleware

**Files:**
- Modify: `web/package.json`
- Create: `web/lib/supabase/client.ts`
- Create: `web/lib/supabase/server.ts`
- Create: `web/middleware.ts`

- [ ] **Step 1: Add the Supabase SSR packages**

```bash
cd web
pnpm add @supabase/supabase-js @supabase/ssr
```

- [ ] **Step 2: Add env vars**

Create `web/.env.local` (already gitignored via `.env*.local` in `web/.gitignore`) with the project's anon-safe values (get these from the Supabase Dashboard → Settings → API — same project the existing `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` in the metrics route already point at):

```
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
```

Also add both to the Vercel project's Environment Variables (Production + Preview) via the dashboard — this is a manual step outside this repo, not something to script.

- [ ] **Step 3: Browser client**

```ts
// web/lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

- [ ] **Step 4: Server client**

```ts
// web/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export function createClient() {
  const cookieStore = cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {
            // Called from a Server Component render — middleware below
            // refreshes the session on every request instead.
          }
        },
      },
    }
  )
}
```

No test for these two files — they're thin SDK wrappers with zero branching logic; `getRedirectPath` (Task 2) already covers the only real decision they feed into. Verified via `pnpm build` type-check plus the manual login walkthrough in Task 4.

- [ ] **Step 5: Middleware**

```ts
// web/middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import { getRedirectPath } from '@/lib/auth/redirect'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          response = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  let onboarded = false
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('onboarded_at')
      .eq('id', user.id)
      .maybeSingle()
    onboarded = Boolean(profile?.onboarded_at)
  }

  const redirect = getRedirectPath({
    session: Boolean(user),
    onboarded,
    pathname: request.nextUrl.pathname,
  })

  if (redirect) {
    const url = request.nextUrl.clone()
    url.pathname = redirect
    return NextResponse.redirect(url)
  }

  return response
}

export const config = {
  matcher: ['/app/:path*', '/onboarding/:path*', '/login', '/signup'],
}
```

- [ ] **Step 6: Verify the build compiles**

Run: `pnpm --dir web build`
Expected: build succeeds (this only type-checks — real behavior is verified in Task 4 once `/login` exists to redirect to).

- [ ] **Step 7: Commit**

```bash
git add web/package.json web/pnpm-lock.yaml web/lib/supabase/client.ts web/lib/supabase/server.ts web/middleware.ts
git commit -m "feat(web): add Supabase SSR clients and auth-gating middleware"
```

---

## Task 4: Login, signup, and magic-link callback

**Files:**
- Create: `web/components/auth/MagicLinkForm.tsx`
- Create: `web/app/login/page.tsx`
- Create: `web/app/signup/page.tsx`
- Create: `web/app/auth/callback/route.ts`

- [ ] **Step 1: Shared magic-link form**

Supabase's `signInWithOtp` creates the user on first send by default (`shouldCreateUser: true`), so login and signup are the same call — only the copy differs. One component, two thin pages, per PRD's "email + magic link, no password complexity theater."

```tsx
// web/components/auth/MagicLinkForm.tsx
'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export function MagicLinkForm({ mode }: { mode: 'login' | 'signup' }) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setStatus('sending')
    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    })
    setStatus(error ? 'error' : 'sent')
  }

  if (status === 'sent') {
    return (
      <div style={{ color: 'var(--w)', font: '400 14px var(--font-body)' }}>
        Check {email} for a sign-in link.
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <input
        type="email"
        required
        placeholder="you@company.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{
          background: 'var(--glass-fill)',
          border: '0.5px solid rgba(0,229,204,0.3)',
          borderRadius: 4,
          padding: '12px 14px',
          color: 'var(--w)',
          font: '400 14px var(--font-body)',
        }}
      />
      <button
        type="submit"
        disabled={status === 'sending'}
        style={{
          background: 'var(--teal)',
          color: 'var(--void)',
          borderRadius: 4,
          padding: '12px 14px',
          font: '700 12px var(--font-body)',
          letterSpacing: '0.08em',
        }}
      >
        {status === 'sending' ? 'SENDING…' : mode === 'login' ? 'SEND LOGIN LINK →' : 'SEND SIGNUP LINK →'}
      </button>
      {status === 'error' && (
        <div style={{ color: 'var(--gold)', font: '400 12px var(--font-body)' }}>
          Something went wrong sending the link. Try again.
        </div>
      )}
    </form>
  )
}
```

- [ ] **Step 2: Login and signup pages**

```tsx
// web/app/login/page.tsx
import { MagicLinkForm } from '@/components/auth/MagicLinkForm'

export default function LoginPage() {
  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--void)' }}>
      <div style={{ width: 360 }}>
        <h1 style={{ font: '900 28px var(--font-serif)', color: 'var(--w)', marginBottom: 24 }}>
          ForgeOS
        </h1>
        <MagicLinkForm mode="login" />
      </div>
    </main>
  )
}
```

```tsx
// web/app/signup/page.tsx
import { MagicLinkForm } from '@/components/auth/MagicLinkForm'

export default function SignupPage() {
  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--void)' }}>
      <div style={{ width: 360 }}>
        <h1 style={{ font: '900 28px var(--font-serif)', color: 'var(--w)', marginBottom: 24 }}>
          Start forging.
        </h1>
        <MagicLinkForm mode="signup" />
      </div>
    </main>
  )
}
```

- [ ] **Step 3: Callback route**

```ts
// web/app/auth/callback/route.ts
import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

// Guards against open redirect: a raw `next` value like "evil.com/x"
// concatenates with `origin` into a syntactically valid URL pointing at a
// different, attacker-registerable hostname (https://forgeos.appevil.com/x).
// Only a same-origin relative path is honored.
function safeNextPath(next: string | null): string {
  if (next && next.startsWith('/') && !next.startsWith('//')) {
    return next
  }
  return '/app'
}

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = safeNextPath(searchParams.get('next'))

  if (code) {
    const supabase = createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`)
    }
  }
  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`)
}
```

- [ ] **Step 4: Manual verification (no automated test — this is a real network+email round trip)**

Run: `pnpm --dir web dev`, open `http://localhost:3000/signup`, submit a real email you control, click the link in the email, confirm it lands on `/onboarding` (since the new user has no `onboarded_at` yet — this exercises the middleware from Task 3 end to end). Confirm hitting `/app` directly while logged out redirects to `/login`.

- [ ] **Step 5: Commit**

```bash
git add web/components/auth/MagicLinkForm.tsx web/app/login/page.tsx web/app/signup/page.tsx web/app/auth/callback/route.ts
git commit -m "feat(web): magic-link login/signup pages and auth callback route"
```

---

## Task 5: Onboarding flow (3 steps, skippable)

**Files:**
- Create: `web/app/onboarding/page.tsx`
- Create: `web/app/onboarding/actions.ts`
- Create: `web/components/onboarding/OnboardingStep.tsx`

- [ ] **Step 1: Server action to persist onboarding and mark it complete**

```ts
// web/app/onboarding/actions.ts
'use server'

import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import { validateStep } from '@/lib/onboarding/validate'

export async function completeOnboarding(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const fullName = String(formData.get('fullName') ?? '').trim()
  const companyName = String(formData.get('companyName') ?? '').trim()

  const nameError = validateStep('name', fullName)
  if (nameError) {
    redirect(`/onboarding?error=${encodeURIComponent(nameError)}`)
  }
  if (companyName) {
    const companyError = validateStep('company', companyName)
    if (companyError) {
      redirect(`/onboarding?error=${encodeURIComponent(companyError)}`)
    }
  }

  let { data: workspace } = await supabase
    .from('workspaces')
    .select('id')
    .limit(1)
    .maybeSingle()

  if (!workspace) {
    const { data: created } = await supabase
      .from('workspaces')
      .insert({ name: companyName || 'My Workspace' })
      .select('id')
      .single()
    workspace = created
  }

  await supabase.from('profiles').upsert({
    id: user.id,
    workspace_id: workspace?.id ?? null,
    full_name: fullName || null,
    company_name: companyName || null,
    onboarded_at: new Date().toISOString(),
  })

  redirect('/app')
}

export async function skipOnboarding() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  await supabase.from('profiles').upsert({
    id: user.id,
    onboarded_at: new Date().toISOString(),
  })

  redirect('/app')
}
```

- [ ] **Step 2: Onboarding page — 3 glass panels, one question each, skip always visible**

```tsx
// web/app/onboarding/page.tsx
import { completeOnboarding, skipOnboarding } from './actions'

export default function OnboardingPage({
  searchParams,
}: {
  searchParams: { error?: string }
}) {
  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--void)' }}>
      <form action={completeOnboarding} style={{ width: 420, display: 'flex', flexDirection: 'column', gap: 20 }}>
        {searchParams.error && (
          <div style={{ color: 'var(--gold)', font: '400 12px var(--font-body)' }}>
            {searchParams.error}
          </div>
        )}
        <div style={{
          background: 'var(--glass-fill)',
          backdropFilter: 'var(--glass-blur)',
          border: '0.5px solid rgba(0,229,204,0.22)',
          borderRadius: 6,
          padding: 24,
        }}>
          <label style={{ display: 'block', font: '400 10px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.14em', marginBottom: 10 }}>
            YOUR NAME
          </label>
          <input
            name="fullName"
            required
            maxLength={120}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid rgba(0,229,204,0.3)',
              color: 'var(--w)',
              font: '400 18px var(--font-body)',
              padding: '6px 0',
            }}
          />
        </div>
        <div style={{
          background: 'var(--glass-fill)',
          backdropFilter: 'var(--glass-blur)',
          border: '0.5px solid rgba(0,229,204,0.22)',
          borderRadius: 6,
          padding: 24,
        }}>
          <label style={{ display: 'block', font: '400 10px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.14em', marginBottom: 10 }}>
            COMPANY NAME
          </label>
          <input
            name="companyName"
            maxLength={120}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid rgba(0,229,204,0.3)',
              color: 'var(--w)',
              font: '400 18px var(--font-body)',
              padding: '6px 0',
            }}
          />
        </div>
        <div style={{
          background: 'var(--glass-fill)',
          backdropFilter: 'var(--glass-blur)',
          border: '0.5px solid rgba(0,229,204,0.22)',
          borderRadius: 6,
          padding: 24,
        }}>
          <label style={{ display: 'block', font: '400 10px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.14em', marginBottom: 10 }}>
            FIRST PRODUCT IDEA (FEEDS SPEC.MD GENERATION)
          </label>
          <textarea
            name="idea"
            rows={3}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid rgba(0,229,204,0.3)',
              color: 'var(--w)',
              font: '400 15px var(--font-body)',
              padding: '6px 0',
              resize: 'none',
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            type="submit"
            style={{ flex: 1, background: 'var(--teal)', color: 'var(--void)', borderRadius: 4, padding: 14, font: '700 12px var(--font-body)', letterSpacing: '0.08em' }}
          >
            CONTINUE →
          </button>
          <button
            formAction={skipOnboarding}
            style={{ background: 'transparent', border: '0.5px solid rgba(240,237,232,0.2)', color: 'var(--w-dim)', borderRadius: 4, padding: 14, font: '400 12px var(--font-body)' }}
          >
            SKIP
          </button>
        </div>
      </form>
    </main>
  )
}
```

Note: the PRD describes 3 *separate* single-question screens; this ships all 3 fields on one page with one submit for the first pass — genuinely splitting into 3 routed steps (`/onboarding/name` → `/onboarding/company` → `/onboarding/idea`) with client-side step state is a reasonable follow-up but isn't required for the skip-button and data-capture behavior the PRD actually specifies. Flag this simplification to the user when this task is reviewed.

- [ ] **Step 3: Manual verification**

Continue the Task 4 login flow: after landing on `/onboarding`, fill the form, submit, confirm redirect to `/app` and that `profiles.onboarded_at` is now set (check in Supabase Dashboard → Table Editor). Separately, create a second test user and click SKIP — confirm it also lands on `/app` with `onboarded_at` set but `full_name`/`company_name` null. Also submit the form with an empty name — confirm it redirects back to `/onboarding?error=This%20field%20is%20required.` and the error renders (this exercises the `validateStep` unit tested in Task 2 for real, server-side, not just via the browser's `required` attribute).

- [ ] **Step 4: Commit**

```bash
git add web/app/onboarding/page.tsx web/app/onboarding/actions.ts
git commit -m "feat(web): 3-question onboarding flow with skip"
```

---

## Task 6: App shell — glass panel, sigil, bot avatar, nav

**Files:**
- Create: `web/components/app-shell/GlassPanel.tsx`
- Create: `web/components/app-shell/Sigil.tsx`
- Create: `web/components/app-shell/BotAvatar.tsx`
- Create: `web/components/app-shell/Nav.tsx`
- Create: `web/app/app/layout.tsx`

- [ ] **Step 1: Reusable glass panel — the gradient-border + backdrop-filter + inset-shadow recipe from both source files, retinted**

```tsx
// web/components/app-shell/GlassPanel.tsx
import type { CSSProperties, ReactNode } from 'react'

export function GlassPanel({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div
      style={{
        borderRadius: 6,
        padding: 1,
        backgroundImage:
          'linear-gradient(#0000,#0000), linear-gradient(160deg, rgba(0,229,204,.5), rgba(240,237,232,.3) 50%, rgba(124,58,237,.3))',
        backgroundOrigin: 'border-box',
        backgroundClip: 'padding-box, border-box',
        ...style,
      }}
    >
      <div style={{ position: 'relative', borderRadius: 5, overflow: 'hidden', height: '100%' }}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backdropFilter: 'var(--glass-blur)',
            WebkitBackdropFilter: 'var(--glass-blur)',
            background: 'var(--glass-fill)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(160deg, rgba(255,255,255,.06), rgba(0,229,204,.02) 45%, rgba(0,0,0,.24))',
            boxShadow: 'inset 0 1px 1px rgba(255,255,255,.16), inset 0 -12px 20px rgba(0,0,0,.3)',
          }}
        />
        <div style={{ position: 'relative', zIndex: 2, height: '100%' }}>{children}</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Sigil — the concentric-ring system health mark, retinted to teal**

```tsx
// web/components/app-shell/Sigil.tsx
export function Sigil({ size = 34, glowIntensity = 0.4 }: { size?: number; glowIntensity?: number }) {
  const glow = Math.max(0, Math.min(1, glowIntensity))
  return (
    <svg
      viewBox="0 0 240 240"
      width={size}
      height={size}
      style={{
        animation: `ringspin ${Math.round(85 - glow * 65)}s linear infinite`,
        filter: `drop-shadow(0 0 ${Math.round(8 + glow * 30)}px rgba(0,229,204,${(0.08 + glow * 0.4).toFixed(2)}))`,
      }}
    >
      <circle cx="120" cy="120" r="104" fill="none" stroke="rgba(0,229,204,0.2)" strokeWidth="4" />
      <circle cx="120" cy="120" r="76" fill="none" stroke="rgba(0,229,204,0.35)" strokeWidth="4" strokeDasharray="6 20" />
      <circle cx="120" cy="120" r="18" fill="#00E5CC" opacity={(0.45 + glow * 0.5).toFixed(2)} />
    </svg>
  )
}
```

Add the keyframe once, globally:

```css
/* append to web/app/globals.css */
@keyframes ringspin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

- [ ] **Step 3: Bot avatar rig — antenna, blinking eyes, cursor-tracking pupils, retinted**

```tsx
// web/components/app-shell/BotAvatar.tsx
'use client'

import { useEffect, useRef } from 'react'

export function BotAvatar({ accent, size = 30, label }: { accent: string; size?: number; label?: string }) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!window.matchMedia('(pointer:fine)').matches) return
    const svg = svgRef.current
    if (!svg) return
    let raf: number | null = null
    const onMove = (e: MouseEvent) => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = null
        const r = svg.getBoundingClientRect()
        const dx = e.clientX - (r.left + r.width / 2)
        const dy = e.clientY - (r.top + r.height / 2)
        const d = Math.hypot(dx, dy) || 1
        const m = Math.min(2.4, d / 40)
        svg.querySelectorAll('[data-pupil]').forEach((p) => {
          p.setAttribute('transform', `translate(${((dx / d) * m).toFixed(1)},${((dy / d) * m).toFixed(1)})`)
        })
      })
    }
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [])

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <svg ref={svgRef} viewBox="0 0 64 64" width={size} height={size} style={{ flexShrink: 0, overflow: 'visible' }}>
        <line x1="32" y1="9" x2="32" y2="17" stroke={accent} strokeWidth="2" />
        <circle cx="32" cy="7" r="2.8" fill={accent} />
        <rect x="13" y="17" width="38" height="31" rx="11" fill={`${accent}18`} stroke={accent} strokeWidth="1.5" />
        <g>
          <circle cx="25" cy="33" r="5.2" fill="var(--void)" stroke={accent} strokeWidth="1" />
          <circle cx="39" cy="33" r="5.2" fill="var(--void)" stroke={accent} strokeWidth="1" />
          <circle data-pupil cx="25" cy="33" r="2.3" fill={accent} />
          <circle data-pupil cx="39" cy="33" r="2.3" fill={accent} />
        </g>
        <path d="M28 42.5 Q32 45.5 36 42.5" stroke={accent} strokeWidth="1.6" fill="none" strokeLinecap="round" />
      </svg>
      {label && (
        <span style={{ font: '400 10.5px var(--font-body)', color: 'var(--w)' }}>{label}</span>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Persistent nav**

```tsx
// web/components/app-shell/Nav.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Sigil } from './Sigil'

const NAV_ITEMS = [
  { href: '/app', label: 'Dashboard' },
  { href: '/app/products', label: 'Products' },
  { href: '/app/agents', label: 'Agents' },
  { href: '/app/artifacts', label: 'Artifacts' },
  { href: '/app/command', label: 'Command' },
  { href: '/app/billing', label: 'Billing' },
  { href: '/app/settings', label: 'Settings' },
]

export function Nav() {
  const pathname = usePathname()
  return (
    <nav style={{ width: 220, flexShrink: 0, background: 'var(--deep)', borderRight: '0.5px solid rgba(0,229,204,0.14)', display: 'flex', flexDirection: 'column', padding: '16px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: 14, borderBottom: '0.5px solid rgba(0,229,204,0.12)', marginBottom: 14 }}>
        <Sigil size={28} />
        <span style={{ font: '900 15px var(--font-serif)', color: 'var(--w)' }}>ForgeOS</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {NAV_ITEMS.map((item) => {
          const active = item.href === '/app' ? pathname === '/app' : pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                padding: '9px 10px',
                borderRadius: 4,
                font: '500 12px var(--font-body)',
                color: active ? 'var(--teal)' : 'var(--w-dim)',
                background: active ? 'rgba(0,229,204,0.08)' : 'transparent',
                borderLeft: active ? '2px solid var(--teal)' : '2px solid transparent',
              }}
            >
              {item.label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
```

- [ ] **Step 5: App shell layout**

```tsx
// web/app/app/layout.tsx
import { Nav } from '@/components/app-shell/Nav'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: 'var(--void)' }}>
      <Nav />
      <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
    </div>
  )
}
```

- [ ] **Step 6: Manual verification**

Run: `pnpm --dir web dev`, log in, land on `/app`, click each nav item — confirm the active-state highlight matches the current route and links to not-yet-built routes 404 cleanly (expected; Task 7 only builds `/app` itself).

- [ ] **Step 7: Commit**

```bash
git add web/components/app-shell/GlassPanel.tsx web/components/app-shell/Sigil.tsx web/components/app-shell/BotAvatar.tsx web/components/app-shell/Nav.tsx web/app/app/layout.tsx web/app/globals.css
git commit -m "feat(web): app shell — glass panel, sigil, bot avatar, persistent nav"
```

---

## Task 7: War Room Dashboard (`/app`)

**Files:**
- Create: `web/hooks/useDashboardEvents.ts`
- Create: `web/hooks/useProductMetrics.ts`
- Create: `web/components/dashboard/AgentRoster.tsx`
- Create: `web/components/dashboard/ActivityStream.tsx`
- Create: `web/components/dashboard/ArtifactPreview.tsx`
- Create: `web/components/dashboard/MetricsBar.tsx`
- Create: `web/app/app/page.tsx`

- [ ] **Step 1: Realtime hook for dashboard_events**

```ts
// web/hooks/useDashboardEvents.ts
'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export type DashboardEvent = {
  id: string
  agent: string
  event_type: 'info' | 'action' | 'gate' | 'error'
  message: string
  created_at: string
}

export function useDashboardEvents(limit = 14): DashboardEvent[] {
  const [logs, setLogs] = useState<DashboardEvent[]>([])

  useEffect(() => {
    const supabase = createClient()

    supabase
      .from('dashboard_events')
      .select('id, agent, event_type, message, created_at')
      .order('created_at', { ascending: false })
      .limit(limit)
      .then(({ data }) => {
        if (data) setLogs([...data].reverse())
      })

    const channel = supabase
      .channel('dashboard_events_stream')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'dashboard_events' },
        (payload) => {
          setLogs((prev) => [...prev, payload.new as DashboardEvent].slice(-limit))
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [limit])

  return logs
}
```

- [ ] **Step 2: product_metrics hook**

```ts
// web/hooks/useProductMetrics.ts
'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export type ProductMetricRow = {
  product_slug: string
  mrr_inr: number
  signups: number
  conversions: number
  recorded_at: string
}

export function useProductMetrics(): ProductMetricRow[] {
  const [rows, setRows] = useState<ProductMetricRow[]>([])

  useEffect(() => {
    const supabase = createClient()
    supabase
      .from('product_metrics')
      .select('product_slug, mrr_inr, signups, conversions, recorded_at')
      .order('recorded_at', { ascending: false })
      .then(({ data }) => {
        if (data) setRows(data)
      })
  }, [])

  return rows
}
```

- [ ] **Step 3: Agent roster panel**

```tsx
// web/components/dashboard/AgentRoster.tsx
import { GlassPanel } from '@/components/app-shell/GlassPanel'
import { BotAvatar } from '@/components/app-shell/BotAvatar'
import { Sigil } from '@/components/app-shell/Sigil'
import { AGENT_ROSTER, statusDotColor } from '@/lib/agents/roster'

export function AgentRoster() {
  return (
    <GlassPanel style={{ height: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', padding: '16px 14px', height: '100%', overflowY: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: 14, borderBottom: '0.5px solid rgba(0,229,204,0.12)', marginBottom: 14 }}>
          <Sigil size={30} glowIntensity={0.3} />
          <div>
            <div style={{ font: '900 14px var(--font-serif)', color: 'var(--w)' }}>ForgeOS</div>
            <div style={{ font: '400 7px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.14em', marginTop: 3 }}>
              WAR ROOM · DIM · HONEST
            </div>
          </div>
        </div>
        <div style={{ font: '400 8px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.2em', marginBottom: 12 }}>
          AGENT ROSTER · {AGENT_ROSTER.length}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {AGENT_ROSTER.map((agent) => (
            <div key={agent.slug} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 8px' }}>
              <BotAvatar accent={agent.accent} size={30} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ font: '400 10.5px var(--font-body)', color: 'var(--w)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {agent.name}
                </div>
                <div style={{ font: '400 7px var(--font-body)', color: 'var(--w-ghost)', letterSpacing: '0.12em' }}>
                  {agent.defaultStatus.toUpperCase()}
                </div>
              </div>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: statusDotColor(agent.defaultStatus, agent.accent), flexShrink: 0 }} />
            </div>
          ))}
        </div>
      </div>
    </GlassPanel>
  )
}
```

- [ ] **Step 4: Activity stream panel**

```tsx
// web/components/dashboard/ActivityStream.tsx
'use client'

import { useDashboardEvents } from '@/hooks/useDashboardEvents'

export function ActivityStream() {
  const logs = useDashboardEvents()

  return (
    <div style={{ border: '0.5px solid rgba(0,229,204,0.14)', borderRadius: 6, background: '#07080A', display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderBottom: '0.5px solid rgba(0,229,204,0.1)' }}>
        <span style={{ font: '400 8.5px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.18em' }}>AGENT ACTIVITY STREAM</span>
        <span style={{ font: '400 8px var(--font-body)', color: 'var(--w-ghost)', letterSpacing: '0.12em' }}>
          SUPABASE REALTIME · <span style={{ color: 'var(--teal)' }}>CONNECTED</span>
        </span>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: '8px 0' }}>
        {logs.length === 0 && (
          <div style={{ padding: '5.5px 18px', font: '400 9.5px var(--font-body)', color: 'var(--w-ghost)' }}>
            No agent activity yet — this fills in as the pipeline runs.
          </div>
        )}
        {logs.map((log) => (
          <div key={log.id} style={{ display: 'flex', gap: 12, padding: '5.5px 18px', font: '400 9.5px var(--font-body)' }}>
            <span style={{ color: 'var(--w-ghost)', flexShrink: 0 }}>
              {new Date(log.created_at).toLocaleTimeString('en-IN', { hour12: false })}
            </span>
            <span style={{ color: 'var(--hud)', flexShrink: 0, minWidth: 88 }}>[{log.agent.toUpperCase()}]</span>
            <span style={{ color: log.event_type === 'error' ? 'var(--gold)' : 'var(--w-dim)' }}>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Artifact preview panel — honest empty state (Artifacts screen itself lands in a later plan)**

```tsx
// web/components/dashboard/ArtifactPreview.tsx
export function ArtifactPreview() {
  return (
    <div style={{ border: '0.5px solid rgba(0,229,204,0.14)', borderRadius: 6, background: '#07080A', display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '12px 18px', borderBottom: '0.5px solid rgba(0,229,204,0.1)' }}>
        <span style={{ font: '400 8.5px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.18em' }}>LIVE ARTIFACT</span>
      </div>
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', padding: 16 }}>
        <span style={{ font: '400 11px var(--font-body)', color: 'var(--w-ghost)', textAlign: 'center' }}>
          No artifact is currently being drafted.
          <br />
          This panel lights up when an agent starts writing.
        </span>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Metrics bar**

```tsx
// web/components/dashboard/MetricsBar.tsx
'use client'

import { GlassPanel } from '@/components/app-shell/GlassPanel'
import { useProductMetrics } from '@/hooks/useProductMetrics'

export function MetricsBar() {
  const rows = useProductMetrics()
  const totals = rows.reduce(
    (acc, r) => ({
      mrr: acc.mrr + r.mrr_inr,
      signups: acc.signups + r.signups,
      conversions: acc.conversions + r.conversions,
    }),
    { mrr: 0, signups: 0, conversions: 0 }
  )

  const cells = [
    { label: 'MRR · LIVE', value: `₹${totals.mrr.toLocaleString('en-IN')}` },
    { label: 'SIGNUPS', value: String(totals.signups) },
    { label: 'CONVERSIONS', value: String(totals.conversions) },
    { label: 'PRODUCTS TRACKED', value: String(rows.length) },
  ]

  return (
    <GlassPanel>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1 }}>
        {cells.map((cell) => (
          <div key={cell.label} style={{ padding: '16px 22px' }}>
            <div style={{ font: '400 7.5px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.2em', marginBottom: 7 }}>
              {cell.label}
            </div>
            <div style={{ font: '700 24px var(--font-serif)', color: 'var(--w)' }}>{cell.value}</div>
          </div>
        ))}
      </div>
    </GlassPanel>
  )
}
```

- [ ] **Step 7: Dashboard page — assembles the 4 panels in the War Room grid**

```tsx
// web/app/app/page.tsx
import { AgentRoster } from '@/components/dashboard/AgentRoster'
import { ActivityStream } from '@/components/dashboard/ActivityStream'
import { ArtifactPreview } from '@/components/dashboard/ArtifactPreview'
import { MetricsBar } from '@/components/dashboard/MetricsBar'

export default function DashboardPage() {
  return (
    <div style={{ height: '100vh', display: 'grid', gridTemplateRows: '1fr auto' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 300px', gap: 14, padding: '14px 14px 0', minHeight: 0 }}>
        <AgentRoster />
        <ActivityStream />
        <ArtifactPreview />
      </div>
      <div style={{ padding: 14 }}>
        <MetricsBar />
      </div>
    </div>
  )
}
```

- [ ] **Step 8: Manual verification**

Run: `pnpm --dir web dev`, log in, land on `/app`. Confirm:
- Agent roster shows all 7 agents with Cosmic Garden accent colors (no ice-blue).
- Activity stream shows the honest empty state (no `dashboard_events` rows exist yet from Task 1).
- In the Supabase Dashboard, manually insert one row into `dashboard_events` (`insert into dashboard_events (agent, event_type, message) values ('core', 'info', 'Manual test row')`) and confirm it appears in the stream **without a page refresh** — this is the actual Realtime proof, not just an initial fetch.
- Metrics bar shows `₹0` / `0` / `0` / `0` honestly (no `product_metrics` rows exist yet) — matches PRD §6's "no fabricated data" non-goal.

- [ ] **Step 9: Commit**

```bash
git add web/hooks/useDashboardEvents.ts web/hooks/useProductMetrics.ts web/components/dashboard/ web/app/app/page.tsx
git commit -m "feat(web): War Room Dashboard wired to real Supabase Realtime dashboard_events and product_metrics"
```

---

## What's left (sketch only — not to be executed from this file)

Each of these becomes its own plan, written right before it's built, informed by how the foundation actually shipped:

- **Products** (`/app/products`, `/app/products/[id]`) — needs a `products` table (doesn't exist yet either) before the list/detail views mean anything.
- **Pipeline visualization** (`/app/products/[id]/pipeline`) — the 18(V1)/20(V2)-stage HermesOrchestrator track; needs a way to read live stage state out of `builds/<id>/context.json` or a new `pipeline_runs` table, since that state currently lives only in per-build JSON files on disk, not Supabase.
- **Agents** (`/app/agents`) — grid + detail drawer over the same `AGENT_ROSTER` + `dashboard_events` this plan already built; mostly a filtered view, should be cheap once Task 7 exists.
- **Artifacts** (`/app/artifacts`) — filterable feed over `dashboard_events` (or a dedicated `artifacts` table if logs prove too unstructured); needs the "Nightly Reasoning Agent reads this" note per PRD §4.
- **Command** (`/app/command`) — the real routing layer into `agents/hermes.py`; this is the biggest remaining subsystem and needs its own architecture discussion (how does a Next.js server action reach a Python orchestrator process?) before a plan can be written.
- **Billing** (`/app/billing`) — Lemon Squeezy webhook receiver + a `billing_events` table; no Lemon Squeezy integration exists anywhere in this repo yet.
- **Settings** (`/app/settings`) — account info + API key *references* (never raw secrets, per PRD §2); mostly reads `profiles` this plan already created.
- **Workspace switcher UI** — per PRD §6, UI-only against the single real `workspaces` row this plan created; no new backend work.
