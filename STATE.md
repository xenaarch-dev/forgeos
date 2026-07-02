# ForgeOS — Session State

**Date:** 2026-07-02
**Day:** 174
**Day-N rule:** Computed fresh each session from `date +%Y-%m-%d` using `floor((today − 2026-01-10) / 86_400_000) + 1` — NEVER incremented from the previous session's value, regardless of how many sessions occur per calendar day.
**Branch:** main (not master — same repo, xenaarch-dev/forgeos, default branch is main)
**Remote:** https://github.com/xenaarch-dev/forgeos.git (5 commits ahead of origin/main — push pending)
**Session focus:** Day 173 — ModelRouter v2 (GLM-5.2 Tier 1, Fable-5 Tier 3 gated), Semgrep execution-verified security gate, SPEC_RepairLoop.md, FORGE_BRAIN.md company brain

---

## Day 174 — Completed (2026-07-02)

### ModelRouter v2 — Task 1 CLOSED ✓

**Verification scope:** Two checks only — no new features.

**CHECK 1 — GLM-5.2 live:** ❌ `GLM_API_KEY` is not set in either WSL2 (`~/.bashrc`) or Windows shell. `GLMClient.__init__` raises `LLMError: GLM_API_KEY is not set.` immediately. Key must be obtained at openrouter.ai and added: `export GLM_API_KEY='sk-or-v1-...'`.

**CHECK 2 — Fallback warning logged:** Gap found and fixed.

Original gap: when `GLM_API_KEY` IS set but the actual API call raises (network timeout, quota, wrong model slug), `complete()` was catching the exception silently and falling back to Sonnet with no log output. The "key missing" path already warned via `sys.stderr.write()` in `_is_available()`.

**Fix (`llm/router.py`):** Added `import logging` + `_log = logging.getLogger(__name__)`. In `complete()`, both `except LLMError` and `except Exception` blocks now call `_log.warning("[router] GLM call failed — falling back to Sonnet. Error: %s", e)` when `client_name == "glm52"`.

**New test (`tests/test_model_router.py`):** `TestCompleteGLMCallFailure::test_glm_call_failure_logs_warning_and_falls_back_to_sonnet` — sets `GLM_API_KEY` + `ANTHROPIC_API_KEY`, mocks `GLMClient.complete` to raise `LLMError`, mocks `ClaudeClient.complete` to return a fake response, asserts a `WARNING` log fires mentioning "GLM" and "fall", and asserts Sonnet response is returned.

**Tests:** 312 total — 309 passing, 3 skipped (integration/semgrep, need semgrep binary on PATH).

**Task 1 (ModelRouter v2) status: CLOSED.**

---

## Day 173 — Completed (2026-07-01)

### ModelRouter v2 — `6b248a9`

GLM-5.2 (zhipuai/glm-z1-32b via OpenRouter) becomes the Tier 1 default for all build stages. qwen2.5-coder:7b is retired as primary — lives on only via `FORGEOS_OFFLINE_MODE=true`. claude-fable-5 added as gated Tier 3 for architecture + security task types when `FORGEOS_FRONTIER_TIER=true`.

**New files**: `llm/glm.py` — GLMClient (OpenAI-compatible, targets OpenRouter), `config/models.yaml` rewritten with `[stages]` + `[frontier]` blocks.

**Modified**: `llm/router.py` — `_select_chain()` three-tier + offline logic; `config.py` — `LLMConfig` fields `glm_api_key`, `glm_model`, `glm_base_url`, `frontier_tier`, `offline_mode`; `agents/gstack.py` — `_gate_call()` `task_type` param, CSOGate passes `task_type="security"`; `AGENTS.md` — ModelRouter v2 rules block (31 sections total).

**Tests**: 22 new in `tests/test_model_router.py` — **298/298 green** at commit.

### Semgrep gate + SPEC_RepairLoop — `a43230c`

**SecurityAgent** (`agents/security.py`) gains `_run_semgrep()`: calls `semgrep --config=auto --json --quiet`, prepends binary dir to PATH (fixes pysemgrep resolution on Windows), returns `[]` on any failure. `_find_semgrep_binary()` checks Scripts/ and `%APPDATA%/Python/Python311/Scripts/` as fallback. Results stored in `context.metadata["security"]["semgrep"]` with `blocking=True` when ERROR-severity findings exist.

**CSOGate** (`agents/gstack.py`) checks `semgrep.blocking` BEFORE calling LLM — hard-fails gate with finding count + check_id details if true.

**SECURITY.md** render now has a dedicated "Semgrep Static Analysis (execution-verified)" section at top with ERROR finding table or clean confirmation.

**`forge_sdk/specs/SPEC_RepairLoop.md`** — full spec: pipeline position (between stage 9-10), 4 test runner detection table, 3-attempt loop pseudocode, exhaustion behavior (REPAIR_SUMMARY.md + halt), failure feedback format (tail 3000 chars), LLM tier per attempt (GLM→GLM→Sonnet), cost analysis (~$0.05 worst case), 5 open questions.

**Tests**: 13 new in `tests/test_semgrep_gate.py` — **311/311 green** at commit. `pyproject.toml` — `integration` marker registered.

---

## Day 163 — Completed (2026-06-23)

### outreach_leads migration — live in production Supabase

Migration `supabase/migrations/20260622000000_outreach_leads.sql` run manually via Supabase SQL editor (project: vcjicrqfnwdegggkrlpd). Confirmed: table, trigger (`outreach_leads_updated_at`), and RLS all created successfully. `OutreachForgeAgent.queue_for_approval()` can now write to production.

### MigrationNotRunError + verify_migration() — `0d4bccd`

- `MigrationNotRunError(Exception)` added to `agents/outreach.py`
- `verify_migration()`: `SELECT id FROM outreach_leads LIMIT 1` — prints "Migration confirmed: outreach_leads exists" on success, raises `MigrationNotRunError` with SQL editor remediation link on any failure
- `test_verify_migration_raises_on_missing_table`: mocks `execute()` raising postgrest-style exception, asserts `MigrationNotRunError` propagates
- **273/273 green** (was 272 — +1 new test)

### Discord approval notifications — `7b08c01`

Telegram permanently removed from plan (Section 69A IT Act, still blocked in India as of Day 163). Discord webhook is the approval channel.

**`agents/outreach.py`**:
- `send_approval_notification(lead_id, lead_name, draft_message) -> bool` — async method: POSTs Discord embed to `DISCORD_WEBHOOK_URL`, returns True on HTTP 204, False on any error or missing env var, never raises
- Embed format: content = "🔔 **OutreachForge — Approval Required**", embed title = lead name, description = draft, footer = "Lead ID: {id} | Reply: /approve {id} or /reject {id}", color = 15105570 (orange)
- `queue_for_approval()` updated: extracts `lead_id` from insert result, calls notification via `asyncio.run()` in a best-effort try/except
- Imports added: `asyncio`, `logging`, `httpx`; `_log = logging.getLogger(__name__)` added at module level

**Discord webhook setup instructions** (run manually when ready):
```bash
# Add to WSL2 ~/.bashrc:
echo 'export DISCORD_WEBHOOK_URL="paste_webhook_url_here"' >> ~/.bashrc
source ~/.bashrc

# Create the webhook:
# 1. Open any Discord server (or create one called "ForgeOS Control")
# 2. Any channel → Edit Channel → Integrations → Webhooks → New Webhook
# 3. Name it "OutreachForge" → Copy Webhook URL → paste into command above
```

**Tests** (3 new):
- `test_send_approval_notification_success`: mocks `httpx.AsyncClient`, asserts True on 204
- `test_send_approval_notification_missing_env`: no `DISCORD_WEBHOOK_URL`, asserts False without raising
- `test_queue_for_approval_triggers_discord_notification`: mocks Supabase + `send_approval_notification` (AsyncMock), asserts called with correct lead_id/name/draft

**276/276 green** (was 273 — +3 new tests)

### YC application draft — `yc/application_draft.md` (not committed)

Two versions written. Version B (ContractForge leads, ForgeOS as engine) flagged as stronger. Xena to review and edit before commit.

---

## Day 162 — Completed (2026-06-22)

### README rewritten — `e5b2cee`

`README.md` fully rewritten. 82 insertions, 232 deletions. Night Forge tone — dark, precise, builder-voice, no startup marketing. No badges.

Content: what shipped (ContractForge), the 18-stage pipeline, 7 named agents, Daemon Mode, stack (Python 3.12 / Render+Vercel), 244 tests, Night Forge design tokens, India-first deliberate choices, ForgeADK snippet, quick start.

`.env.example` exists at root — referenced as prose: "Copy `.env.example` to `.env` and add your keys — minimum: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`."

### OutreachForgeAgent v1 — `436c5d2`

Four files shipped in one commit:

**`agents/outreach.py`** — `OutreachForgeAgent(ForgeAgent)`:
- `name="outreach_forge"`, `phase="outreach"`, `budget_usd=0.05`
- `_execute` raises `NotImplementedError` — not a HermesOrchestrator pipeline stage
- Public API: `draft_message(lead)` → `queue_for_approval(lead, draft)` → `mark_approved(lead_id)` → `mark_sent(lead_id)` + `get_pending_approvals()`
- `draft_message`: validates required fields (`name`, `platform`, `fit_context`), calls `ClaudeClient.complete()` with ContractForge positioning prompt, peer-to-peer voice, max 4 sentences
- All Supabase calls through `_supabase_client()` static method (service role key)
- **HARD RULE** enforced in code comment and docstring: nothing sends automatically, ever

**`agents/__init__.py`** — `OutreachForgeAgent` added to `_LAZY` + `__all__` under "Standalone utilities" comment

**`supabase/migrations/20260622000000_outreach_leads.sql`** — new `supabase/migrations/` directory:
- `outreach_leads` table: `id`, `name`, `handle`, `platform` (check: x/email/linkedin), `fit_context`, `status` (check: drafted/approved/sent), `draft_message`, `approved_at`, `sent_at`, `reply_received`, `follow_up_draft`, `created_at`, `updated_at`
- `updated_at` trigger via `update_updated_at()` function
- RLS enabled, service role only — not exposed to end users

**`tests/test_outreach_agent.py`** — 28 unit tests, 6 classes:
- `TestDraftMessage` (7): missing-field validation, missing API key, return value, handle optional
- `TestQueueForApproval` (5): status=drafted enforced, payload fields, no sent_at/approved_at on insert, correct table, Supabase error handling
- `TestGetPendingApprovals` (4): returns list, filters status=drafted, correct table, None→[] guard
- `TestMarkApproved` (5): status=approved, approved_at set, id filter, sent_at absent, Supabase error handling
- `TestMarkSent` (5): status=sent, sent_at set, id filter, approved_at absent, Supabase error handling
- `TestSupabaseClient` (2): SUPABASE_URL missing, SUPABASE_SERVICE_ROLE_KEY missing
- All Supabase calls mocked via `patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client)`
- `TestSupabaseClient` mocks `sys.modules["supabase"]` — the Windows env has a broken `supabase` package install (`create_client` not importable), so the mock bypasses the ImportError to reach the env var check
- **28 / 28 passed** (`0.23s`)

### .mcp.json + .gitignore — `cd81f88`

**`.mcp.json`** (new, not committed — gitignored):
```json
{
  "mcpServers": {
    "magic":           { "command": "npx", "args": ["-y", "@21st-dev/magic@latest"],         "env": { "API_KEY": "PLACEHOLDER_REPLACE_AFTER" } },
    "nano-banana-pro": { "command": "npx", "args": ["@rafarafarafa/nano-banana-pro-mcp"],     "env": { "GEMINI_API_KEY": "PLACEHOLDER_REPLACE_AFTER" } }
  }
}
```
Fill in real keys then restart the Claude Code session — tools will appear. `.mcp.json` is added to `.gitignore` (API keys, not for git).

Note: `SPEC-OutreachForge-v1.md` (`docs/specs/SPEC-OutreachForge-v1.md`) was confirmed present on remote at `569e8ac` — created in WSL2 in Day 161. OutreachForge agent was built matching that spec.

---

## Day 161 — Completed (2026-06-19)

### Group C test run — 33/33 passed (`/tmp/groupc_final.txt`)

Full suite: `PYTHONPATH=. python3 -m pytest -k "integration or FromAgent" -v`  
- 244 collected, 211 deselected, **33 selected — all passed** in 1878.38 s (0:31:18)
- Machine confirmed quiet before run: no user python3 processes, Ollama idle, GPU 18%/480 MiB

| File | Tests |
|------|-------|
| `test_architect_output.py` | 10 |
| `test_eval_agent.py` | 1 |
| `test_legal_agent.py` | 6 |
| `test_pm_agent.py` | 3 |
| `test_scaffold_output.py` | 8 |
| `test_security_output.py` | 5 |
| **Group C total** | **33** |

**Suite total: 244/244 green** (was 243 — +1 from `f6669da` models fix).

### ADR-001 updated — `fa35622`

`docs/adr/ADR-001-daemon-mode.md` — Decision section rewritten from "Recommended approach" to "What was shipped":
- Records flat-file JSON queue design (not queue.txt)
- Records Telegram-in-drainer pattern (not a separate bot process)
- Open Questions table: all 5 resolved
- Pushed to main: `fa35622`

### SPEC-OutreachForge-v1.md created — `569e8ac`

`docs/specs/SPEC-OutreachForge-v1.md` (new directory `docs/specs/`)
- Problem: zero paying customers through Day 161 — blocker is outreach, not product or payment
- Scope: accept supplied leads, draft personalised first-touch, human-approval gate, Supabase tracking, follow-up drafts
- Architecture: `OutreachForgeAgent(ForgeAgent)` in `agents/outreach.py`, new `outreach_leads` Supabase table
- Open Question 2 (approval/notification channel) **UNRESOLVED** — Telegram blocked in India June 16–22 (NEET exam-fraud order, Section 69A IT Act). Lifts June 22; message-editing restriction until June 30. Do not build notification piece until decided.
- Everything else in spec is buildable now.
- Pushed to main: `569e8ac`

### Daemon Mode — live

- `ForgeOS_Daemon_Drain` Task Scheduler job confirmed running every 15 minutes
- Manual drainer run verified: Telegram gracefully skipped (no creds), queue empty, exit 0
- Drainer log at `logs/drainer.log`

---

## Day 159 — Completed (2026-06-17)

### ADR-001 Daemon Mode — IMPLEMENTED (`86cc519`)

**Status:** ADR-001 updated to Accepted.

#### 1 — FORGEOS_AUTO_DEPLOY guard (`agents/deploy.py`)
- Guard at top of `DeployAgent._execute` — checks `os.environ.get("FORGEOS_AUTO_DEPLOY", "0")`
- When NOT set (default): skips GitHub/Render/Vercel/Sentry/UptimeRobot entirely, writes a `DEPLOYMENT.md` "deploy skipped" notice, returns `skipped=[...]` result — pipeline continues normally
- When set to `"1"`: proceeds with full deploy logic unchanged
- One env var = one mechanism = one place to control unattended deploy. No separate gate class.
- TELEGRAM status: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` still absent from `~/.bashrc` — **flagged: pending configuration before Telegram trigger works**.

#### 2 — BuildQueue (`daemon/queue.py`)
- Flat-file FIFO: `builds/queue/pending/<timestamp>_<uuid>.json` → `builds/queue/archive/` on completion
- Job IDs use `%Y%m%dT%H%M%S_%f` (microseconds) so alphabetical sort == chronological order even within the same second
- `enqueue(idea, source)` → `pop_next()` → `archive(job, status, error)` lifecycle
- `builds/` is gitignored — queue is runtime state, never committed

#### 3 — Drainer (`daemon/drainer.py`)
- Single-invocation pattern: check Telegram → drain one job → exit
- `_tg_poll(queue)`: calls `getUpdates` with offset tracking (`daemon/state/telegram_offset.txt`); no-ops silently without `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`; any text message from the configured chat is enqueued as a build idea
- `drain_once(queue)`: pops oldest job, runs `HermesOrchestrator(idea=...).run()`, archives as success or failed+error; returns True/False
- `main()`: polls Telegram, logs queue depth, drains one job, `sys.exit(1)` on build failure so Task Scheduler sees a non-zero exit

#### 4 — Ollama TODO (`llm/ollama.py`)
- Comment at `url = f"{self.api_base.rstrip('/')}/api/chat"` marks this as the `localhost:11434` call site for the future direct Claude API swap
- Task logged as `builds/queue/pending/20260617T000000_ollama-api-swap.json` (runtime, not committed)

#### Windows Task Scheduler — NOT registered (by design)
Padmaja reviews and runs the following command herself:

```
schtasks /create /tn "ForgeOS Drainer" /tr "wsl.exe -d Ubuntu-22.04 -e bash -lc \"cd /home/padmaja/forge/forgeos && PYTHONPATH=. python3 -m daemon.drainer >> /home/padmaja/forge/forgeos/logs/drainer.log 2>&1\"" /sc HOURLY /mo 1 /ru SYSTEM /f
```

Or for on-demand / manual trigger only (no schedule):
```
schtasks /create /tn "ForgeOS Drainer" /tr "wsl.exe -d Ubuntu-22.04 -e bash -lc \"cd /home/padmaja/forge/forgeos && PYTHONPATH=. python3 -m daemon.drainer >> /home/padmaja/forge/forgeos/logs/drainer.log 2>&1\"" /sc ONSTART /ru SYSTEM /f
```

To add an idea to the queue and trigger manually:
```bash
# In WSL2:
cd /home/padmaja/forge/forgeos
PYTHONPATH=. python3 -c "from daemon.queue import BuildQueue; BuildQueue().enqueue('Build a habit tracker SaaS')"
PYTHONPATH=. python3 -m daemon.drainer
```

#### Tests
- `tests/test_deploy_guard.py` — 9 tests: guard-off skips all external calls, DEPLOYMENT.md always written, guard-on proceeds to deploy logic
- `tests/test_queue.py` — 24 tests: enqueue/pop/archive lifecycle, FIFO ordering, edge cases (empty, corrupted file, error truncation)
- `tests/test_drainer.py` — 16 tests: drain_once success/fail/empty, Telegram poll with/without creds, chat_id filter, offset advance, network failure
- **Test suite: 243/243** (was 194 — +49 new)

---

## Day 158 — Completed (2026-06-16)

### Daemon Mode ADR — SHIPPED (`303fbaa`)
- `docs/adr/ADR-001-daemon-mode.md` — decision record, status: Proposed (pending Padmaja review)
- **Environment facts captured** (verified by running commands):
  - `claude --version` = 2.1.146 (Windows binary, NOT in WSL2 PATH)
  - No `--schedule` or `--channels` flag in Claude Code CLI — `/schedule` is a cloud Routine *skill*, not a flag
  - `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` absent from `~/.bashrc` — TelegramNotifier silently no-ops on every build today
- **Options evaluated:** Claude Code Routines (deferred — Ollama is local-only, cloud can't reach localhost:11434), bare crontab in WSL2 (non-starter — WSL2 shuts down when terminal closes), systemd timer in WSL2 (inadvisable on a laptop), Windows Task Scheduler → wsl.exe (recommended near-term), Telegram-triggered builds (correct long-term architecture)
- **Gate analysis:** existing gate=True/False split is sound for unattended runs; **DeployAgent (gate=False) is the only exception** — needs `FORGEOS_AUTO_DEPLOY` env guard before any unattended build can safely proceed (creates real GitHub/Railway/Vercel resources)
- **Failure gaps identified:** Telegram not configured (silent failures), no build timeout (hung Ollama blocks indefinitely), no dead-letter log, no per-run spend cap
- **5 open questions** for Padmaja in the ADR before implementation starts
- No code changes in this task — decision record only

### Repo Hygiene — worktree-dark-manifesto deleted
- Branch tip `ce37aa8` confirmed as direct ancestor of main (`git merge-base --is-ancestor` exit 0) — commit was IN main's linear history, not just superseded
- WaterCursor.tsx byte-identical on both branches; zero unmerged content
- Remote `origin/worktree-dark-manifesto`: deleted ✓
- Local branch `worktree-dark-manifesto`: deleted ✓
- Git worktree registry: clean — only `main` + `act-ii-portal` remain ✓
- Physical dirs (`.claude/worktrees/dark-manifesto`, `.git/worktrees/dark-manifesto`): removed manually via Explorer (Windows permission block on `git worktree remove --force`)
- One discarded loose change in the worktree: `settings.local.json` adding `"Bash(vercel --version)"` — uncommitted, no loss

### LaunchAgent + FalClient — SHIPPED (`c79a20a`)
- `agents/launch.py`: ForgeAgent stage 20, `gate=False`, after DeployAgent
  - Single LLM call → three LAUNCH.md sections: PH listing draft, outreach seed table, launch thread (Xena voice)
  - Reads `context.metadata["pm_output"]["icp"]` for richer prospect seeding
  - Writes to `<workdir>/LAUNCH.md` AND `project/LAUNCH.md` (mirrors DeployAgent pattern)
  - Sets `launch_draft_ready=True` + `launch_needs_review=True` in metadata
  - Soft Telegram notify via `TelegramNotifier` (best-effort, never raises)
  - `capabilities=["LAUNCH.md"]`, `requires=[idea, project_id, spec, frontend_url, backend_url, repo_url]`, `budget_usd=0.0`
- `tools/fal_client.py`: provider-agnostic stub (Pika + Higgsfield via Fal.ai)
  - Methods: `build_a_brand()`, `app_screens()`, `product_sizzle()` — `founder_video` intentionally excluded
  - `is_ready()` returns False without `FAL_API_KEY` — all `generate()` calls raise `NotImplementedError`
  - `FAL_VIDEO_PROVIDER` env var selects provider (default: pika)
  - CLI: `python3 tools/fal_client.py generate --type build_a_brand --prompt '...'`
- `agents/__init__.py`: `LaunchAgent` added to `_LAZY` + `__all__`
- `agents/hermes.py`: launch stage wired after deploy in `_build_pipeline()`
- `tests/test_launch_agent.py`: 23 tests (attrs, render_launch_md, run with mocked LLM, FalClient stub)
- Test suite: **194/194** (was 171 — +23 new)
- **FalClient activation checklist** (when ready):
  1. Sign up at fal.ai → generate API key
  2. `export FAL_API_KEY=...` in WSL2 `~/.bashrc`
  3. Optionally `export FAL_VIDEO_PROVIDER=higgsfield` to switch provider
  4. Replace `raise NotImplementedError` body in `FalClient.generate()` with real fal-client queue submit + poll
  5. Verify model slugs in `_MODEL_MAP` against fal.ai/models

### Pika / Higgsfield — Investigation Complete: NOT STARTED
- `.mcp.json`: does not exist anywhere in repo. MCP config is `.claude/settings.json` — 3 servers: `supabase`, `context7`, `playwright`. No Pika, no Higgsfield entry.
- `agents/pika_launch.py`: does not exist. No `pika*.py`, no `higgsfield*.py` in agents dir.
- `orchestrator.py` / `hermes.py`: zero matches for `pika`, `higgsfield`, `LAUNCH_STAGES`, `build_a_brand`, `app_screens`, `product_sizzle`, `founder_video`.
- Whole-repo grep: zero matches for any of those terms across the entire codebase.
- The "May 2026 planning doc" was conversation-only — never committed to repo. Neither integration has any code, config, or reference. Clean-slate choice for both Pika and Higgsfield — no partially-wired code to navigate around.
- **Gated on**: Padmaja confirming account status / cost for whichever video provider she chooses before implementation begins.

---

## Day 157 — Continued (2026-06-15)

### Migrations
- MissionOrchestrator → ForgeAgent (`9b8a777`) — `capabilities=["VALIDATION_CONTRACT.json"]`, `requires=["idea","tasks"]`, `budget_usd=0.0`
- MissionWorkerLoop → ForgeAgent (`9b8a777`) — `capabilities=[]` (files written by MissionWorker helper, not the loop itself; key nuance for agent-organizer routing), `requires=["tasks"]`, `budget_usd=0.0`; filesystem dep on ScaffoldAgent's `project/` dir is documented in-class comment
- MissionValidator → ForgeAgent (`9b8a777`) — `capabilities=[]`, `requires=["idea"]` (`validation_contract` is a metadata key with self-healing fallback), `budget_usd=0.0`
- Shared import: `from .base import BaseAgent` → `from forge_sdk.agent import ForgeAgent` in `agents/mission.py`

### Test Fixes
- voice_agent asyncio harness — replaced `asyncio.get_event_loop().run_until_complete(coro)` with `asyncio.run(coro)` in `TestSilentMode._run`, `TestFallbackOnError._run`, and `test_speak_never_raises` direct call (`9d61e71`)
- Result: 171/171 — fully green (was 166/171)

### VoiceAgent — ElevenLabs swap + revert (`d00e531` → `e46f947`)
- ElevenLabs was wired in `d00e531`; reverted in `e46f947` — blocked by 402 (free-tier library voices require paid plan)
- Active default: edge-tts (`_tts_and_play` via `edge_tts.Communicate`) — free, no API key, smoke-tested: 29.2 KB MP3 written
- ElevenLabs code **preserved** as `_tts_elevenlabs()` — inactive method, documented with activation instructions
- `ELEVENLABS_API_KEY` remains in `.env.example` for when subscription is upgraded
- **voice_id follow-up (future session)**: when ElevenLabs reactivated, `_DEFAULT_VOICE = "en-GB-RyanNeural"` must be replaced with a valid ElevenLabs library voice ID from paid library

### Doppler — not installed on this machine
- Confirmed: Doppler CLI absent from WSL2 and Windows (no binary, no PATH entry, no shell config reference)
- Actual practice: secrets stored in WSL2 `~/.bashrc` (`export ELEVENLABS_API_KEY=...` at line 153)
- Documented convention (CLAUDE.md references Doppler/Render env) vs actual practice (`~/.bashrc`) — divergence, backlog
- Affects: `ELEVENLABS_API_KEY` (now in `~/.bashrc`), `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` (pending, needed for HermesOrchestrator Telegram notifications)
- Fix path when relevant: either install Doppler CLI in WSL2 (`brew install dopplerhq/cli/doppler` or `.deb`) and migrate secrets, or document `~/.bashrc` as the intentional convention

---

## Day 157 — Completed (2026-06-15)

### Migrations
- GameAgent → ForgeAgent (`a638c80`)
- DeployAgent → ForgeAgent (`e9d891d`)
- GStackGate base → ForgeAgent (`63117e0`) — 10 gate subclasses inherit transitively
- Per-gate `requires` for all 10 GStackGate subclasses (`fe2eaab`) — GStackGate migration fully complete

### Repo Hygiene
- `portal-v3` — deleted local + remote (confirmed fast-forward merged to main, Day 155)
- `act-ii-portal` — pushed to `origin/act-ii-portal` (local backup preserved; 2 commits ahead of dark-manifesto; unmerged, decision pending)
- `web/.next/` — verified already gitignored (line 13) and never tracked; no action needed
- `worktree-dark-manifesto`'s only unmerged content (WaterCursor.tsx) superseded by main's Lighthouse-99-optimized version — flagged for deletion next hygiene pass

### Day-N Formula — RESOLVED (closed permanently)
HUD formula confirmed correct: `Math.floor((Date.now() - new Date('2026-01-10').getTime()) / 86_400_000) + 1`
Source: `web/components/portal/S01_Hero.tsx` (epoch set in `0c46cae`).
Gives DAY 157 on 2026-06-15 — matches STATE.md exactly. No discrepancy. Issue closed.

### LaunchAgent SPEC.md (`89c8fae`)
- Drafted `agents/SPEC_LaunchAgent.md` — spec only, no implementation code
- Stage 20, `gate=False`, after DeployAgent
- Produces `LAUNCH.md` with: Product Hunt listing draft, outreach seed list (5-10 ICP entries), launch announcement thread
- `requires`: idea, project_id, spec, frontend_url, backend_url, repo_url
- `capabilities`: ["LAUNCH.md"]
- `budget_usd = 0.0` — late-pipeline, all spend incurred before stage 20
- Human-in-loop: all content requires Padmaja's approval before any posting/submitting
- Non-goals: does NOT post, does NOT submit to PH (gated on ≥10 paying customers), does NOT call OutreachQueue.add() automatically
- 5 open questions pending Padmaja review (non-blocking, not on critical path)

### Distribution Tooling Audit (`agents/distribution/`)
**ProspectAgent** (`prospect_agent.py`):
- CLI: `--handle / --platform / --context` — one prospect per invocation, no batch/file mode
- Runnable with `ANTHROPIC_API_KEY` set (env or `.env` fallback); no Doppler; no broken imports

**OutreachQueue** (`outreach_queue.py`):
- JSONL schema: `{handle, platform, status, draft_dm, prospect_summary, created_at, sent_at}`
- `status` cycles: `pending → sent | skip`; `replied` exists in stats but must be set manually
- `queue.jsonl` currently empty

### GStackGate + 10 Gates — Classification Complete (read-only)

**GStackGate** (`agents/gstack.py:39`) — abstract base, extends `BaseAgent`. Provides `_execute` runner
(calls `_evaluate`, appends to `context.metadata["gates"]`, raises `RuntimeError` on blocking fail)
and `_gate_call` (wraps `llm_complete`). All 11 classes already in `agents/__init__._LAZY`.

| # | Gate class | hermes.py stage | `gate=` | Phase | Current base | What it does | Classification | Recommendation |
|---|-----------|----------------|---------|-------|--------------|--------------|----------------|----------------|
| – | **GStackGate** | (base class) | – | gate | `BaseAgent` | Abstract runner: `_execute` → `_evaluate`, appends to metadata["gates"], raises on blocking fail | Pipeline base | **Migrate GStackGate → ForgeAgent; all 10 gates inherit** |
| 1 | **OfficeHoursGate** | `office_hours` (stage 1) | `True` | planning | GStackGate→BaseAgent | LLM: evaluates idea viability — market demand, monetization, complexity, risk, moat | Pipeline stage | migrate (transitively via GStackGate base) |
| 2 | **CEOReviewGate** | `ceo_review` (stage 2) | `True` | planning | GStackGate→BaseAgent | LLM: reviews SPEC from investor lens — revenue model, ICP, scope, missing features | Pipeline stage | migrate (transitively) |
| 3 | **EngReviewGate** | `eng_review` (stage 4) | `True` | design | GStackGate→BaseAgent | LLM: reviews ARCH from staff-engineer lens — stack, data model, API design, gaps | Pipeline stage | migrate (transitively) |
| 4 | **DesignShotgunGate** | `design_shotgun` (stage 5) | `False` | design | GStackGate→BaseAgent | LLM: rapid-fire design verdicts (auth, db, frontend, payments, deploy); `blocking=False` — advisory only | Pipeline stage | migrate (transitively) |
| 5 | **ReviewGate** | `review` (stage 10) | `True` | review | GStackGate→BaseAgent | LLM: staff code review — completeness, quality, TODOs, security, production readiness | Pipeline stage | migrate (transitively) |
| 6 | **AdversarialGate** | `adversarial` (stage 11) | `True` | review | GStackGate→BaseAgent | LLM: attacker-mode review — SQLi, auth bypass, IDOR, rate limiting, hardcoded secrets, billing logic | Pipeline stage | migrate (transitively) |
| 7 | **ScoreGate** | `score` (stage 12) | `True` | review | GStackGate→BaseAgent | LLM: final quality score on generated codebase; `min_score=7.0` — highest bar of the review tier | Pipeline stage | migrate (transitively) |
| 8 | **CSOGate** | `cso` (stage 14) | `True` | security | GStackGate→BaseAgent | LLM: CSO-level review — JWT, RLS, input validation, secrets, deps, GDPR; reads SECURITY.md artifact | Pipeline stage | migrate (transitively) |
| 9 | **QAGate** | `qa` (stage 15) | `True` | qa | GStackGate→BaseAgent | LLM: validates against MissionValidator's `validation_contract.assertions`; soft-passes if no contract found | Pipeline stage | migrate (transitively) |
| 10 | **ShipGate** | `ship` (stage 17) | `True` | ship | GStackGate→BaseAgent | No LLM call — aggregates `context.metadata["gates"]`; fails if any prior gate failed or avg < 7.0 | Pipeline stage | migrate (transitively) |

**Key structural finding:** The 10 gate subclasses only override `_evaluate`, not `_execute`. Migrating GStackGate base alone (BaseAgent → ForgeAgent) propagates to all 10 subclasses. Each subclass still needs its own `capabilities`/`requires` added (they vary per gate). `capabilities = []` for all (gates write no files — they write to `context.metadata`).

**Flags for implementation:**
- **ShipGate `requires`**: its only input is `context.metadata["gates"]` — a non-standard field, not a top-level `ProjectContext` attribute. Flag this when writing per-subclass `requires`.
- **RuntimeError propagation** (elevated — see Next Session, Step 1): GStackGate's blocking-fail path raises `RuntimeError`. Verify `ForgeAgent.run()` propagates this unchanged BEFORE migrating. After migration, confirm a test covers gate FAILURE (not just pass) — 167/167 alone doesn't prove this path is covered.

---

## Day 155 — Completed (2026-06-13)

- 5 bugs fixed and committed (`a436601` → `f610cee`)
- portal-v3 merged to main, clean fast-forward
- Vercel production updated at forgeos-eight.vercel.app
- Twitter card metadata added (rich X previews now work)
- CTA placeholder text fixed on dark bg
- 7 orbital arcs now varied (rand fix)
- PRDSim cursor visible
- Agent reference corrected (removed "Nova" persona not shown in portal)

| Bug | File | Commit |
|-----|------|--------|
| PRDSim cursor invisible | S04_Maya.tsx | `a436601` |
| zenVerdict refs "Nova" not in portal | simulations.ts | `ae4c4d9` |
| Missing Twitter card metadata | layout.tsx | `786eb7f` |
| CTA placeholder color unset | S13_CTA.tsx | `dcce4c3` |
| `rand(0.9,0.9)` no-op — all loop arcs same | PortalScene.tsx | `8ef444a` |

---

## Current State

| Item | Value |
|------|-------|
| Live URL | forgeos-eight.vercel.app |
| ContractForge | contractforge.co.in |
| main branch | Day 174 commit pending (6 commits ahead of origin — push pending) |
| Test suite | 312 collected — 309 passing, 3 skipped (integration), 0 failing |
| MRR | ₹0 |

---

## Next Session Starts With

**Day 174 — complete.** Task 1 (ModelRouter v2 verification) CLOSED. GLM fallback now logs `_log.warning()` when API call fails. 312 tests (309 passing, 3 skipped). Push to origin still pending — 6 commits ahead. Next session open items:

1. **`git push origin main`** — run this first; 6 commits ahead of origin (5 from Day 173 + 1 Day 174 fix).
2. **GLM_API_KEY activation** — sign up at openrouter.ai, `export GLM_API_KEY='sk-or-v1-...'` in WSL2 `~/.bashrc`, `source ~/.bashrc`. Verify: `PYTHONPATH=. python3 -c "from llm.glm import GLMClient; c=GLMClient(); r=c.complete([{'role':'user','content':'ping'}]); print(r.content[:80])"`. Key was not set as of Day 174 close — all builds still fall back to Sonnet with a logged warning.
3. **WSL2 sync** — WSL2 copy at Day 161 (`1c9caab`). After `git push origin main` from Windows, run `git pull origin main` in WSL2 to sync.
4. **RepairLoop implementation** — `agents/repair.py` + `tests/test_repair_loop.py` + hermes.py stage wiring. Read `forge_sdk/specs/SPEC_RepairLoop.md` Open Question 1 first: does ScaffoldAgent always produce test files? Run a test build and inspect `project/` output before writing code.
5. **YC video script** — deadline July 27, 2026 (25 days). Draft not started.
6. **YC application draft** — `yc/application_draft.md` Version B exists, not committed. Review + commit before July 15.
7. **Revenue**: pick one outreach channel and send; all 4 LinkedIn messages and 3 CA emails are drafted, none sent.
8. **Discord webhook URL** — still needed for OutreachForge approval notifications.
9. **FalClient activation** — deferred until `FAL_API_KEY` exists.

---

## Key Invariants to Preserve

1. `ForgeAgent.run()` is the single point of GBrainLogger lifecycle (`start` → `finish`) — never call `logger.start/finish` from `_execute`
2. `agents/__init__.py` must keep `BaseAgent` as the only eager import — all subclasses in `_LAZY`
3. `gbrain-events.jsonl` is append-only during a build — never truncate or rewrite
4. `budget_usd = 0.0` means unlimited — use it for agents that run mid/late pipeline (no useful cap)
5. All ForgeOS `from` imports are absolute (`from models import X`, not `from .models import X`)
6. PMAgent and EvalAgent are NOT in `agents/__init__._LAZY` — they're imported directly in `hermes.py`
7. GStackGate's blocking-fail path raises `RuntimeError` inside `_execute` — but **ForgeAgent.run() catches it** (via `except Exception`) and returns `AgentResult(status=FAILED)`. Hermes halts the pipeline by checking `result.status == "failed" and is_gate` (hermes.py:332), not by receiving the RuntimeError. Both BaseAgent and ForgeAgent handle this identically. Test coverage: `tests/test_gstack.py::test_blocking_gate_failure_produces_failed_result`.

---

## Test Status

| Suite | Passing | Failing | Notes |
|-------|---------|---------|-------|
| `test_agents.py` | 4/4 | 0 | full pass |
| `test_architect_output.py` | 17/17 | 0 | full pass |
| `test_dataset_collector.py` | 19/19 | 0 | full pass |
| `test_deploy_guard.py` | 9/9 | 0 | new Day 159 — auto-deploy guard |
| `test_drainer.py` | 16/16 | 0 | new Day 159 — daemon drainer |
| `test_eval_agent.py` | 19/19 | 0 | full pass |
| `test_gstack.py` | 4/4 | 0 | gate-failure + pass + subclass + base-attr |
| `test_launch_agent.py` | 23/23 | 0 | LaunchAgent attrs, render, run (mocked LLM), FalClient stub |
| `test_legal_agent.py` | 13/13 | 0 | full pass |
| `test_orchestrator.py` | 4/4 | 0 | full pass |
| `test_model_router.py` | 23/23 | 0 | Day 174 +1: GLM call failure warning test (`TestCompleteGLMCallFailure`) |
| `test_outreach_agent.py` | 32/32 | 0 | Day 163: +MigrationNotRunError, +Discord webhook (3 tests) |
| `test_pm_agent.py` | 27/27 | 0 | full pass |
| `test_queue.py` | 24/24 | 0 | new Day 159 — build queue FIFO lifecycle |
| `test_scaffold_output.py` | 12/12 | 0 | full pass |
| `test_security_output.py` | 15/15 | 0 | full pass |
| `test_semgrep_gate.py` | 13/13 | 0 | new Day 173 — semgrep integration + CSOGate blocking |
| `test_tools.py` | 6/6 | 0 | full pass |
| `test_validator_output.py` | 7/7 | 0 | full pass |
| `test_voice_agent.py` | 18/18 | 0 | asyncio.run() replaces get_event_loop() — Python 3.14 compat (`9d61e71`) |
| `test_worker_output.py` | 6/6 | 0 | full pass |
| **TOTAL** | **312 collected — 309 passing, 3 skipped** | **0** | 3 skipped = integration/semgrep (need semgrep on PATH) |

---

## Agent Migration Status

| Agent | Base class | Migrated |
|-------|-----------|---------|
| ArchitectAgent | ForgeAgent | ✓ (2026-06-07) |
| PMAgent | ForgeAgent | ✓ (2026-06-07) |
| ScaffoldAgent | ForgeAgent | ✓ (2026-06-07) |
| DesignAgent | ForgeAgent | ✓ structure only — `_execute` raises NotImplementedError |
| MediaAgent | ForgeAgent | ✓ structure only — `_execute` raises NotImplementedError |
| CoderAgent | ForgeAgent | ✓ (2026-06-08) |
| SecurityAgent | ForgeAgent | ✓ (2026-06-08) |
| EvalAgent | ForgeAgent | ✓ (2026-06-08) |
| DeployAgent | ForgeAgent | ✓ (2026-06-15) |
| GameAgent | ForgeAgent | ✓ (2026-06-15) |
| LaunchAgent | ForgeAgent | ✓ (2026-06-16) — `c79a20a`, stage 20, FalClient stub wired |
| GStackGate + 10 gates | ForgeAgent | ✓ (2026-06-15) — base `63117e0` + per-gate requires `fe2eaab` |
| MissionOrchestrator | ForgeAgent | ✓ (2026-06-15) |
| MissionWorkerLoop | ForgeAgent | ✓ (2026-06-15) — `capabilities=[]`: files written by MissionWorker helper, not the loop |
| MissionValidator | ForgeAgent | ✓ (2026-06-15) |
| OutreachForgeAgent | ForgeAgent | ✓ (2026-06-22) — `436c5d2`, standalone utility, `_execute` raises NotImplementedError |
| VoiceAgent | *none* (plain class) | N/A — standalone TTS utility, no pipeline base needed |

---

## HANDOFF — Day 173 (2026-07-01)

**Default agent behavior changed today. Read this before touching any LLM call.**

### Default LLM for all agent calls is now GLM-5.2, not qwen2.5-coder:7b

As of commit `6b248a9`, every ForgeOS pipeline stage — scaffold, worker, validator, pm_agent,
eval_agent, architect, security, cso_gate — routes to **GLM-5.2 (zhipuai/glm-z1-32b via OpenRouter)**
by default. qwen2.5-coder:7b no longer runs unless `FORGEOS_OFFLINE_MODE=true` is set.

This is not a config toggle. It is the new default routing path in `llm/router.py::_select_chain()`.

**Before running any build**, confirm this env var is set:
```bash
echo $GLM_API_KEY   # must print sk-or-v1-... (OpenRouter key)
```
If it's blank, the router falls back to `claude-sonnet-4-6` (Tier 2), which costs ~6× more.
To get a key: sign up at openrouter.ai → Dashboard → API Keys. Free tier is available.
Add to `~/.bashrc`:
```bash
export GLM_API_KEY="sk-or-v1-..."
```
**GLM_API_KEY was NOT set as of Day 173 close.** All builds until it is set will silently use Sonnet.

### Semgrep gate is live — but needs to be installed

SecurityAgent now runs `semgrep --config=auto --json` against every generated project.
CSOGate hard-blocks on any ERROR-severity finding, independent of LLM judgment.

`semgrep` is now declared in `pyproject.toml` (`dev` and `all` extras, `>=1.50`).

Install in WSL2 (where builds actually run):
```bash
pip install semgrep --break-system-packages
# or in a venv:
pip install -e ".[all]"
```

If semgrep is not installed, `_run_semgrep()` returns `[]` silently — **the gate does not block,
and there are no findings to merge into SECURITY.md.** This is indistinguishable from "scan ran
clean." Always verify semgrep is on PATH in the WSL2 environment where builds run.

### Fable-5 frontier tier — off by default

`FORGEOS_FRONTIER_TIER` defaults to `False` in `config.py`. When set to `true`, architect and
cso_gate stages route to `claude-fable-5` instead of GLM-5.2. The model string is the literal
`"claude-fable-5"` (constant `_FABLE5` in `llm/router.py`). Costs ~$10/$50 MTok.

Do not set `FORGEOS_FRONTIER_TIER=true` in CI or unattended builds — it bypasses the cost budget.

### Open blockers for next session

| Blocker | Action |
|---------|--------|
| `GLM_API_KEY` not set | Sign up openrouter.ai, add key to WSL2 `~/.bashrc` |
| semgrep not verified in WSL2 | `pip install semgrep --break-system-packages` in WSL2, then `semgrep --version` |
| Live GLM-5.2 call not verified | After setting key: `PYTHONPATH=. python3 -c "from llm.glm import GLMClient; c=GLMClient(); r=c.complete([{'role':'user','content':'ping'}]); print(r.content[:80])"` |
| RepairLoop not implemented | Spec at `forge_sdk/specs/SPEC_RepairLoop.md` — answer Open Q1 first |
