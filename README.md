# ForgeOS

> One English sentence. One command. A production-ready SaaS — built, tested, secured, deployed.

ForgeOS is an autonomous product factory. It runs a 20-stage, LLM-gated pipeline that turns a plain-language idea into a working codebase, architecture docs, security audit, GitHub repo, and cloud deployment — in 30–45 minutes, for under $0.05.

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Version](https://img.shields.io/badge/version-2.0-violet.svg)](CHANGELOG.md)

---

## Proof it works

ContractForge — an AI contract generator SaaS at $29/mo — was built entirely by ForgeOS:

```bash
PYTHONPATH=. python3 orchestrator.py \
  --idea "Build ContractForge — AI contract generator SaaS at $29/mo"
```

**Output, 42 minutes later:**
- `SPEC.md` + `ARCH.md` + `TASKS.json` + `STACK.json` + `VALIDATION_CONTRACT.json`
- Full Next.js 14 + FastAPI + Supabase scaffold
- 8 features implemented, each in its own git commit
- Adversarial code review passed (score 8.3 / 10)
- OWASP security audit + RLS policies + CSO sign-off
- GitHub repo created, Railway API deployed, Vercel frontend live
- Total LLM cost: **$0.031**

---

## Why not just prompt ChatGPT?

Prompting an LLM gives you code. ForgeOS gives you a **product** — the difference is what happens between the prompt and the deploy.

10 LLM-powered quality gates are woven into the pipeline. Each gate calls an LLM with a specialised evaluation prompt, parses `PASS/FAIL` + `SCORE: N/10`, and **blocks the pipeline** if the bar isn't met:

| Gate | Phase | Blocks? | Minimum |
|------|-------|---------|---------|
| `office_hours` | Demand validation | yes | strategic fit |
| `ceo_review` | Business review | yes | viable market |
| `eng_review` | Technical design | yes | feasible stack |
| `design_shotgun` | UX review | no | — |
| `review` | Code quality | yes | 7.0 / 10 |
| `adversarial` | Attack surface | yes | no criticals |
| `score` | Holistic score | yes | 7.0 / 10 |
| `cso` | Security sign-off | yes | OWASP pass |
| `qa` | QA gate | yes | 7.0 / 10 |
| `ship` | Deploy readiness | yes | all checks green |

The pipeline won't ship code that doesn't pass. If a gate fails, the build stops — no silent degradation.

---

## The 20-stage pipeline

```
PMAgent(G) → OfficeHours(G) → CEOReview(G) → ArchitectAgent →
EngReview(G) → DesignShotgun →
MissionOrchestrator → ScaffoldAgent → [GameAgent] →
MissionWorkerLoop →
Review(G) → Adversarial(G) → Score(G) →
SecurityAgent → CSO(G) → QA(G) →
MissionValidator → Ship(G) →
EvalAgent(G, ≥80) → DeployAgent
```

`(G)` = blocking gate. `[GameAgent]` = skipped for non-game ideas. `EvalAgent` blocks if the composite quality score is below 80.

**Stage breakdown:**

| # | Agent | What it does |
|---|-------|-------------|
| 0 | PMAgent | Demand validation + go/no-go (blocks on `dont_build`) |
| 1–2 | OfficeHoursGate, CEOReviewGate | Strategic + business review |
| 3 | ArchitectAgent | Produces SPEC, ARCH, TASKS, STACK |
| 4–5 | EngReviewGate, DesignShotgunGate | Technical feasibility + UX review |
| 6 | MissionOrchestrator | Writes ValidationContract (acceptance criteria before code) |
| 7–8 | ScaffoldAgent, GameAgent | Full project tree + game layer if needed |
| 9 | MissionWorkerLoop | Feature-by-feature implementation, one commit per feature |
| 10–12 | ReviewGate, AdversarialGate, ScoreGate | Three-layer code quality gauntlet |
| 13 | SecurityAgent | OWASP audit + RLS policies → SECURITY.md |
| 14–16 | CSOGate, QAGate, MissionValidator | Security sign-off, QA, contract validation |
| 17 | ShipGate | Final deploy readiness check |
| 18 | EvalAgent | Composite quality score (blocks if < 80) |
| 19 | DeployAgent | GitHub repo + Railway (API) + Vercel (UI) |

---

## What ForgeOS builds

Every generated product ships with:

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 App Router + TypeScript + Tailwind CSS |
| Backend | FastAPI + Pydantic v2 |
| Database | Supabase (Postgres + Auth + Row-Level Security) |
| Payments | Lemon Squeezy |
| Secrets | Doppler |
| Deploy | GitHub → Railway (API) + Vercel (UI) |
| Tests | pytest + Vitest |
| Monitoring | Sentry + UptimeRobot |

---

## Quick Start

### Prerequisites

- WSL2 (Ubuntu 22.04) + Python 3.11+
- `ANTHROPIC_API_KEY` in `.env`
- [Ollama](https://ollama.ai) with `qwen2.5-coder:7b` — free, GPU-accelerated (optional but recommended)
- Node 20+ for the UI

### Install

```bash
git clone https://github.com/xenaarch-dev/forgeos
cd forgeos
cp .env.example .env
# Add ANTHROPIC_API_KEY at minimum
pip install -r requirements.txt
```

### Run a build

```bash
# V2 pipeline (default)
PYTHONPATH=. python3 orchestrator.py --idea "Build a habit tracker SaaS at $12/mo"

# Resume an interrupted build
PYTHONPATH=. python3 orchestrator.py --idea "<same idea>" --workdir builds/<id>

# V1 legacy pipeline
PYTHONPATH=. python3 orchestrator.py --idea "..." --legacy
```

### Start the dashboard

```bash
# Terminal 1 — ForgeOS API + SSE stream (port 8000)
PYTHONPATH=. python3 api.py

# Terminal 2 — Next.js dashboard (port 3000)
cd forgeos-ui && npm run dev
```

Open [localhost:3000](http://localhost:3000) to watch the build pipeline in real time — each agent emits structured events over SSE as it runs.

---

## LLM routing

| Task | Provider chain |
|------|---------------|
| Architecture & planning | Ollama → Claude Sonnet 4 |
| Code review & quality gates | Ollama → Claude Haiku 4.5 |
| Scaffolding & formatting | Ollama → Claude Haiku 4.5 |
| Feature implementation | Claude Code CLI → LLM fallback |

Ollama (`qwen2.5-coder:7b`) runs free on local GPU and is tried first. Claude is the cloud fallback. Typical build cost: **$0.01–$0.05**.

---

## Notifications

ForgeOS sends build notifications via **[Hermes Agent](https://hermes-agent.nousresearch.com)** (optional). Supports Telegram, Discord, Slack.

```bash
hermes gateway setup   # choose your channel
hermes gateway run     # receives commands, sends notifications
```

Once the gateway is running you can trigger builds from Discord:

> `build a habit tracker SaaS at $12/mo`

---

## ForgeADK — writing pipeline agents

Every ForgeOS agent inherits from `ForgeAgent` (`forge_sdk/agent.py`):

```python
from forge_sdk.agent import ForgeAgent

class MyAgent(ForgeAgent):
    name         = "my_agent"
    phase        = "build"
    capabilities = ["OUTPUT.md"]      # artifacts this agent writes
    requires     = ["idea", "spec"]   # context fields it reads
    budget_usd   = 0.20               # max build spend before abort; 0.0 = unlimited

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        resp = self._llm(context, "...", purpose="my_task")
        self._write(context, "OUTPUT.md", resp.text)
        return {"my_agent": "done"}
```

Every `_llm()` and `_write()` call is auto-instrumented — model, tokens, cost, and artifact size are logged to `gbrain-events.jsonl` and streamed live to the dashboard over SSE. No manual logging needed.

`capabilities` and `requires` are read by the agent-organizer for auto-routing. `budget_usd` enforces a hard spend cap — the agent raises `LLMError` if the build has already exceeded it before the agent even starts.

---

## GBrain — knowledge that grows with every build

`gbrain/patterns/` is a checked-in structured knowledge store that agents read before producing output:

- `technical.json` — engineering patterns accumulated across builds (e.g. Supabase billing triggers, PDF font requirements, session token hygiene)
- `legal.json` — India regulatory knowledge (ICA 1872, GST SAC codes, late-payment interest, Mumbai jurisdiction defaults)

ArchitectAgent loads `technical.json` before producing `ARCH.md`. After each successful build, ForgeBrain appends new patterns — the system gets smarter over time.

---

## Environment variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional — LLM
OLLAMA_MODEL=qwen2.5-coder:7b
ANTHROPIC_MODEL=claude-haiku-4-5

# Optional — Deploy
GITHUB_TOKEN=ghp_...
RAILWAY_TOKEN=...
VERCEL_TOKEN=...

# Optional — Generated project database
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_ACCESS_TOKEN=...

# Optional — Notifications (Hermes)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Optional — Monitoring
SENTRY_AUTH_TOKEN=...
UPTIMEROBOT_API_KEY=...

# Optional — Pipeline tuning
GSTACK_MIN_SCORE=7.0        # gate pass threshold (default 7.0)
MISSION_MAX_FEATURES=12     # max features per build
```

---

## File layout

```
forgeos/
├── orchestrator.py          # entry point — V2 pipeline or --legacy V1
├── api.py                   # FastAPI + SSE streaming dashboard
├── models.py                # LLMClient, ProjectContext, GateResult
├── config.py                # LLM, Stack, Deploy config + cost table
├── forge_brain.py           # Obsidian knowledge accumulation (post-build)
├── healer.py                # self-healing daemon (Sentry + UptimeRobot)
├── forge_sdk/               # ForgeADK — agent development kit
│   ├── agent.py             # ForgeAgent: capabilities, budget, auto-instrumentation
│   └── glogger.py           # GBrainLogger: per-run structured JSONL event log
├── gbrain/                  # Persistent knowledge store (checked in)
│   ├── knowledge.json       # Index + stats
│   └── patterns/
│       ├── technical.json   # Engineering patterns
│       └── legal.json       # India regulatory knowledge
├── agents/
│   ├── base.py              # BaseAgent ABC (low-level; prefer ForgeAgent)
│   ├── architect.py         # ArchitectAgent — SPEC/ARCH/TASKS/STACK
│   ├── pm_agent.py          # PMAgent — demand validation
│   ├── scaffold.py          # ScaffoldAgent — full project tree
│   ├── mission.py           # MissionOrchestrator/WorkerLoop/Validator
│   ├── security.py          # SecurityAgent — OWASP + RLS
│   ├── eval_agent.py        # EvalAgent — composite quality gate (≥80)
│   ├── deploy.py            # DeployAgent — GitHub + Railway + Vercel
│   ├── gstack.py            # 10 GStack quality gates
│   └── hermes.py            # HermesOrchestrator — V2 pipeline coordinator
├── llm/
│   ├── router.py            # route() — Ollama → Claude
│   ├── ollama.py            # OllamaClient
│   └── claude.py            # ClaudeClient
├── tools/                   # GitHub, Railway, Vercel, Supabase, Sentry, UptimeRobot
├── models/
│   └── outputs/             # Pydantic output models per agent
├── dataset/
│   └── collector.py         # Fine-tuning flywheel — appends build metadata
└── builds/                  # Runtime output — one folder per build
    └── <id>/
        ├── context.json
        ├── gbrain-events.jsonl        # GBrainLogger event stream (tailed by SSE)
        ├── SPEC.md  ARCH.md  TASKS.json  STACK.json
        ├── VALIDATION_CONTRACT.json
        ├── SECURITY.md
        └── project/                   # The generated codebase
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ImportError: attempted relative import` | Run as `PYTHONPATH=. python3 orchestrator.py` |
| `ConnectionRefusedError` on port 11434 | Start Ollama: `ollama serve` |
| Build stops after ArchitectAgent | Check `TASKS.json` — reset stuck tasks to `pending`, re-run |
| `ANTHROPIC_API_KEY not set` | Add to `.env`; Claude gates will not run |
| `UnicodeEncodeError` on Windows terminal | Remove non-ASCII from print paths; use WSL2 terminal |

---

## License

MIT — see [LICENSE](LICENSE).

---

*ForgeOS V2 · RTX 4050 + WSL2 Ubuntu 22.04 · $0.01–$0.05 per build*
