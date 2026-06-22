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

## The system

18 stages. 10 blocking gates. 7 agents.

| Agent | Name | What it does |
|-------|------|-------------|
| PMAgent | Maya | Demand validation — go/no-go before a line of code is written |
| ArchitectAgent | Aria | SPEC.md, ARCH.md, TASKS.json, STACK.json |
| ScaffoldAgent | Rex | Full project tree, configs, Supabase schema |
| SecurityAgent | Marcus | OWASP audit, RLS policies, SECURITY.md |
| EvalAgent | Nova | Composite quality score — blocks pipeline if < 80 |
| LegalAgent | Lexi | India-specific clauses, GST compliance |
| DeployAgent | Kira | GitHub repo, Render API, Vercel frontend |

Gates run between agents and block the pipeline on failure. No silent degradation.

---

## Daemon Mode

`ForgeOS_Daemon_Drain` runs every 15 minutes via Windows Task Scheduler.

Flat-file JSON queue at `queue/pending/`. The drainer picks up queued jobs, checks the
auto-deploy guard (no deploy after 22:00 IST), and processes in order.
Decision record: [ADR-001](docs/adr/ADR-001-daemon-mode.md).

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
| Local inference | Ollama `qwen2.5-coder:7b` · RTX 4050 |
| Agent framework | ForgeADK (this repo) |

---

## Tests

**244 / 244 passing.**

- Group A: 12 — core models, LLM routing
- Group B: 199 — agent pipeline, gates, tools
- Group C: 33 — system tests, daemon

---

## Night Forge design system

| Token | Value | Use |
|-------|-------|-----|
| `void-black` | `#07050F` | Background |
| `teal` | `#00E5CC` | Primary accent, CTAs |
| `gold` | `#E8961F` | Pricing, warnings |
| `violet` | `#7C3AED` | Secondary accent |
| Heading | Cormorant Garamond | Display |
| Mono | Space Mono | Code, data |

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
`ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

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
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_MODEL=qwen2.5-coder:7b

GITHUB_TOKEN=ghp_...
VERCEL_TOKEN=...

SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

SENTRY_DSN=...
LEMON_SQUEEZY_API_KEY=...
```

---

## License

MIT — see [LICENSE](LICENSE).

---

*ForgeOS · RTX 4050 · WSL2 Ubuntu 22.04 · $0.01–$0.05 per build*
