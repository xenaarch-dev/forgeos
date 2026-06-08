# ForgeOS — Claude Code Context

## What this project is

ForgeOS is a fully autonomous, multi-agent product factory. Give it one English sentence; it returns a built, tested, secured, and deployed software product. It runs locally on WSL2 with an RTX 4050 GPU using Ollama (qwen2.5-coder:7b) as the primary LLM and Claude haiku-4-5 as a cheap fallback for architect-level tasks.

## Hardware & environment

- **Machine**: ASUS TUF + RTX 4050 6GB, running Windows 11 with WSL2 (Ubuntu)
- **LLM primary**: Ollama `qwen2.5-coder:7b` — free, local, GPU-accelerated
- **LLM fallback**: Anthropic `claude-haiku-4-5` — ~$0.01/build, cloud
- **Python**: 3.11+ inside WSL2
- **Node**: 20+ for the Next.js UI (`forgeos-ui/`)
- **Working dir**: `/home/padmaja/forge/forgeos` in WSL2

## Key commands

```bash
# Check Ollama is alive (WSL2)
curl -s http://127.0.0.1:11434/api/tags | python3 -m json.tool

# Run a build
PYTHONPATH=. python3 orchestrator.py --idea "Build a habit tracker SaaS"

# Run a build with an existing workdir (resume)
PYTHONPATH=. python3 orchestrator.py --idea "<same idea>" --workdir builds/<id>

# Start the FastAPI streaming server (port 8000)
PYTHONPATH=. python3 api.py

# Start the Next.js UI (port 3000)
cd forgeos-ui && npm run dev

# Run tests
PYTHONPATH=. python3 -m pytest tests/ -v

# Check current build state
cat builds/<id>/context.json | python3 -m json.tool | head -60
```

## Agent pipeline

**V2 pipeline** (default — `HermesOrchestrator` in `agents/hermes.py`):

| # | Agent | Base | Output | Gate? |
|---|-------|------|--------|-------|
| 0 | PMAgent | ForgeAgent | `pm_output` metadata | yes — blocks on dont_build |
| 1 | OfficeHoursGate | GStackGate | gate score | yes |
| 2 | CEOReviewGate | GStackGate | gate score | yes |
| 3 | ArchitectAgent | ForgeAgent | `SPEC.md`, `ARCH.md`, `TASKS.json`, `STACK.json` | no |
| 4 | EngReviewGate | GStackGate | gate score | yes |
| 5 | DesignShotgunGate | GStackGate | gate score | no |
| 6 | MissionOrchestrator | BaseAgent | mission plan | no |
| 7 | ScaffoldAgent | BaseAgent | project skeleton | no |
| 8 | GameAgent | BaseAgent | `project/game/` | no — skips if non-game |
| 9 | MissionWorkerLoop | BaseAgent | all features implemented | no |
| 10 | ReviewGate | GStackGate | gate score | yes |
| 11 | AdversarialGate | GStackGate | gate score | yes |
| 12 | ScoreGate | GStackGate | gate score | yes |
| 13 | SecurityAgent | BaseAgent | `SECURITY.md` | no |
| 14 | CSOGate | GStackGate | gate score | yes |
| 15 | QAGate | GStackGate | gate score | yes |
| 16 | MissionValidator | BaseAgent | validation contract | no |
| 17 | ShipGate | GStackGate | gate score | yes |
| 18 | EvalAgent | BaseAgent | `eval_output` metadata | yes — blocks if score < 80 |
| 19 | DeployAgent | BaseAgent | GitHub repo, Railway, Vercel | no — degrades gracefully |

**V1 legacy pipeline** (`--legacy` flag): ArchitectAgent → ScaffoldAgent → CoderAgent → GameAgent → SecurityAgent → DeployAgent

## LLM routing (current)

All task types use: **Ollama → Claude haiku-4-5**

```python
_HARD_STACK   = ("ollama", "claude")   # architecture, security
_MEDIUM_STACK = ("ollama", "claude")   # code review
_LOW_STACK    = ("ollama", "claude")   # scaffolding, formatting
```

The router calls `_is_available()` before each provider. Ollama requires the service running on port 11434. Claude requires `ANTHROPIC_API_KEY` in `.env`.

## ForgeADK — agent development standards

**ForgeAgent** (`forge_sdk/agent.py`) is the new base for all pipeline agents.
Inherit from `ForgeAgent`, not `BaseAgent`, for any new agent.

```python
from forge_sdk.agent import ForgeAgent

class MyAgent(ForgeAgent):
    name         = "my_agent"
    phase        = "build"
    capabilities = ["OUTPUT.md"]          # artifacts this agent writes
    requires     = ["idea", "spec"]       # context fields it reads
    budget_usd   = 0.20                   # max project spend before abort; 0=unlimited
    tools        = [...]                  # optional tool registry for agent-organizer

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        ...                               # raise NotImplementedError until ready
```

**Rules:**
- `_execute` must raise `NotImplementedError` if not implemented — never `pass`
- `budget_usd = 0.0` for agents that run before any significant spend (ArchitectAgent)
- All `_llm()` and `_write()` calls are auto-instrumented — never call `GBrainLogger` manually inside `_execute`
- If an agent calls Claude structured output directly, log the call yourself: `self._logger.log_event("structured_llm", {...})`
- `capabilities` / `requires` / `tools` are read by agent-organizer — keep them accurate

**Migrated to ForgeAgent:** ArchitectAgent, PMAgent
**Pending migration:** ScaffoldAgent, CoderAgent, SecurityAgent, EvalAgent, all GStack gates
**Planned (not yet implemented):** DesignAgent (`phase=design`), MediaAgent (`phase=media`)

**GBrainLogger** (`forge_sdk/glogger.py`) — per-agent event log:
- Writes `<workdir>/gbrain-events.jsonl` (tailed by SSE stream) + `~/.forgeos/gbrain/sessions/<proj_id>_<agent>.jsonl`
- `GBrainLogger.start(project_id, workdir)` is called automatically by `ForgeAgent.run()`
- Manual events: `self._logger.log_gate(...)`, `self._logger.log_event("my_event", {...})`

**Circular import rule (critical):**
`agents/__init__.py` uses lazy module `__getattr__` for all agent subclasses. `BaseAgent` is the only eager export. When a new agent imports from `forge_sdk`, it MUST NOT be eagerly imported in `agents/__init__.py` — add it to `_LAZY` instead.

## Agent mesh vision

ForgeOS V3 target: a fully-connected agent mesh where any agent can consult
any other agent without going through the linear HermesOrchestrator pipeline.

```
                    ┌─────────────┐
                    │  PMAgent    │  demand validation
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │     ArchitectAgent      │  spec + stack + tasks
              └──┬──────────┬───────────┘
                 │          │
        ┌────────▼──┐  ┌────▼────────┐
        │DesignAgent│  │ ScaffoldAgent│
        │ (planned) │  └──────┬───────┘
        └────────┬──┘         │
                 │      ┌─────▼──────┐
                 └──────► CoderAgent │  per-feature loop
                         └─────┬──────┘
                               │
                    ┌──────────▼──────────┐
                    │    MediaAgent       │  (planned)
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   SecurityAgent     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    EvalAgent        │  quality gate
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    DeployAgent      │
                    └─────────────────────┘
```

Each node in the mesh:
- Declares `capabilities` (what it produces) and `requires` (what it needs)
- Registers a `tools` list for agent-organizer auto-routing
- Emits structured events to GBrain via GBrainLogger
- Can be addressed directly by HermesOrchestrator or by other agents

The mesh enables: parallel feature coding (multiple CoderAgent instances),
design-to-code handoff (DesignAgent → ScaffoldAgent without architect re-run),
and live quality feedback loops (EvalAgent → CoderAgent for targeted fixes).

## GBrain knowledge store

`gbrain/` — persistent structured knowledge directory read before each build.

```
gbrain/
├── README.md                # schema + usage docs
├── knowledge.json           # index of all pattern files
└── patterns/
    ├── technical.json       # engineering patterns (stack, bugs, library quirks)
    └── legal.json           # India regulatory knowledge (ICA, GST, jurisdiction)
```

ArchitectAgent loads `technical.json` before producing ARCH.md.
LegalAgent loads `legal.json` before generating contracts.
ForgeBrain appends new patterns post-build.

## Stack conventions

**Backend (ForgeOS engine)**
- Python 3.11, FastAPI, Pydantic v2
- No relative imports — all absolute (`from models import X`, not `from .models import X`)
- `PYTHONPATH=.` must be set when running any module directly
- `models.py` is the canonical home for `LLMClient`, `LLMError`, `LLMResponse`
- New agents inherit from `forge_sdk.agent.ForgeAgent` (not `agents.base.BaseAgent` directly)

**Frontend (ForgeOS UI)**
- Next.js 14 App Router + TypeScript + Tailwind CSS
- shadcn/ui components, Framer Motion animations, dark mode only
- React Three Fiber for 3D hero scene (dynamic import, `ssr: false`)
- SSE streaming from `/builds/{id}/stream` to the agent card list

**Generated projects** (what ForgeOS builds)
- Default stack: Next.js 14 + FastAPI + Supabase
- Auth: Supabase Auth + RLS
- Deploy: GitHub → Railway (backend) + Vercel (frontend)

## File layout

```
forgeos/
├── orchestrator.py        # entry point — V1 legacy pipeline
├── api.py                 # FastAPI server with SSE streaming (agent_event + log)
├── models.py              # LLMClient, LLMError, LLMResponse (canonical)
├── config.py              # LLM, Stack, Deploy dataclasses + cost table
├── forge_brain.py         # Obsidian knowledge accumulation (post-build)
├── healer.py              # self-healing daemon (Sentry + UptimeRobot)
├── forge_sdk/             # ForgeADK — agent development kit
│   ├── __init__.py        # public: ForgeAgent, GBrainLogger, EventCallback
│   ├── agent.py           # ForgeAgent base (capabilities, requires, budget, events)
│   └── glogger.py         # GBrainLogger (per-agent JSONL event log)
├── gbrain/                # persistent knowledge store (checked in)
│   ├── README.md          # schema + usage docs
│   ├── knowledge.json     # index + stats
│   └── patterns/
│       ├── technical.json # engineering patterns (stack, bugs, library quirks)
│       └── legal.json     # India regulatory (ICA, GST, jurisdiction)
├── agents/
│   ├── __init__.py        # BaseAgent eager; all subclasses lazy via __getattr__
│   ├── base.py            # BaseAgent ABC (low-level; prefer ForgeAgent)
│   ├── architect.py       # ArchitectAgent  [ForgeAgent]
│   ├── pm_agent.py        # PMAgent         [ForgeAgent]
│   ├── design_agent.py    # DesignAgent     [ForgeAgent] — NotImplemented
│   ├── media_agent.py     # MediaAgent      [ForgeAgent] — NotImplemented
│   ├── scaffold.py        # ScaffoldAgent
│   ├── coder.py           # CoderAgent
│   ├── game.py            # GameAgent (Three.js/Phaser/Godot)
│   ├── security.py        # SecurityAgent
│   ├── legal_agent.py     # LegalAgent
│   ├── eval_agent.py      # EvalAgent
│   ├── deploy.py          # DeployAgent
│   ├── gstack.py          # GStackGate + 10 quality gates
│   ├── mission.py         # MissionOrchestrator, MissionWorkerLoop, MissionValidator
│   └── hermes.py          # HermesOrchestrator (V2 pipeline coordinator)
├── llm/
│   ├── base.py            # re-exports from models.py (thin shim)
│   ├── router.py          # route() — picks Ollama or Claude
│   ├── ollama.py          # OllamaClient
│   └── claude.py          # ClaudeClient (sonnet-4-6 default)
├── tools/
│   ├── github.py          # repo creation via GitHub API
│   ├── railway.py         # deploy via Railway API
│   ├── vercel.py          # deploy via Vercel API
│   ├── supabase_admin.py  # service-role Supabase client
│   ├── sentry.py          # Sentry issue watcher
│   └── uptimerobot.py     # uptime monitor setup
├── models/
│   └── outputs/           # Pydantic output models per agent
│       ├── architect_output.py
│       ├── pm_output.py
│       ├── eval_output.py
│       └── ...
├── dataset/
│   └── collector.py       # DatasetCollector — fine-tuning flywheel
├── .claude/
│   ├── settings.json      # MCP server config (Supabase, Context7, Playwright)
│   ├── settings.local.json
│   └── agents/            # Claude Code subagents (7 specialists)
└── builds/                # runtime output — one folder per build
    └── <build-id>/
        ├── context.json        # full pipeline state
        ├── gbrain-events.jsonl # GBrainLogger event stream (tailed by SSE)
        ├── SPEC.md
        ├── ARCH.md
        ├── TASKS.json
        ├── STACK.json
        ├── SECURITY.md
        └── project/            # the generated codebase
```

## Environment variables (`.env`)

```bash
# LLM — at minimum, one of these must be set
ANTHROPIC_API_KEY=sk-ant-...        # Claude haiku-4-5 fallback
OLLAMA_MODEL=qwen2.5-coder:7b      # default Ollama model

# Deploy — optional; agents degrade gracefully without these
GITHUB_TOKEN=ghp_...
RAILWAY_TOKEN=...
VERCEL_TOKEN=...

# Supabase — for generated projects and Supabase MCP
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_ACCESS_TOKEN=...           # for MCP server auth

# Monitoring — optional
SENTRY_DSN=...
UPTIMEROBOT_API_KEY=...
```

## MCP servers (Claude Code)

Configured in `.claude/settings.json`. Activate with `claude mcp` in the project directory.

| Server | Purpose |
|--------|---------|
| `supabase` | Query/manage Supabase projects, run SQL, manage Auth |
| `context7` | Fetch up-to-date library docs (Next.js, FastAPI, Supabase, etc.) |
| `playwright` | Browser automation for E2E testing of generated UIs |

## Subagents (Claude Code)

Seven specialist subagents in `.claude/agents/`. Invoke with `/agents` or let Claude auto-route.

| Agent | Use when |
|-------|----------|
| `fullstack-developer` | Building a complete SaaS (Next.js + FastAPI + Supabase) |
| `nextjs-developer` | Frontend-only work, App Router, RSC, performance |
| `backend-developer` | FastAPI endpoints, DB schema, auth middleware |
| `game-developer` | Any game (R3F, Phaser, Godot, RN+Skia) |
| `mobile-developer` | React Native + Expo iOS/Android apps |
| `agent-organizer` | Planning which agents to assemble for a new idea |
| `context-manager` | Resuming a failed build, reconstructing pipeline state |

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: attempted relative import` | Running as `__main__` without PYTHONPATH | `PYTHONPATH=. python3 orchestrator.py` |
| `ConnectionRefusedError` on port 11434 | Ollama not running | `ollama serve` in WSL2 |
| `ANTHROPIC_API_KEY not set` | Missing env | Add to `.env`, Claude will not be used as fallback |
| Build stops after ArchitectAgent | Coder tasks pending but CoderAgent skipped | Check `TASKS.json` — reset stuck tasks to `pending`, re-run |
| `UnicodeEncodeError` on Windows terminal | Arrow or emoji in output | Terminal is cp1252; remove non-ASCII from print statements |
| GameAgent runs on non-game idea | Bug in keyword detection | Check `_GAME_KEYWORDS` in `agents/game.py` |

## Output style for Claude

When answering questions about ForgeOS code:
- **Architect mode**: explain decisions, trade-offs, and invariants before showing code
- Full files only — no ellipsis, no truncation
- Absolute imports throughout (`from models import X`)
- When suggesting commands, always include `PYTHONPATH=.` prefix
- Prefer editing existing files over creating new ones
- Flag circular import risks immediately if spotted

## Build resumption (quick ref)

```bash
# 1. Find build ID
ls builds/

# 2. Check state
cat builds/<id>/context.json | python3 -m json.tool | head -60

# 3. Resume (skips completed agents automatically)
PYTHONPATH=. python3 orchestrator.py --idea "<original idea>" --workdir builds/<id>

# 4. If one task is stuck: set it back to pending in TASKS.json, then re-run
```
