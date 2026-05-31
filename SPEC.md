# ForgeOS — Product Specification
> Version 0.2 (current). This is the living spec.

## What it is
ForgeOS is an autonomous, multi-agent product factory.
Give it one English sentence. It returns a built, tested, secured, and deployed SaaS.

**Tagline**: One sentence. Full SaaS.

## Who it's for
- Solo founders who want to validate ideas fast
- CS/AI students learning by building real products
- Builders who want a "factory" not a "tool"

---

## Current architecture (v0.2)

### Pipeline (fixed order)
```
User idea (string)
    │
    ▼
[ArchitectAgent]  → SPEC.md, ARCH.md, TASKS.json, STACK.json
    │
    ▼
[ScaffoldAgent]   → Full project directory tree + config files
    │
    ▼
[CoderAgent]      → Implements all tasks from TASKS.json
    │
    ▼
[GameAgent]       → Skipped unless idea contains game keywords
    │
    ▼
[SecurityAgent]   → SECURITY.md, RLS policies, secrets audit
    │
    ▼
[DeployAgent]     → GitHub repo + Render (backend) + Vercel (frontend)
    │
    ▼
Live URLs: GitHub + onrender.com + vercel.app
```

### Generated stack (what ForgeOS builds)
- **Frontend**: Next.js 14 App Router + Tailwind + Shadcn/ui → Vercel
- **Backend**: FastAPI + Pydantic v2 → Render.com
- **Database**: Supabase (Postgres + Auth + RLS)
- **Payments**: Lemon Squeezy
- **Auth**: Supabase Auth
- **CI/CD**: GitHub Actions

### LLM routing
```
All tasks → Ollama (qwen2.5-coder:7b, local GPU) → Claude haiku-4-5 (fallback)
```

---

## What works right now (v0.2)
- [x] Full pipeline runs end-to-end (~20 min per build)
- [x] GitHub repo created + code committed on every build
- [x] Render service created + deploy triggered
- [x] Vercel project created + deploy triggered
- [x] ForgeOS UI: live SSE streaming, agent cards, build history, 3D hero
- [x] Build resumption (`--workdir` flag)

## What's broken / needs fixing
- [ ] Generated FastAPI code missing `/healthz` route → Render shows "Not Found"
- [ ] Vercel deployment fails → frontend 404 (wrong root directory config)
- [ ] Security agent is near no-op (needs real RLS + secrets work)
- [ ] CI always fails (generated GitHub Actions has broken configs)
- [ ] No Supabase project auto-creation (generated code points to placeholder URLs)

---

## Roadmap

### v0.3 — Code Quality Sprint (next)
**Goal**: Every build produces a FastAPI app that actually serves traffic and a Next.js app that actually deploys.

- [ ] Fix coder agent system prompt: mandate `/healthz`, proper file structure
- [ ] Fix Vercel deploy: pass `rootDirectory: "frontend"` in trigger
- [ ] Add a validator step after coder: checks that required files exist
- [ ] Fix SecurityAgent: real RLS policy generation
- [ ] Make generated repos public (so Vercel/Render can pull without auth)

### Missions Architecture (planned)
**Goal**: Instead of a single pipeline run, ForgeOS manages long-lived "Missions" — projects that evolve over time with ongoing agent activity.

A Mission is:
- A named product with a persistent identity
- A series of "runs" (sprints) that build on each other
- Agent memory that persists between runs
- A dashboard showing mission health, live URLs, and history

Missions would enable:
- "Improve my habit tracker" (vs rebuild from scratch)
- "Add a team collaboration feature to my todo SaaS"
- Ongoing healer agent that watches production and auto-fixes issues

### Gstack (planned)
The "Generation Stack" — a curated, battle-tested set of prompts, templates, and patterns that ForgeOS uses to generate code that actually works.

Key pieces:
- Validated FastAPI template (always includes `/healthz`, auth middleware, CORS)
- Validated Next.js template (correct folder structure for Vercel, auth flow)
- Validated Supabase schema template (RLS policies that work)
- Prompt library: tested system prompts for each agent

---

## Key files to read before working
1. `CONTEXT.md` — current state, known bugs, env setup
2. `agents/deploy.py` — deploy pipeline (GitHub + Render + Vercel)
3. `agents/coder.py` — where code generation happens (prompt engineering target)
4. `llm/router.py` — how models are selected per task
5. `forgeos-ui/app/page.tsx` — UI entry point

## Constraints
- No Stripe (use Lemon Squeezy)
- No Aider
- No truncated files — always write complete files
- Doppler for secrets in generated projects
- Absolute imports throughout Python codebase
- `PYTHONPATH=.` always required when running Python
