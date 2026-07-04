# ForgeOS

Give it one sentence. Thirty minutes later, production SaaS is deployed.

---

## What shipped

**ContractForge** — [contractforge.co.in](https://contractforge.co.in)

AI contract generation for Indian freelancers. GST-compliant. DPDP Act 2023. ₹1,499 per contract
or ₹2,499/month. Instant generation, legally sound under the Indian Contract Act 1872. Mumbai
jurisdiction by default.

Built entirely by ForgeOS:

```bash
PYTHONPATH=. python3 orchestrator.py \
  --idea "AI contract generator for Indian freelancers, GST-compliant, INR pricing"
```

---

## Live homepage

[forgeos-eight.vercel.app](https://forgeos-eight.vercel.app) is `LandingV3` — a Roman/cosmic
hybrid design (Playfair Display, laurel/eclipse motifs, a starfield canvas) rendered as a single
page (`web/app/page.tsx`), with in-page anchors for Agents / How It Works / Proof / Dashboard
rather than separate routes.

All MRR, lead-pipeline, and agent-status figures on the page come from `/api/metrics`
(`web/app/app/api/metrics/route.ts`) — `force-dynamic`, no stale caching. It computes
`day_number` and `yc_days_remaining` from fixed baseline dates and reads real lead counts from
Supabase (`outreach_leads` table) when service-role credentials are present. `LandingV3` calls
this route through the `useMetrics()` hook (`web/hooks/useMetrics.ts`) and patches the DOM with
the live response — nothing on the page is hardcoded copy that happens to match reality.

The earlier S01–S13 "portal" component tree (the pre-LandingV3 marketing site) has been deleted
outright — it was fully orphaned once LandingV3 shipped.

---

## The system

The default pipeline is `HermesOrchestrator` (`agents/hermes.py`) — 20 stages, 11 blocking gates:

| # | Agent | Output | Gate? |
|---|-------|--------|-------|
| 0 | PMAgent | demand validation | yes |
| 1 | OfficeHoursGate | gate score | yes |
| 2 | CEOReviewGate | gate score | yes |
| 3 | ArchitectAgent | `SPEC.md`, `ARCH.md`, `TASKS.json`, `STACK.json` | no |
| 4 | EngReviewGate | gate score | yes |
| 5 | DesignShotgunGate | gate score | no |
| 6 | MissionOrchestrator | mission plan | no |
| 7 | ScaffoldAgent | project skeleton | no |
| 8 | GameAgent | `project/game/` (skipped if non-game) | no |
| 9 | MissionWorkerLoop | features implemented | no |
| 10 | ReviewGate | gate score | yes |
| 11 | AdversarialGate | gate score | yes |
| 12 | ScoreGate | gate score | yes |
| 13 | SecurityAgent | `SECURITY.md` | no |
| 14 | CSOGate | gate score | yes |
| 15 | QAGate | gate score | yes |
| 16 | MissionValidator | validation contract | no |
| 17 | ShipGate | gate score | yes |
| 18 | EvalAgent | quality score (blocks below 80) | yes |
| 19 | DeployAgent | GitHub repo, Railway, Vercel | no |

A V1 legacy pipeline (ArchitectAgent → ScaffoldAgent → CoderAgent → GameAgent → SecurityAgent →
DeployAgent) is still available via `--legacy` for the original flat flow without GStack gates or
Missions.

Gates block the pipeline on failure — no silent degradation.

---

## ModelRouter

Tiered routing (`llm/router.py`, `config/models.yaml`):

| Tier | Model | Role |
|------|-------|------|
| 1 (default) | GLM-5.2 (`openrouter/z-ai/glm-5.2`) | scaffolding, review, architecture, security — most agent turns |
| 2 (fallback) | `claude-sonnet-4-6` | used automatically when a GLM call fails; logs a warning (`[router] GLM call failed — falling back to Sonnet`) |
| 3 (frontier, gated) | `claude-fable-5` | architecture + security gates only, and only when `FORGEOS_FRONTIER_TIER=true` |
| Offline (opt-in) | Ollama `qwen2.5-coder:7b` | only when `FORGEOS_OFFLINE_MODE=true` — no longer a default tier |

GLM-5.2 requires `GLM_API_KEY` (OpenRouter). Sonnet/Fable-5 require `ANTHROPIC_API_KEY`.

---

## Daemon Mode

`ForgeOS_Daemon_Drain` runs every 15 minutes via Windows Task Scheduler, invoking
`daemon/drainer.py`. Each run polls Telegram for new build ideas (no-ops silently without
`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`), pops the oldest job from a flat-file FIFO queue at
`builds/queue/pending/`, runs it through `HermesOrchestrator`, and archives it to
`builds/queue/archive/`. Decision record: [ADR-001](docs/adr/ADR-001-daemon-mode.md).

`job_queue.py` / `worker_daemon.py` (a separate Redis + RQ queue) exist in the repo but are not
imported anywhere in the active pipeline — treat them as superseded by the flat-file drainer
above, not as the current mechanism.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 App Router + TypeScript + Tailwind |
| Backend | FastAPI · Python 3.12 |
| Database | Supabase — Postgres + Auth + RLS |
| Payments | Lemon Squeezy |
| Deploy | Render (backend) · Vercel (frontend) |
| Secrets | Doppler |
| LLM routing | GLM-5.2 default → Sonnet fallback → Fable-5 (gated frontier tier) — see [ModelRouter](#modelrouter) |
| Agent framework | ForgeADK (this repo) |

---

## Tests

**309 passing, 3 skipped, 312 total** (skips are semgrep integration tests — need the `semgrep`
binary on `PATH`).

```bash
PYTHONPATH=. python3 -m pytest tests/ -q
```

---

## Design system

The live homepage (`web/components/v3/LandingV3.tsx`) uses a Roman/cosmic hybrid palette:

| Token | Value | Use |
|-------|-------|-----|
| Background | `#08090B` | Page background |
| Text | `#ECEBE6` | Body text |
| Accent | `#A4D8FF` | Links, CTAs, data highlights |
| Heading | Playfair Display | Display type, laurel/eclipse motifs |
| Mono | DM Mono | Nav, labels, stats |
| Sans | DM Sans | Body copy |
| Data | Space Grotesk | Stat counters |

(The earlier "Night Forge" token set — void-black/teal/gold — belonged to the deleted S01–S13
portal and no longer exists anywhere in the codebase.)

---

## India-first

Not a default — a choice made at every layer.

- Voice synthesis: `en-IN-NeerjaNeural`
- Contract law: Indian Contract Act 1872
- Tax: GST 18% · SAC codes
- Jurisdiction: Mumbai
- Currency: INR first, USD second
- Privacy: DPDP Act 2023

---

## ForgeADK — writing agents

```python
from forge_sdk.agent import ForgeAgent

class MyAgent(ForgeAgent):
    name         = "my_agent"
    phase        = "build"
    capabilities = ["OUTPUT.md"]
    requires     = ["idea", "spec"]
    budget_usd   = 0.20

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        resp = self._llm(context, "...", purpose="my_task")
        self._write(context, "OUTPUT.md", resp.text)
        return {"my_agent": "done"}
```

Every `_llm()` and `_write()` call is auto-instrumented — model, tokens, cost, artifact size —
logged to `gbrain-events.jsonl` and streamed to the dashboard over SSE.

---

## Quick start

```bash
git clone https://github.com/xenaarch-dev/forgeos
cd forgeos
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your keys — minimum:
`GLM_API_KEY` (Tier-1 default) or `ANTHROPIC_API_KEY` (Sonnet/Fable-5), plus `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`.

```bash
PYTHONPATH=. python3 orchestrator.py --idea "Your idea here"
```

Resume an interrupted build:

```bash
PYTHONPATH=. python3 orchestrator.py --idea "<same idea>" --workdir builds/<id>
```

---

## Environment

```bash
# LLM — GLM_API_KEY is the Tier-1 default; ANTHROPIC_API_KEY covers Sonnet fallback + Fable-5
GLM_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
FORGEOS_FRONTIER_TIER=false   # true to enable Fable-5 for architecture/security gates
FORGEOS_OFFLINE_MODE=false    # true to force Ollama qwen2.5-coder:7b, no API key needed

GITHUB_TOKEN=ghp_...
RENDER_API_KEY=...
RENDER_OWNER_ID=...
VERCEL_TOKEN=...

SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

SENTRY_DSN=...
LEMONSQUEEZY_API_KEY=...

# Daemon Mode — build-idea intake, optional
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## Repo

Public — [github.com/xenaarch-dev/forgeos](https://github.com/xenaarch-dev/forgeos). Confirmed
secrets-history-clean as of Day 176 (2026-07-04).

---

## License

MIT — see [LICENSE](LICENSE).

---

*ForgeOS · $0.01–$0.05 per build*
