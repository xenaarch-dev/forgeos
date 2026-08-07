# Agent Mesh Backend — Specification

> Status: SPEC ONLY — no implementation exists. No code was written in the session that produced this file.
> Spec date: 2026-08-07 (Day 210)
> Author: Padmaja Kotoky + Claude Sonnet 5
> Grounded in: the Command-interface investigation earlier this session (findings restated in §1, not re-derived)
> Ready for: implementation review

---

## 1. Ground truth this spec is built on

Everything in this section was verified by reading code earlier tonight. It is
restated here so the spec stands on its own; it is not re-argued.

### 1a. The Command UI is a static mock

[`web/app/app/command/page.tsx`](web/app/app/command/page.tsx) is a client
component whose entire behaviour is local `useState`. Its `send()` handler
(lines 26–32) appends the user's text and a canned
`Routing "..." to the mesh...` string to an array and returns. There is no
`fetch`, no `axios`, no API URL constant, anywhere in the file or its
directory.

The opening NDA/fintech exchange is the `INITIAL` array at line 8 — a hardcoded
fixture that renders identically on every page load regardless of input. It is
not a replayed run.

The `APPROVE ARTIFACT →` and `REQUEST REVISION` buttons (lines 111–116) have no
`onClick` handler at all.

**Consequence:** a genuinely new prompt produces a user bubble, a routing line,
and then silence — because there is no further code to execute. Nothing is
hanging or timing out.

### 1b. `POST /builds` is real but is the wrong shape, and is unreachable

[`api.py:249`](api.py#L249) is genuine, executing code: it creates a build
record, spawns `orchestrator.py` as a subprocess, and streams output over SSE at
[`api.py:312`](api.py#L312). It runs the actual V2/V1 pipeline
(Architect → Scaffold → Coder → Game → Security → Deploy).

Two problems:

1. **Unreachable.** Nothing in `web/` references it. Grep for
   `NEXT_PUBLIC_API_URL`, `localhost:8000`, `API_URL`, `BACKEND_URL` across the
   whole `web/` tree returns zero hits. There is no `vercel.json` rewrite. The
   only real backend integration in the frontend is
   `web/app/api/metrics/route.ts`, which talks to Supabase directly.
2. **Wrong shape.** `/builds` is a 20-stage, minutes-to-tens-of-minutes
   *product build*. The Command UI depicts something else: a short
   conversational turn routed to one named capability
   (ContractForge / OutreachForge / …) that returns one reviewable artifact.
   A contract draft is not a repo scaffold. `/builds` is a *capability the mesh
   should be able to call*, not the mesh itself.

### 1c. Which other screens are also fixtures — and which are not

The earlier investigation flagged "Products/Artifacts/Pipeline are hardcoded
too." Checked individually, the picture is more mixed, and it changes scope:

| Screen | Data source | Honest? | In scope here? |
|---|---|---|---|
| `/app` Dashboard — ActivityStream | `useDashboardEvents()` → real `dashboard_events` table | **Yes** — live, with a real empty state | No — already correct |
| `/app` Dashboard — ArtifactPreview | none; static empty state ("No artifact is currently being drafted") | **Yes** — honest placeholder | Phase 7 lights it up |
| `/app` Dashboard — AgentRoster | `lib/agents/roster.ts` static list | **Yes** — agent *identity*, not fabricated activity | No |
| `/app/agents` | `lib/forge/agents.ts` — activity fields deliberately `null` with an explanatory comment | **Yes** — refuses to invent activity | Phase 4 gives those fields a real source |
| `/app/command` | `INITIAL` fixture in the page file | **No** — presents a fake completed run | **Yes — this spec** |
| `/app/artifacts` | `lib/forge/artifacts.ts` — 7 invented artifacts with fake dates/statuses | **No** | **Yes — Phase 8** |
| `/app/products` | hardcoded ContractForge card | Partly — ContractForge is genuinely live, so the card is true; it just can't grow | No — see below |
| `/app/products/[id]/pipeline` | `lib/forge/pipeline.ts` — 18 stages, 15 marked `COMPLETE` | **No** | No — see below |

**Products and Pipeline are separately scoped and deliberately excluded.** They
describe the `/builds` product-factory pipeline, not the mesh. Making them
truthful means deploying and wiring `POST /builds` + reading `context.json` /
`gbrain-events.jsonl` per build — a sibling project with its own spec. Doing it
inside this one would double the surface area and couple two independent
deployables. Track it separately.

`/app/artifacts` **is** in scope, because artifacts are the mesh's primary
output and there is no point producing real ones into a screen that ignores
them.

### 1d. What already exists on the backend per named UI agent

| UI agent | Real backing code today | State |
|---|---|---|
| ContractForge | `agents/legal_agent.py` — `LegalAgent`, India-law T&C/Privacy/Refund via `claude-sonnet-4-6`, streaming | Real and working, but **not** a `ForgeAgent` — bespoke `run(ctx, output_dir)` signature, own `AgentResult` handling |
| OutreachForge | `agents/outreach.py` — `OutreachForgeAgent`, a real `ForgeAgent`; drafts lead messages, writes `outreach_leads` in Supabase | Real. Already carries the invariant this spec must not weaken: *"HARD RULE: Nothing sends automatically. No message leaves this system until a human calls `mark_approved()`."* |
| SpecForge | `agents/architect.py` (`ArchitectAgent`) + the `/builds` pipeline | Real, but heavyweight — see §5c |
| ClientForge | `agents/distribution/prospect_agent.py`, `outreach_queue.py` | CLI tools, not agents; no conversational entry point |
| GBrain | `gbrain/` knowledge store + `forge_brain.py` | A knowledge store and a post-build writer — **not** a conversational agent |
| MeetingForge | none | `QUEUED` in the UI, correctly |
| ReputationForge | none | `QUEUED` in the UI, correctly |

**This spec does not make all seven real.** It makes the router honest about
which are real, and ships two of them properly. Pretending otherwise is how the
current mock happened.

### 1e. Stale documentation to correct while implementing

- `CLAUDE.md` says deploy target is **Railway**. The truth is **Render**:
  `tools/render.py` (`RenderClient`), `agents/deploy.py` provisions
  `https://{repo}.onrender.com`, `README.md`'s stack table says
  "Render (backend) · Vercel (frontend)", and `.env.example` carries
  `RENDER_API_KEY` / `RENDER_OWNER_ID`. There is no `tools/railway.py`.
- `CLAUDE.md` says LLM routing is `Ollama → Claude`. The truth is
  `config/models.yaml` + `llm/router.py`: **GLM-5.2 (OpenRouter) → Sonnet
  fallback → Fable-5 (gated frontier)**, with Ollama as an explicit
  `FORGEOS_OFFLINE_MODE=true` opt-in.
- `CLAUDE.md` places `ForgeAgent` in `agents/base.py`. It lives in
  `forge_sdk/agent.py`; `agents/base.py` holds `BaseAgent`, its parent.

These are doc fixes, not blockers. Fold them into whichever phase touches them.

---

## 2. What the mesh is

A **capability router with a conversational surface**. One free-text command
in; a stream of real progress events out; zero or one reviewable artifact at
the end, gated on founder approval before anything irreversible happens.

```
  founder types free text
           │
           ▼
   ┌───────────────┐   deterministic prefilter (exact/quick-action)
   │  MeshRouter   │   → LLM structured classify (closed enum)
   └───────┬───────┘   → clarify / unsupported
           │
     RouteDecision{capability, args, confidence, rationale}
           │
           ▼
   ┌───────────────────────────────────────────────┐
   │  CapabilityRegistry — only *implemented* ones │
   │  contract · outreach · spec · build           │
   └───────┬───────────────────────────────────────┘
           │  ForgeAgent.run(context)   [in-process asyncio task]
           │  _emit() → GBrainLogger → gbrain-events.jsonl
           ▼
   ┌───────────────┐        ┌──────────────────────┐
   │  SSE stream   │───────▶│  Command UI transcript│
   └───────┬───────┘        └──────────────────────┘
           │
           ▼
   ┌───────────────────┐   artifact row (status=pending)
   │ FounderApprovalGate│──▶ blocks side effects until approved
   └───────────────────┘
```

**Non-goals, stated explicitly:**

- Not a general chatbot. Unroutable input gets an honest "I can't do that yet",
  not an LLM freestyle answer.
- Not multi-tenant. One workspace exists (`app_foundations.sql` says so in a
  comment). RLS already grants all authenticated users everything.
- Not autonomous send/publish. Approval gates everything with an external
  effect.
- Does not replace `/builds`. It calls it.

---

## 3. Router / dispatcher design

### 3a. Recommendation: two-stage hybrid — deterministic prefilter, then constrained LLM classify

Not pure rules, not pure LLM.

**Stage 1 — deterministic prefilter.** Exact-match a small table before any
network call.

- The three `QUICK_ACTIONS` in the UI (`GENERATE NDA`,
  `DRAFT OUTREACH FOR CA FIRMS`, `RUN MORNING METRICS`) are *known button
  payloads*, not natural language. They must never cost an LLM call or add
  latency.
- Slash commands (`/contract`, `/outreach`, `/build …`) route directly.
- Empty/whitespace short-circuits.

**Stage 2 — LLM structured classification** for everything else, via
`_structured_llm()` with a Pydantic output model constrained to a **closed
enum of capabilities that are actually implemented**:

```python
class Capability(str, Enum):
    CONTRACT    = "contract"      # LegalAgent
    OUTREACH    = "outreach"      # OutreachForgeAgent
    SPEC        = "spec"          # ArchitectAgent, spec-only mode
    BUILD       = "build"         # POST /builds — full pipeline
    CLARIFY     = "clarify"       # ambiguous — ask one question back
    UNSUPPORTED = "unsupported"   # real intent, no implementation yet

class RouteDecision(BaseModel):
    capability: Capability
    args: dict[str, str] = {}
    confidence: float                 # 0.0–1.0
    rationale: str                    # one sentence, shown in the transcript
    unsupported_reason: str | None = None
```

### 3b. Why hybrid, specifically

**Why not pure rules.** Keyword matching fails on exactly the input that
exposed this bug. "Build a simple waitlist landing page for a productivity app"
contains no contract/outreach keyword; a rule table's honest answer is "no
match," which produces the same silence the mock produces today. The whole
point is graceful handling of input nobody anticipated.

**Why not pure LLM.** Three reasons, all concrete:

1. The quick-action buttons are deterministic payloads. Paying ~800ms and a
   token cost to classify a string the frontend *generated from a constant* is
   waste.
2. An unconstrained classifier will confidently route to MeetingForge — a
   capability that does not exist as a single line of code. That is precisely
   the failure mode this whole exercise is correcting. The closed enum makes it
   structurally impossible.
3. Cost. A router runs on every keystroke-submitted command, including typos
   and mis-sends. Rules absorb the cheap cases for free.

### 3c. Confidence handling

| Confidence | Behaviour |
|---|---|
| `>= 0.75` | Dispatch directly. Emit `route` event with the rationale. |
| `0.45 – 0.75` | Dispatch, but prefix the transcript with `Routing to <X> — say "no, I meant …" to redirect.` |
| `< 0.45` | Do **not** dispatch. Return `CLARIFY` with exactly one question. |

Never dispatch below 0.45. A wrong contract draft costs more than one extra
question.

### 3d. `UNSUPPORTED` is a first-class outcome

When the classifier recognises a real intent with no backing implementation
(MeetingForge, ReputationForge, ClientForge, most GBrain queries), it returns
`UNSUPPORTED` with a plain reason. The UI renders:

> `MeetingForge isn't built yet — it activates at 10 active clients. Nothing ran.`

This is the single most important behavioural difference from the current mock:
**the system says what it cannot do instead of going quiet.**

### 3e. Which model routes

Use `claude-sonnet-4-6` via `_structured_llm()`, **not** the GLM-5.2 default
tier. Reason, from the code: `agents/base.py::_structured_llm` documents that
it "Always uses ClaudeClient directly — bypasses Ollama since Ollama does not
support the Anthropic tool_use protocol." The same constraint applies to the
GLM/OpenRouter path. Routing is a short, latency-sensitive, schema-critical
call where a malformed response is a hard failure — it is the wrong place to
economise. Add `router: "claude-sonnet-4-6"` to `config/models.yaml` `stages:`
so the choice is visible and overridable.

Budget: `budget_usd = 0.02` on the router agent. It is a ~300-token call; if it
somehow exceeds that, something is wrong and it should abort loudly.

### 3f. Files

```
mesh/
├── __init__.py
├── router.py        # MeshRouter: prefilter + classify + confidence policy
├── registry.py      # CapabilityRegistry: capability -> adapter
├── capabilities/
│   ├── contract.py  # adapter over LegalAgent
│   ├── outreach.py  # adapter over OutreachForgeAgent
│   ├── spec.py      # adapter over ArchitectAgent (spec-only)
│   └── build.py     # adapter over POST /builds
└── models.py        # RouteDecision, Capability, CommandThread, MeshArtifact
```

`mesh/` is a new top-level package, not a subpackage of `agents/`. It is a
*coordination* layer that consumes agents; nesting it under `agents/` invites
the circular-import class of bug that `agents/__init__.py`'s lazy
`__getattr__` already exists to prevent.

---

## 4. Agent base class: forgeadk vs `forge_sdk.ForgeAgent` vs new

### 4a. Recommendation: `forge_sdk.agent.ForgeAgent`. Do not use forgeadk here. Do not write a new base.

### 4b. Why

`ForgeAgent` already provides, in this repo, today: declarative
`capabilities` / `requires` / `budget_usd`; per-run USD budget enforcement;
auto-instrumented `_llm()` and `_write()`; the `_write()` workdir-escape guard;
and an `event_callback` hook that `api.py`'s SSE endpoint was *built to
consume*. `GStackGate` — the entire gate ladder — already inherits from it.
`OutreachForgeAgent`, one of the two capabilities shipping first, already **is**
one.

forgeadk (`~/forge/forgeadk`, extracted earlier) is genuinely good and
near-identical in shape: same `_execute` contract, same
`capabilities`/`requires`/`budget_usd` attributes, `RunLogger` ≈ `GBrainLogger`,
same `EventCallback` signature. That similarity is exactly why adopting it here
buys nothing and costs three real things:

1. **Provider gap.** forgeadk's router ships `claude`, `ollama`, and
   `openai_compatible`. ForgeOS actually runs on the GLM-5.2 → Sonnet → Fable-5
   *tiered* chain in `llm/router.py`, driven by `config/models.yaml` and
   `FORGEOS_FRONTIER_TIER`. forgeadk's `register_provider()` could host GLM, but
   the tier-resolution policy (`_resolve_chain`, `_FRONTIER_TASK_TYPES`, the
   per-stage YAML) would have to be ported or duplicated. That is a migration,
   not a dependency swap.
2. **Two event-log formats through one SSE endpoint.** `api.py` tails
   `gbrain-events.jsonl` written by `GBrainLogger`. forgeadk's `RunLogger`
   writes its own summary + JSONL. Running both means the streaming layer
   reconciles two schemas — new complexity in the exact place this feature is
   supposed to be simple.
3. **Wrong reason to migrate.** forgeadk's value is as a *published, standalone*
   package for people outside ForgeOS. Converging ForgeOS onto it may well be
   right later, but it should be its own migration with its own tests, not
   smuggled in under a feature that needs streaming and a router. Mixing them
   means a mesh bug and a base-class bug are indistinguishable.

A new base class is not worth discussing: it would reimplement budget
enforcement, event emission, and artifact-write guarding that already work and
are already under test.

**Later convergence stays cheap.** Because the two are structurally the same,
swapping `forge_sdk.ForgeAgent` for `forgeadk.Agent` later is mechanical — an
import change plus a logger adapter. Nothing in this spec forecloses it. Note
it in the ADR when that day comes.

### 4c. Capability adapter shape

Every capability is a `ForgeAgent` subclass in `mesh/capabilities/`, even when
it wraps something that isn't one:

```python
class ContractCapability(ForgeAgent):
    name         = "contract_capability"
    phase        = "mesh"
    capabilities = ["artifacts/contract.md"]
    requires     = ["idea"]
    budget_usd   = 0.35

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        # Adapts LegalAgent's bespoke run(ctx, output_dir) signature into the
        # mesh contract and normalises its output into a MeshArtifact.
        ...
```

The adapter is where `LegalAgent`'s non-standard signature gets normalised —
without editing `LegalAgent` itself. Keeping that seam explicit means
ContractForge's proven India-law prompts are reused verbatim rather than
rewritten under time pressure.

---

## 5. Streaming

### 5a. Recommendation: reuse `api.py`'s SSE pattern and its event contract, but run in-process

The event contract is already specified in `api.py:314-327` and already
understood by whatever consumes it:

```
{"type": "log",         "text": "<line>"}
{"type": "agent_event", "event": "<name>", "agent": "<name>", ...}
{"type": "done",        "status": "success"|"failed"}
```

The mesh adds two `agent_event` names and changes nothing else:

| Event | Payload | Rendered as |
|---|---|---|
| `route` | `{capability, confidence, rationale}` | "Routing to ContractForge — NDA + service agreement requested." |
| `artifact_ready` | `{artifact_id, type, title, preview}` | Right-hand LIVE ARTIFACT panel populates |

Existing `ForgeAgent` events (`start`, `llm_call`, `artifact`, `gate`,
`success`, `error`, `finish`) already produce the per-stage progress lines the
UI mock fakes with three static bullets.

### 5b. One deliberate difference from `/builds`: no subprocess

`_run_build` (`api.py:204`) spawns `orchestrator.py` via
`asyncio.create_subprocess_exec` and parses stdout. Correct for a 30-minute
build with an existing CLI entry point. Wrong for the mesh:

- A mesh command is seconds to ~a minute. Process spawn overhead is a
  meaningful fraction of total latency.
- Structured events would have to survive a round-trip through stdout text and
  be re-parsed, when `ForgeAgent._emit()` already hands over a typed dict.

So: `asyncio.create_task` running the capability **in-process**, with the
`event_callback` pushing straight onto an `asyncio.Queue` per command. Reuse
`_run_build`'s in-memory registry + fire-and-forget task shape; drop the
subprocess.

### 5c. `build` is the exception — it delegates

`Capability.BUILD` does not run in-process. It calls the existing `POST /builds`
path and then **relays** that build's SSE stream into the command's stream,
re-tagging events. This keeps one code path for product builds and gives the
Command UI a truthful "this will take a while" affordance instead of a
conversational-looking response for a 20-stage job.

### 5d. Rejected alternatives

**WebSockets.** The transport is one-directional — the founder submits over
plain HTTP POST and only *receives* progress. `EventSource` reconnects
automatically; a WS reconnect/heartbeat layer would have to be written. No.

**Supabase Realtime on `dashboard_events` as the primary channel.** Tempting —
the table exists, is already in `supabase_realtime`, and `useDashboardEvents()`
already subscribes. But it has no per-command correlation column, no ordering
guarantee suitable for a conversational transcript, and broadcast semantics
that would leak one command's stream into every open tab.

**Use it as the secondary channel instead.** Every mesh event also inserts a
`dashboard_events` row (`agent`, `event_type`, `message`, `metadata`). That is
what makes the Dashboard ActivityStream light up during a mesh command, for
free, with no new frontend code — it is already reading that table. SSE for the
live transcript; `dashboard_events` for the persistent cross-page feed.

### 5e. Endpoints

```
POST /command                     -> 201 {command_id, stream_token, route: RouteDecision}
GET  /command/{id}/stream?t=...   -> text/event-stream
GET  /command/{id}                -> full transcript (reload / late join)
POST /artifacts/{id}/approve      -> 200 {status: "approved"}
POST /artifacts/{id}/revise       -> 201 {command_id, ...}  # new turn, same thread
```

`POST /command` runs the router **synchronously** (sub-second) so the response
carries the real `RouteDecision`. The UI can render a truthful routing line
immediately — and, on `UNSUPPORTED`, correctly render nothing further and never
open a stream.

---

## 6. Deployment

### 6a. Recommendation: Render web service

**Render, not Railway** — per §1e, Render is what the repo actually uses.
`tools/render.py` already wraps its API, `agents/deploy.py` already provisions
against it, `RENDER_API_KEY` / `RENDER_OWNER_ID` are already environment
contract. Introducing a second PaaS for one service is a cost with no benefit.

| Setting | Value |
|---|---|
| Service type | Web Service (Python) |
| Start command | `uvicorn api:app --host 0.0.0.0 --port $PORT` |
| Health check | `/healthz` (exists, `api.py:243`) |
| Region | Singapore — closest Render region to India |
| Instance | **Starter (paid), not Free** — see below |

**The free tier is not viable and this is a real cost decision, not a
footnote.** Render free instances sleep after ~15 minutes idle; a cold start is
tens of seconds. A founder demoing the Command interface would hit a spinner,
then an SSE connection against a booting process. For a feature whose entire
purpose is proving the system responds, that is worse than the current mock.
Either budget the Starter instance or add an external keep-warm ping — decide
before Phase 5, not during it.

**In-memory state must not survive as the design.** `api.py`'s `_builds` dict
dies on every restart and is wrong the moment there are two instances. Mesh
command state persists to Supabase (§7). The in-process `asyncio.Queue` is a
live-stream buffer only; a reconnect reads history from Postgres via
`GET /command/{id}`.

### 6b. Frontend → backend wiring

`NEXT_PUBLIC_FORGEOS_API=https://forgeos-api.onrender.com` in Vercel env, for
Production and Preview. No `vercel.json` rewrite/proxy — a proxy would buffer
SSE through Vercel's function layer and defeat the streaming.

### 6c. Auth

Supabase Auth is already live and already protects `/app/*` —
[`web/middleware.ts`](web/middleware.ts) uses `@supabase/ssr`, calls
`supabase.auth.getUser()`, and checks `profiles.onboarded_at`. The mesh backend
verifies the same JWT. No new identity system.

- `POST /command`, `GET /command/{id}`, `/artifacts/*`:
  `Authorization: Bearer <supabase_access_token>`, verified against the
  project's JWKS.
- **`GET /command/{id}/stream` cannot use that header.** The browser
  `EventSource` API accepts no custom headers — a real, specific constraint
  worth stating before someone discovers it mid-implementation.

  **Resolution:** `POST /command` returns a **one-time `stream_token`** — signed,
  5-minute TTL, scoped to that single `command_id` and that user — passed as
  `?t=`. Rejected alternative: `fetch()` + manual `ReadableStream` parsing,
  which does allow headers but means hand-rolling SSE framing and reconnect
  logic that `EventSource` gives for free.

### 6d. CORS

Explicit allowlist. Never `*` — credentials are in play.

```python
allow_origins = [
    "https://forgeos-eight.vercel.app",
    "http://localhost:3000",
]
allow_origin_regex = r"^https://forgeos-[a-z0-9\-]+\.vercel\.app$"   # previews
allow_credentials = True
allow_methods     = ["GET", "POST", "OPTIONS"]
```

### 6e. Rate limiting

Per-user: 10 commands/minute, 100/day. Every mesh command spends real money on
GLM/Sonnet. Enforce in the backend, not the UI — the UI is not a trust
boundary. Return `429` with a plain message the transcript can render.

---

## 7. Artifacts and the approve / revise flow

### 7a. What produces an artifact

Every capability run yields zero or one `MeshArtifact`, written twice:

1. **A file** in the command workdir via `ForgeAgent._write()` — reusing the
   existing workdir-escape guard in `agents/base.py`. Path:
   `builds/commands/<command_id>/artifacts/<slug>.md`.
2. **A Supabase row** in a new `artifacts` table — the source of truth for
   `/app/artifacts` and the LIVE ARTIFACT panel.

```sql
create table if not exists artifacts (
    id                  uuid primary key default gen_random_uuid(),
    command_id          uuid not null references command_threads(id) on delete cascade,
    parent_artifact_id  uuid references artifacts(id) on delete set null,  -- revisions
    agent               text not null,
    artifact_type       text not null check (artifact_type in ('CONTRACT','SPEC','EMAIL','PROPOSAL')),
    title               text not null,
    body                text not null,
    status              text not null default 'pending'
                        check (status in ('pending','approved','revision_requested','rejected')),
    workdir_path        text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);
```

`artifact_type` intentionally mirrors the `ArtifactType` union already in
`web/lib/forge/artifacts.ts`, so Phase 8 is a data-source swap rather than a
component rewrite.

A sibling `command_threads` table holds `id`, `user_id`, `input_text`,
`routed_capability`, `confidence`, `status`, `created_at`.

Follow existing migration conventions from `20260707000000_app_foundations.sql`:
snake_case, check-constrained enums, `update_updated_at` trigger, RLS enabled
with explicit policies, `select` for `authenticated`.

### 7b. Founder approval as a gate

This repo already has a gate convention: `GStackGate` in `agents/gstack.py` —
`blocking=True` raises and halts, `GateResult(gate, passed, score, feedback)`,
verdicts appended to `context.metadata["gates"]`, pipeline entries declared as
`{"name": ..., "cls": ..., "gate": True}`.

`FounderApprovalGate` follows those conventions with one difference: **the
verdict comes from a human, not an LLM.**

| Aspect | `GStackGate` | `FounderApprovalGate` |
|---|---|---|
| Verdict source | LLM scores 1–10 | Founder clicks Approve / Revise |
| Blocking | raises `RuntimeError` immediately | **suspends** — persists `pending`, ends the stream cleanly |
| Resume | n/a | `POST /artifacts/{id}/approve` resumes any downstream effect |
| Logging | `GateResult` → `context.metadata["gates"]` | same shape, `passed=None` while pending |

Emit via the existing `GBrainLogger.log_gate(...)` so gate events reach the SSE
stream through the path that already works.

**What the gate protects.** Generating a draft is safe and needs no gate.
The gate sits before anything **irreversible or externally visible**: sending
outreach, publishing, committing a contract to a client. This preserves —
rather than reinvents — the invariant already written into `agents/outreach.py`:
nothing leaves the system without a human. The mesh must not become the loophole
that bypasses it.

### 7c. Approve

`POST /artifacts/{id}/approve` → status `approved`, `dashboard_events` row,
downstream effect (if any) released. For a contract draft there is no
downstream effect — approval is a bookkeeping state that makes
`/app/artifacts` truthful.

### 7d. Revise

`POST /artifacts/{id}/revise {note}` opens a **new turn in the same thread**,
seeding the capability with the prior artifact body plus the founder's note.
The result is a new row with `parent_artifact_id` set; the original moves to
`revision_requested`. History is preserved, not overwritten — the founder can
always see what changed and why.

### 7e. Frontend note

Both buttons currently have no handler at all (§1a). Phase 7 gives them one.
Until then they should be visibly disabled rather than clickable-and-inert.

---

## 8. Phased build plan

Each phase is independently committable, independently testable, and sized for
**one** Claude Code session. No phase leaves `main` broken. Phases 1–5 ship
without touching the frontend at all, so the UI is only rewired once there is
something real behind it.

---

**Phase 1 — Router as a pure library**
`mesh/models.py`, `mesh/router.py`, `mesh/registry.py`. No HTTP, no UI, no
capability execution: the router returns a `RouteDecision` and stops.
*Test:* `tests/test_mesh_router.py` — prefilter exact-matches all three quick
actions with zero LLM calls; the classifier is mocked; every confidence band and
`UNSUPPORTED` is asserted; "Build a simple waitlist landing page…" (the input
that exposed the bug) routes to `BUILD`, not silence.
*Commit:* `feat(mesh): intent router with closed capability enum`

**Phase 2 — Two real capabilities, CLI only**
`mesh/capabilities/contract.py` (adapts `LegalAgent`) and
`mesh/capabilities/outreach.py` (wraps the existing `ForgeAgent`). Entry point
`python3 -m mesh.run "<text>"`. Still no HTTP.
*Test:* one real end-to-end contract generation writing a file to a temp
workdir; outreach path asserted to draft-only, never send.
*Commit:* `feat(mesh): contract + outreach capabilities behind the router`

**Phase 3 — HTTP surface and SSE**
`POST /command`, `GET /command/{id}/stream`, `GET /command/{id}` in `api.py`.
In-process `asyncio.create_task`, `event_callback` → per-command
`asyncio.Queue`. Reuses the existing three event shapes; adds `route` and
`artifact_ready`.
*Test:* `curl -N` against a local server shows the full event sequence;
`UNSUPPORTED` returns without opening a stream.
*Commit:* `feat(api): POST /command + SSE stream for the agent mesh`

**Phase 4 — Persistence**
Migration `..._command_threads_and_artifacts.sql`. Write-through on every
command and artifact; mirror events into `dashboard_events`.
*Side effect worth naming:* the Dashboard ActivityStream and `/app/agents`
activity fields start showing real mesh data with **zero frontend changes** —
they already read that table.
*Commit:* `feat(mesh): persist command threads and artifacts to Supabase`

**Phase 5 — Deploy to Render + auth + CORS**
Render web service, `NEXT_PUBLIC_FORGEOS_API` in Vercel, Supabase JWT
verification, one-time `stream_token`, CORS allowlist, rate limiting.
*Test:* authenticated `curl` from outside; unauthenticated → 401; wrong origin
→ CORS rejection; a cold-start timing measurement recorded in `STATE.md`.
*Commit:* `feat(deploy): agent mesh backend on Render with Supabase JWT auth`

**Phase 6 — Wire the Command UI**
Replace `send()` in `web/app/app/command/page.tsx` with `POST /command` +
`EventSource`. **Delete the `INITIAL` fixture.** Add a real empty state, a
visible error state, and an `UNSUPPORTED` rendering.
*Test:* live against the deployed backend, both prompts from tonight's
investigation. This is the phase where the reported bug is actually fixed.
*Commit:* `fix(command): wire Command interface to the real agent mesh`

**Phase 7 — Approve / revise**
`FounderApprovalGate`, `POST /artifacts/{id}/approve|revise`, real handlers on
both buttons, LIVE ARTIFACT panel fed by `artifact_ready`.
*Commit:* `feat(mesh): founder approval gate and artifact revision flow`

**Phase 8 — Make `/app/artifacts` real**
Read the `artifacts` table. **Delete `web/lib/forge/artifacts.ts`** and its
seven invented rows.
*Commit:* `fix(artifacts): read real artifacts table, delete fixture data`

**Explicitly deferred (own spec, own sessions):** `/app/products` and
`/app/products/[id]/pipeline` — requires deploying and wiring `POST /builds`
(§1c). MeetingForge / ReputationForge / ClientForge — no backing code exists;
they stay `QUEUED`, and the router honestly reports `UNSUPPORTED`.

---

## 9. Reuse vs. new — itemized

### Reused unchanged

| Component | Location | Role in the mesh |
|---|---|---|
| `ForgeAgent` | `forge_sdk/agent.py` | Base for every capability |
| `GBrainLogger` | `forge_sdk/glogger.py` | Event log the SSE stream reads |
| `ProjectContext` / `AgentResult` | `models/` | Per-command state, persisted |
| Tiered LLM router | `llm/router.py` + `config/models.yaml` | GLM-5.2 → Sonnet → Fable-5 |
| `LegalAgent` | `agents/legal_agent.py` | ContractForge — adapted, not edited |
| `OutreachForgeAgent` | `agents/outreach.py` | OutreachForge — already a `ForgeAgent` |
| `ArchitectAgent` | `agents/architect.py` | SpecForge, spec-only mode |
| `POST /builds` + `_run_build` | `api.py:249`, `api.py:204` | The `BUILD` capability delegates here |
| SSE event contract | `api.py:314-327` | Extended by two events, otherwise unchanged |
| `dashboard_events` + `useDashboardEvents` | migration + `web/hooks/` | Secondary persistent feed — no new code |
| Supabase Auth + `middleware.ts` | `web/middleware.ts` | Identity; backend verifies the same JWT |
| `RenderClient` | `tools/render.py` | Deploy target, already wrapped |
| `GStackGate` conventions | `agents/gstack.py` | Gate shape `FounderApprovalGate` follows |

### Genuinely new

| Component | Location | Why it can't be reused |
|---|---|---|
| `MeshRouter` | `mesh/router.py` | No intent classification exists anywhere in the repo |
| `RouteDecision` / `Capability` | `mesh/models.py` | New contract |
| `CapabilityRegistry` | `mesh/registry.py` | `hermes.py` is a fixed linear pipeline, not a dispatcher |
| Capability adapters (×4) | `mesh/capabilities/` | Normalise heterogeneous signatures (`LegalAgent` especially) |
| `FounderApprovalGate` | `mesh/gates.py` | All existing gates are LLM-scored and synchronous; this suspends on a human |
| `/command` endpoints | `api.py` | `/builds` is build-shaped, not turn-shaped |
| `command_threads`, `artifacts` tables | new migration | No table stores conversational turns or reviewable artifacts |
| One-time `stream_token` | `api.py` | `EventSource` cannot send auth headers |
| Command UI network layer | `web/app/app/command/page.tsx` | Currently zero network code |
| Render service config | Render dashboard + `render.yaml` | Backend has never been deployed |

### Deleted

| What | Where | When |
|---|---|---|
| `INITIAL` fixture messages | `web/app/app/command/page.tsx:7-18` | Phase 6 |
| `ARTIFACTS` fixture (7 invented rows) | `web/lib/forge/artifacts.ts` | Phase 8 |

### Documentation corrected en route

`CLAUDE.md`: Railway → Render; Ollama→Claude routing → GLM-5.2 tier chain;
`ForgeAgent` location `agents/base.py` → `forge_sdk/agent.py` (§1e).

---

## 10. Open questions for implementation review

1. **Render Starter vs. keep-warm ping.** A cost decision, not a technical one
   (§6a). Needs an answer before Phase 5.
2. **Does `SPEC` need its own lightweight path**, or is `ArchitectAgent` in
   spec-only mode fast enough for a conversational turn? If a full architect run
   exceeds ~60s, SpecForge should be a dedicated prompt rather than a
   heavyweight agent invocation. Measure in Phase 2.
3. **Thread memory.** Does turn N see turns 1..N-1? This spec assumes *no* — each
   command routes independently, except `revise`, which explicitly carries the
   prior artifact. Adding general memory is a scope increase and should be its
   own decision.
4. **GBrain as a capability.** Currently a knowledge store, not a conversational
   agent. "What did GBrain learn last night?" is a plausible command with no
   implementation. Leave `UNSUPPORTED`, or build a read-only query capability
   over `gbrain/patterns/*.json`? Defer past Phase 8.
