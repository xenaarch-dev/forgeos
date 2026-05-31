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

Agents run in this fixed order. Each writes its output to `builds/<id>/` and updates `context.json`.

| # | Agent | Output | Auto-skip condition |
|---|-------|--------|---------------------|
| 1 | ArchitectAgent | `SPEC.md`, `ARCH.md`, `TASKS.json`, `STACK.json` | Never |
| 2 | ScaffoldAgent | Full project directory tree + config files | Never |
| 3 | CoderAgent | All `coder`-tagged tasks implemented | Never |
| 4 | GameAgent | Complete playable game in `project/game/` | Idea has no game keywords |
| 5 | SecurityAgent | `SECURITY.md`, RLS policies, secrets audit | Never |
| 6 | DeployAgent | GitHub repo, Railway deploy, Vercel deploy | Missing tokens (degrades) |

## LLM routing (current)

All task types use: **Ollama → Claude haiku-4-5**

```python
_HARD_STACK   = ("ollama", "claude")   # architecture, security
_MEDIUM_STACK = ("ollama", "claude")   # code review
_LOW_STACK    = ("ollama", "claude")   # scaffolding, formatting
```

The router calls `_is_available()` before each provider. Ollama requires the service running on port 11434. Claude requires `ANTHROPIC_API_KEY` in `.env`.

## Stack conventions

**Backend (ForgeOS engine)**
- Python 3.11, FastAPI, Pydantic v2
- No relative imports — all absolute (`from models import X`, not `from .models import X`)
- `PYTHONPATH=.` must be set when running any module directly
- `models.py` is the canonical home for `LLMClient`, `LLMError`, `LLMResponse`
- All agents inherit from `agents.base.BaseAgent`

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
├── orchestrator.py        # entry point, runs the agent pipeline
├── api.py                 # FastAPI server with SSE streaming
├── models.py              # LLMClient, LLMError, LLMResponse (canonical)
├── config.py              # LLM, Stack, Deploy dataclasses + cost table
├── forge_brain.py         # Obsidian knowledge accumulation
├── healer.py              # self-healing daemon (Sentry + UptimeRobot)
├── agents/
│   ├── base.py            # BaseAgent ABC
│   ├── architect.py       # ArchitectAgent
│   ├── scaffold.py        # ScaffoldAgent
│   ├── coder.py           # CoderAgent
│   ├── game.py            # GameAgent (Three.js/Phaser/Godot)
│   ├── security.py        # SecurityAgent
│   └── deploy.py          # DeployAgent
├── llm/
│   ├── base.py            # re-exports from models.py (thin shim)
│   ├── router.py          # route() function — picks Ollama or Claude
│   ├── ollama.py          # OllamaClient
│   └── claude.py          # ClaudeClient (haiku-4-5 default)
├── tools/
│   ├── github.py          # repo creation via GitHub API
│   ├── railway.py         # deploy via Railway API
│   ├── vercel.py          # deploy via Vercel API
│   ├── supabase_admin.py  # service-role Supabase client
│   ├── sentry.py          # Sentry issue watcher
│   └── uptimerobot.py     # uptime monitor setup
├── .claude/
│   ├── settings.json      # MCP server config (Supabase, Context7, Playwright)
│   ├── settings.local.json
│   └── agents/            # Claude Code subagents (7 specialists)
│       ├── fullstack-developer.md
│       ├── nextjs-developer.md
│       ├── backend-developer.md
│       ├── game-developer.md
│       ├── mobile-developer.md
│       ├── agent-organizer.md
│       └── context-manager.md
└── builds/                # runtime output — one folder per build
    └── <build-id>/
        ├── context.json   # full pipeline state, updated after each agent
        ├── SPEC.md
        ├── ARCH.md
        ├── TASKS.json
        ├── STACK.json
        ├── SECURITY.md
        └── project/       # the generated codebase
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
