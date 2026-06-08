# ForgeOS — Session State

**Date:** 2026-06-07  
**Branch:** master  
**Remote:** https://github.com/xenaarch-dev/forgeos.git (pushed — all 10 session commits live)  
**Session focus:** README rewrite, pip packaging, ScaffoldAgent migration, GBrain ArchitectAgent wiring, PMAgent test mocking

---

## Commits landed today

| Hash | Message |
|------|---------|
| `3d9757f` | feat: ForgeADK v0.1 — ForgeAgent base + GBrainLogger |
| `a08ac9c` | refactor: ArchitectAgent extends ForgeAgent |
| `7a33f42` | feat: wire GBrainLogger into api.py SSE stream |
| `be240ac` | refactor: PMAgent extends ForgeAgent |
| `6ca4f39` | feat: add DesignAgent and MediaAgent extending ForgeAgent |
| `c6f42f6` | feat: GBrain knowledge directory v0.1 — seeded |
| `396eb00` | docs: rewrite README as conversion document |
| `4d6beb0` | feat: pip packaging — forgeos CLI v0.1.0 (build, status, init) |
| `dba1760` | refactor: ScaffoldAgent extends ForgeAgent |
| `9c760a2` | feat: ArchitectAgent reads GBrain technical patterns at runtime |
| `cb88cd4` | feat: PMAgent tests — 27/27 green, no live API |

---

## What was built this session (2026-06-07 continuation)

### README rewrite (`README.md`)

Full rewrite as conversion document. Leads with ContractForge proof ($0.031 build cost),
20-stage pipeline table, 10 quality gates table, ForgeADK + GBrain sections, correct
GitHub URL (`xenaarch-dev/forgeos`), Railway deploy target.

### pip packaging (`forgeos/`, `pyproject.toml`)

`forgeos` CLI v0.1.0 installable via `pip install -e .`:
- `forgeos build "<idea>"` — runs the full pipeline (V2 default, `--legacy` for V1)
- `forgeos status [build_id]` — list all builds or drill into one
- `forgeos init` — scaffold `.env` from `.env.example` or built-in template
- `forgeos/pipeline.py` — `_ensure_repo_on_path()` adds repo root to `sys.path` at import time; no `ImportError`
- CP1252-safe: `→` and `—` replaced with ASCII equivalents in CLI output

### ScaffoldAgent migration (`agents/scaffold.py`)

`ScaffoldAgent` now extends `ForgeAgent` (was `BaseAgent`).
`capabilities = ["project/"]` | `requires = ["stack", "tasks"]` | `budget_usd = 0.0`
All 12 scaffold tests pass; no test code changed.

### GBrain → ArchitectAgent (`agents/architect.py`)

Self-improving loop: `ArchitectAgent` loads `gbrain/patterns/technical.json` at `__init__`,
formats patterns as "Learned patterns from previous builds:" block, and injects it BEFORE
the user idea in the system prompt. Silent on missing file. `_gbrain_path` constructor kwarg
provides a test seam. 2 new tests in `test_architect_output.py` (with content / missing file).

### PMAgent test mocking (`tests/test_pm_agent.py`)

All 3 `TestPMAgentIntegration` tests now run offline:
- `monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")` bypasses the env guard
- `monkeypatch.setattr(ClaudeClient, "complete_structured", lambda *a, **kw: PMOutput(**_valid_pm_output()))` replaces the real API call
- No assertion changed. No test logic changed. Only the external dependency is mocked.

---

## What was built (prior session — ForgeADK v0.1)

### ForgeADK (`forge_sdk/`)

New developer-facing SDK for writing ForgeOS pipeline agents.

**`forge_sdk/agent.py` — ForgeAgent**
- Inherits from `BaseAgent`; MRO: `ForgeAgent → BaseAgent → ABC → object`
- Declarative class attributes: `capabilities`, `requires`, `budget_usd`, `tools`
- `run()` override: GBrainLogger auto-integration, SSE event callback hook, USD budget enforcement
- Auto-instrumented: `_llm()` logs every LLM call (model/tokens/cost), `_write()` logs every artifact (relpath/bytes)
- `_describe()` returns machine-readable agent descriptor for agent-organizer routing
- `_emit()` fires events to both GBrainLogger and SSE callback simultaneously

**`forge_sdk/glogger.py` — GBrainLogger**
- Per-agent append-only event log
- Dual-write: `~/.forgeos/gbrain/sessions/<proj_id>_<agent>.jsonl` (global) + `<workdir>/gbrain-events.jsonl` (per-build, tailed by SSE)
- Event types: `start`, `llm_call`, `artifact`, `gate`, `success`, `error`, `finish`
- Accumulates cost/token totals across the run; writes `summary/` JSON on close

### SSE wiring (`api.py`)

`GET /builds/{id}/stream` now emits three SSE event shapes:
```
{"type": "log",         "text": "<stderr/stdout line>"}
{"type": "agent_event", "event": "<name>", "agent": "<name>", ...}
{"type": "done",        "status": "success"|"failed"}
```
Implementation: `_read_gbrain()` helper tails `<workdir>/gbrain-events.jsonl` by byte offset (seek + read), runs alongside the existing text-log poll on the same 0.5 s tick.

**Circular import fix:** `agents/__init__.py` changed from eager to lazy imports via module `__getattr__`. Only `BaseAgent` is eager. All agent subclasses load on first access and are cached in `globals()`. This was required because `forge_sdk.agent → agents.base → agents.__init__ → agents.architect → forge_sdk.agent` was a cycle.

### Agent migrations

**ArchitectAgent** → ForgeAgent  
`capabilities = ["SPEC.md", "ARCH.md", "TASKS.json", "STACK.json"]`  
`requires = ["idea"]` | `budget_usd = 0.0`

**PMAgent** → ForgeAgent  
`capabilities = ["pm_output"]`  
`requires = ["idea"]` | `budget_usd = 0.10`

### New agents (structure only)

**DesignAgent** (`agents/design_agent.py`)  
Phase: `design` | Budget: $0.15  
6 tools: figma_api, style_dictionary, chromatic_snapshot, axe_accessibility, shadcn_registry (req), llm_design_critic (req)  
`_execute` raises `NotImplementedError` with step-by-step implementation guide in docstring.

**MediaAgent** (`agents/media_agent.py`)  
Phase: `media` | Budget: $0.05  
8 tools: ffmpeg, pillow (req), cloudinary, bunny_cdn, supabase_storage (req), stable_diffusion_placeholder, sharp_cli, lighthouse_media_audit  
`_execute` raises `NotImplementedError` with step-by-step implementation guide in docstring.

### GBrain knowledge directory (`gbrain/`)

Checked-in structured knowledge store. Seeded with ContractForge learnings and India regulatory patterns.

**`gbrain/patterns/technical.json`** — 3 patterns:
- `supabase-subscriptions-table` — billing state: status column + Postgres trigger to sync profiles.plan
- `pdf-dejavusans-rupee-symbol` — DejaVuSans.ttf (Apache 2.0) required for ₹ glyph in all PDF libs
- `session-email-never-hardcoded` — always resolve from live JWT; never cache or hardcode

**`gbrain/patterns/legal.json`** — 4 patterns:
- `indian-contract-act-1872` — ICA S.10 requirements for valid SaaS ToS; click-wrap acceptance logging schema
- `gst-18-sac-998314` — SAC 998314 at 18% GST; intra-state CGST/SGST vs inter-state IGST; zero-rated exports
- `late-payment-18-percent` — 18% p.a. simple interest; grace 30 days; applies to base amount only (GST-exempt)
- `mumbai-jurisdiction-default` — Bombay HC exclusive jurisdiction; MCIA arbitration for contracts > ₹5 lakh

---

## Test status

| Suite | Passing | Failing | Notes |
|-------|---------|---------|-------|
| `test_agents.py` | 4/4 | 0 | full pass |
| `test_architect_output.py` | 17/17 | 0 | includes 2 new GBrain tests |
| `test_dataset_collector.py` | 19/19 | 0 | full pass |
| `test_eval_agent.py` | 19/19 | 0 | full pass |
| `test_legal_agent.py` | 7/13 | 6 | integration tests require live ANTHROPIC_API_KEY (pre-existing) |
| `test_orchestrator.py` | 4/4 | 0 | full pass |
| `test_pm_agent.py` | 27/27 | 0 | all integration tests mocked — no live API needed |
| `test_scaffold_output.py` | 12/12 | 0 | full pass after ScaffoldAgent migration |
| `test_security_output.py` | 15/15 | 0 | full pass |
| `test_tools.py` | 6/6 | 0 | full pass |
| `test_validator_output.py` | 7/7 | 0 | full pass |
| `test_worker_output.py` | 6/6 | 0 | full pass |
| **TOTAL** | **143/149** | **6** | 6 pre-existing legal agent failures (need Claude mock) |

GBrainLogger proof: 8 session `.jsonl` files + 8 summary `.json` files written during test run. `gbrain-events.jsonl` verified in workdir after ArchitectAgent smoke-test (7 events: start, 4 artifacts, success, finish).

---

## Open items / next session

- [x] **Git remote** — `origin` set to `https://github.com/xenaarch-dev/forgeos.git`; master pushed 2026-06-07.
- [x] **README rewrite** — conversion document, leads with ContractForge proof, no stubs.
- [x] **pip packaging** — `forgeos` CLI v0.1.0 installable, `build/status/init` commands.
- [x] **ScaffoldAgent migration** — extends `ForgeAgent`, 12/12 tests pass.
- [x] **GBrain → ArchitectAgent** — `technical.json` injected at init; self-improving loop active.
- [x] **PMAgent tests** — 27/27 green, no live API needed.
- [ ] **Migrate remaining agents** — CoderAgent, SecurityAgent, EvalAgent, all 10 GStack gates still extend `BaseAgent` not `ForgeAgent`
- [ ] **Mock LegalAgent integration tests** — same pattern as PMAgent: `monkeypatch.setattr(ClaudeClient, "complete_structured", ...)` to fix 6 failing tests
- [ ] **Commit orphaned files** — `agents/eval_agent.py`, `dataset/`, `models/outputs/eval_output.py`, `tests/test_dataset_collector.py`, `tests/test_eval_agent.py` (left untracked; already passing)
- [ ] **Implement DesignAgent._execute()** — step-by-step guide is in the class docstring
- [ ] **Implement MediaAgent._execute()** — step-by-step guide is in the class docstring
- [ ] **Wire `gbrain/` into LegalAgent** — load `legal.json` jurisdiction rules before contract generation
- [ ] **GBrain auto-ingest** — hook `ForgeBrain._append_dataset()` to also append to `gbrain/patterns/*.json` after each successful build

---

## Key invariants to preserve

1. `ForgeAgent.run()` is the single point of GBrainLogger lifecycle (`start` → `finish`) — never call `logger.start/finish` from `_execute`
2. `agents/__init__.py` must keep `BaseAgent` as the only eager import — all subclasses in `_LAZY`
3. `gbrain-events.jsonl` is append-only during a build — never truncate or rewrite
4. `budget_usd = 0.0` means unlimited — do not set it to a tiny value for first-in-pipeline agents
5. All ForgeOS `from` imports are absolute (`from models import X`, not `from .models import X`)
