# ForgeOS V2

> **One English sentence → a built, tested, secured, and deployed full-stack SaaS.**

ForgeOS is a fully autonomous, multi-agent product factory. Give it an idea; 18 pipeline stages — gated by LLM-powered quality checks — return a complete, production-ready codebase with architecture docs, security audit, GitHub repo, and cloud deployment.

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Hermes Agent](https://img.shields.io/badge/Hermes-v0.13.0-purple.svg)](https://hermes-agent.nousresearch.com)
[![Version](https://img.shields.io/badge/version-2.0-violet.svg)](CHANGELOG.md)

---

## What it does

```
"Build ContractForge — AI contract generator SaaS at $29/mo"
                          ↓  ~30–45 minutes
  ✅ Market viability + strategic alignment gates
  ✅ SPEC.md + ARCH.md + TASKS.json + ValidationContract
  ✅ Full Next.js 14 + FastAPI + Supabase scaffold
  ✅ Feature-by-feature implementation (Claude Code CLI)
  ✅ Adversarial code review + quality score gate (≥7/10)
  ✅ OWASP security audit + RLS policies + CSO sign-off
  ✅ GitHub repo created + Render (backend) + Vercel (frontend)
  ✅ Telegram/Discord build notifications via Hermes Agent
```

---

## V2 Architecture — Three Layers

### Layer 1: GStack Quality Gates

9 LLM-powered gates are woven into the pipeline. Each gate calls an LLM with a specialised prompt, parses `PASS/FAIL` + `SCORE: N/10`, and **blocks the pipeline** if the bar isn't met.

| Gate | Phase | Min Score | Blocking |
|------|-------|-----------|----------|
| `office_hours` | planning | — | yes |
| `ceo_review` | planning | — | yes |
| `eng_review` | design | — | yes |
| `design_shotgun` | design | — | no |
| `review` | code | 7.0 | yes |
| `adversarial` | code | — | yes |
| `score` | code | 7.0 | yes |
| `cso` | security | — | yes |
| `qa` | qa | 7.0 | yes |
| `ship` | deploy | — | yes |

### Layer 2: Missions (serial feature execution)

Replaces the monolithic `CoderAgent` with structured, git-committed feature delivery:

1. `MissionOrchestrator` writes a **ValidationContract** (acceptance assertions) before any code
2. `MissionWorkerLoop` implements features one at a time — tries Claude Code CLI first, falls back to direct LLM
3. Each feature lands in its own git commit
4. `MissionValidator` runs adversarial checks against the contract after all features ship

### Layer 3: Hermes Orchestrator

Top-level coordinator wrapping the full 18-stage pipeline:

- **Telegram / Discord notifications** at every gate and build event (via Hermes Agent v0.13.0)
- **Obsidian knowledge base** writes after every build
- **Dataset flywheel** — appends structured build metadata to `~/.forgeos/dataset.jsonl`

---

## Pipeline (18 stages)

```
office_hours(G) → ceo_review(G) → architect →
eng_review(G) → design_shotgun →
mission_plan → scaffold → game →
mission_work →
review(G) → adversarial(G) → score(G) →
security → cso(G) → qa(G) →
validator → ship(G) → deploy
```

`(G)` = blocking gate

---

## LLM Routing (V2)

| Task type | Provider chain |
|-----------|---------------|
| Architecture / planning | Ollama → Claude Sonnet 4 |
| Code review / gates | Ollama → Claude Haiku 4.5 |
| Scaffolding / formatting | Ollama → Claude Haiku 4.5 |
| Code generation | Claude Code CLI → LLM fallback |

Ollama (`qwen2.5-coder:7b`) is tried first — free and GPU-accelerated on the RTX 4050. Claude is the cloud fallback (~$0.01–0.05/build).

---

## Quick Start

### Prerequisites

- WSL2 (Ubuntu 22.04) + Python 3.11+
- `ANTHROPIC_API_KEY` in `.env` (required for gates)
- [Ollama](https://ollama.ai) with `qwen2.5-coder:7b` (optional — free local LLM)
- Node 20+ for the UI
- [Hermes Agent](https://hermes-agent.nousresearch.com) for notifications (optional)

### Install

```bash
git clone https://github.com/padmajakotoky73-hash/forgeos
cd forgeos
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY at minimum
```

### Run a build

```bash
# V2 pipeline (default)
PYTHONPATH=. python3 orchestrator.py --idea "Build ContractForge — AI contract generator SaaS at $29/mo"

# Legacy V1 pipeline
PYTHONPATH=. python3 orchestrator.py --idea "..." --legacy

# Resume an interrupted build
PYTHONPATH=. python3 orchestrator.py --idea "<same idea>" --workdir builds/<id>
```

### Start the UI + API

```bash
# Terminal 1 — ForgeOS API (port 8000)
PYTHONPATH=. python3 api.py

# Terminal 2 — Next.js dashboard (port 3000)
cd forgeos-ui && npm run dev
```

---

## File Layout

```
forgeos/
├── orchestrator.py        # entry point — HermesOrchestrator (V2) or legacy
├── api.py                 # FastAPI + SSE streaming
├── models.py              # LLMClient, ProjectContext, GateResult, ValidationContract
├── config.py              # LLM, Tool, Runtime config + cost table
├── forge_brain.py         # Obsidian knowledge accumulation
├── healer.py              # self-healing daemon (Sentry + UptimeRobot)
├── agents/
│   ├── base.py            # BaseAgent ABC
│   ├── architect.py       # ArchitectAgent — SPEC/ARCH/TASKS/STACK
│   ├── scaffold.py        # ScaffoldAgent — full project tree
│   ├── coder.py           # CoderAgent (V1 legacy)
│   ├── game.py            # GameAgent — Three.js / Phaser / Godot
│   ├── security.py        # SecurityAgent — OWASP + RLS
│   ├── deploy.py          # DeployAgent — GitHub + Render + Vercel
│   ├── gstack.py          # GStack quality gates (9 gates)
│   ├── mission.py         # MissionOrchestrator, MissionWorkerLoop, MissionValidator
│   └── hermes.py          # HermesOrchestrator, HermesGateway, TelegramNotifier
├── llm/
│   ├── router.py          # route() — Ollama → Claude Sonnet → Claude Haiku
│   ├── ollama.py          # OllamaClient
│   └── claude.py          # ClaudeClient
├── tools/
│   ├── github.py          # GitHub API
│   ├── render.py          # Render deploy API
│   ├── vercel.py          # Vercel deploy API
│   ├── supabase_admin.py  # Supabase service-role client
│   ├── sentry.py          # Sentry issue watcher
│   └── uptimerobot.py     # Uptime monitor
└── builds/                # runtime output — one folder per build
    └── <id>/
        ├── context.json
        ├── SPEC.md  ARCH.md  TASKS.json  STACK.json
        ├── VALIDATION_CONTRACT.json
        ├── SECURITY.md
        └── project/        # the generated codebase
```

---

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...        # Claude — required for GStack gates

# Optional LLM
OLLAMA_MODEL=qwen2.5-coder:7b      # default Ollama model (free, local)
ANTHROPIC_MODEL=claude-haiku-4-5   # Claude model override

# Notifications (Hermes Agent)
TELEGRAM_BOT_TOKEN=...              # or use Discord via hermes gateway setup
TELEGRAM_CHAT_ID=...

# Deploy
GITHUB_TOKEN=ghp_...
VERCEL_TOKEN=...
RENDER_API_KEY=...
RENDER_OWNER_ID=...

# Supabase (for generated projects)
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_ACCESS_TOKEN=...

# Monitoring
SENTRY_AUTH_TOKEN=...
UPTIMEROBOT_API_KEY=...

# GStack tuning
GSTACK_MIN_SCORE=7.0               # gate pass threshold (default 7.0)
MISSION_MAX_FEATURES=12            # max features per build
```

---

## Notifications

ForgeOS uses **[Hermes Agent v0.13.0](https://hermes-agent.nousresearch.com)** for build notifications. Hermes supports Telegram, Discord, Slack, WhatsApp, and more — no Composio needed.

```bash
# Install Hermes (WSL2)
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Set up Discord (or Telegram / Slack)
hermes gateway setup

# Run the gateway (receives commands, sends notifications)
hermes gateway run
```

Once the gateway runs, you can trigger ForgeOS builds from Discord:
> "build ContractForge — AI contract generator SaaS at $29/mo"

---

## Generated Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 App Router + TypeScript + Tailwind CSS |
| Backend | FastAPI + Pydantic v2 |
| Database | Supabase (Postgres + Auth + RLS) |
| Payments | Lemon Squeezy (never Stripe) |
| Secrets | Doppler (prod) |
| Deploy | GitHub → Render (API) + Vercel (UI) |
| Tests | pytest + Vitest |
| Monitoring | Sentry + UptimeRobot |

---

## First Product

**ContractForge** — AI contract generator SaaS at $29/mo

```bash
PYTHONPATH=. python3 orchestrator.py \
  --idea "Build ContractForge — AI contract generator SaaS at $29/mo"
```

---

## License

MIT — see [LICENSE](LICENSE).

---

*ForgeOS V2 · RTX 4050 · WSL2 Ubuntu 22.04 · Hermes Agent v0.13.0*
