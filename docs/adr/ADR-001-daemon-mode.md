# ADR-001 — ForgeOS Daemon Mode: Unattended Pipeline Execution

**Status:** Proposed  
**Date:** 2026-06-16 (Day 158)  
**Author:** Padmaja Kotoky + Claude Sonnet 4.6  
**Relates to:** HermesOrchestrator (`agents/hermes.py`), TelegramNotifier, LaunchAgent

---

## Context

ForgeOS builds are currently triggered manually: a person opens a terminal, types
`PYTHONPATH=. python3 orchestrator.py --idea "..."`, and watches it run.
The original vision was for ForgeOS to run as a persistent factory — accept an idea,
build, deploy, and notify with no one watching.

This ADR examines whether and how to achieve that, given the specific
constraints of this machine (WSL2 on Windows 11 laptop, local Ollama on port 11434).

### Current environment (verified 2026-06-16)

| Fact | Value |
|------|-------|
| Claude Code version | 2.1.146 (Windows binary, not in WSL2 PATH) |
| Primary LLM | Ollama `qwen2.5-coder:7b` on `localhost:11434` |
| Fallback LLM | Claude `claude-haiku-4-5` via `ANTHROPIC_API_KEY` |
| Notification channel | `TelegramNotifier` in `agents/hermes.py` — **not configured**: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` absent from `~/.bashrc` |
| Secrets store | `~/.bashrc` exports (no Doppler, no 1Password CLI) |
| WSL2 distro | Ubuntu-22.04 |

### What "daemon mode" means here

Three distinct interpretations need to be separated:

1. **Persistent process** — ForgeOS runs continuously, polling a queue, and starts builds automatically.
2. **Scheduled trigger** — A scheduler fires `orchestrator.py` on a cron-like schedule with a pre-specified idea.
3. **Remote trigger** — An external event (a Telegram message, a webhook) starts a build on demand.

Interpretation 3 is the most useful for a solo founder — you decide what to build, you trigger it remotely, you get notified when it's done. Interpretation 2 (fixed schedule) only makes sense if there's a known queue of ideas to drain. Interpretation 1 (persistent daemon) is premature.

---

## Decision Drivers

1. **Ollama is local** — anything that requires cloud execution cannot reach `localhost:11434`. This is the hard constraint that shapes everything below.
2. **Laptop goes to sleep** — a process that dies when the lid closes is not a reliable daemon.
3. **Unattended deploys are high-risk** — DeployAgent creates GitHub repos, Railway services, and Vercel projects. Each is a real external side effect that costs money and can't be trivially undone.
4. **Telegram is the intended notification channel** — but it is not yet configured. Any daemon mode is meaningless without it.
5. **The pipeline already has gates** — blocking stages (`gate=True`) exist to prevent bad outputs from reaching deploy. Their behaviour in unattended mode matters.

---

## Options

### Option A — Claude Code Routines (`/schedule` skill)

Claude Code's `/schedule` skill creates a cloud-hosted agent that runs on a cron schedule, using the Anthropic API. The agent receives a prompt, runs in Anthropic's cloud, and executes tool calls remotely.

**Why this does not work for ForgeOS today:**

- The cloud agent cannot reach `localhost:11434`. Ollama — the primary LLM, providing ~$0 build cost — is simply unreachable from Anthropic's infrastructure.
- Every LLM call would fall through to `claude-haiku-4-5`. A full Hermes pipeline run makes dozens of LLM calls across 20 stages. At haiku pricing, an unattended nightly build could cost $1–3 per run, every day, regardless of whether the output was useful.
- The agent also cannot write to the local `builds/` directory or push from the local git identity.
- `claude --help` (v2.1.146) has no `--schedule` flag — Routines are only accessible via the `/schedule` skill inside an interactive or `-p` session on a machine with API access. They are not a standalone scheduler.

**Verdict:** Deferred. Becomes viable if/when Ollama is replaced with a cloud LLM and `builds/` moves to cloud storage. Not viable today.

---

### Option B — DIY headless: bare `crontab` in WSL2

```bash
# This does NOT work reliably
0 2 * * * cd /home/padmaja/forge/forgeos && PYTHONPATH=. python3 orchestrator.py --idea "..."
```

WSL2 instances are not persistent services. When the last Windows Terminal tab accessing a distro closes, WSL2 shuts the instance down within seconds (controlled by `shutdownTimeout` in `.wslconfig`, default 8 seconds). `cron` is an init-level process that only runs while the WSL2 instance is alive. A cron job set for 2 AM will never fire if WSL2 shut down at midnight.

**Verdict:** Non-starter as written. Valid only if WSL2 is kept alive 24/7 via systemd (see Option C).

---

### Option C — systemd in WSL2 + a timer unit

Ubuntu 22.04 in WSL2 supports systemd when enabled in `/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

With systemd active, a `.timer` unit can replace cron and fire reliably as long as the WSL2 instance stays running. However:

- The WSL2 instance still shuts down when Windows decides to terminate it (lid close, idle timeout). The `shutdownTimeout` in `~/.wslconfig` can be set to `0` to prevent automatic shutdown, but this keeps WSL2 running 24/7, consuming RAM and preventing the GPU from sleeping.
- On a laptop with 16GB RAM, a persistent WSL2 instance is a real cost: the Ubuntu kernel plus Ollama loaded keeps ~3–4 GB reserved.
- systemd-level service management adds meaningful operational overhead for a solo founder.

**Verdict:** Viable for a desktop/workstation. Inadvisable for a laptop where lid-close is normal. Not recommended for this machine.

---

### Option D — Windows Task Scheduler → `wsl.exe` (RECOMMENDED for triggers)

Windows Task Scheduler can invoke `wsl.exe` regardless of whether the WSL2 instance is currently running. Windows will start the distro, run the command, and the distro will remain alive until the command finishes.

```
Trigger: On demand (or daily at a fixed time)
Action:  wsl.exe -d Ubuntu-22.04 -e bash -lc
           "cd /home/padmaja/forge/forgeos && PYTHONPATH=. python3 orchestrator.py --idea '%IDEA%'"
```

Advantages:
- Works even when WSL2 is not running — Windows starts it.
- Laptop can sleep between triggers; Windows Task Scheduler survives sleep/wake.
- No systemd required; no persistent daemon consuming RAM.
- The Ollama server needs to be started within the run (or kept alive separately), but a pre-trigger action or a wrapper script can handle this.

Limitations:
- The "idea" must be known in advance and baked into the scheduled task, or read from a queue file (`builds/queue.txt`).
- Not a real-time trigger — Task Scheduler granularity is ~1 minute. For on-demand remote builds, it's the wrong tool.

---

### Option E — Telegram-triggered builds (RECOMMENDED for remote trigger)

`agents/hermes.py` already has `HermesGateway`, a thin wrapper around a `hermes` CLI binary, and the `TelegramNotifier` class. The docstring of `HermesOrchestrator` explicitly names "Telegram-triggered build entrypoint" as a target.

The intended architecture:
```
Padmaja → sends Telegram message ("build a habit tracker SaaS")
         → Telegram Bot receives message
         → calls wsl.exe to invoke orchestrator.py --idea "..."
         → ForgeOS builds
         → TelegramNotifier sends status updates + final LAUNCH.md notification
```

This is the right model for a solo founder working from a phone: you decide what to build, you type it in Telegram, you get a notification when it's done (or when a gate blocks it).

**Why this is blocked today:**
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are absent from `~/.bashrc` (confirmed via grep). `TelegramNotifier` silently no-ops on every build.
- A Telegram Bot requires a webhook server or a polling process — neither exists yet in the codebase.
- `HermesGateway` wraps a `hermes` CLI binary; that binary is not installed.

**Verdict:** The correct long-term architecture. Currently missing: Telegram credentials, a bot polling process, and the webhook-to-orchestrator bridge. These are prerequisites, not part of this ADR's scope.

---

## Gate Analysis for Unattended Runs

The current Hermes pipeline has 11 blocking gates (`gate=True`) and 9 non-blocking stages (`gate=False`).

### Blocking gates — behaviour in unattended mode

| Stage | Gate class | Risk unattended | Recommendation |
|-------|-----------|-----------------|----------------|
| pm_agent | PMAgent | Low — blocks `dont_build` ideas early | Keep `gate=True` |
| office_hours | OfficeHoursGate | Low — screens idea viability | Keep `gate=True` |
| ceo_review | CEOReviewGate | Low — validates revenue model | Keep `gate=True` |
| eng_review | EngReviewGate | Low — validates architecture | Keep `gate=True` |
| review | ReviewGate | Low — code quality floor | Keep `gate=True` |
| adversarial | AdversarialGate | Low — security floor | Keep `gate=True` |
| score | ScoreGate | Low — min_score=7.0 enforced | Keep `gate=True` |
| cso | CSOGate | Low — CSO security sign-off | Keep `gate=True` |
| qa | QAGate | Low — validates against contract | Keep `gate=True` |
| ship | ShipGate | Low — aggregates all prior gates | Keep `gate=True` |
| eval_agent | EvalAgent | Low — blocks if score < 80 | Keep `gate=True` |

The gate split is sound for unattended runs. If any blocking gate fails, the pipeline halts and (once Telegram is configured) notifies. No bad output reaches deploy.

### Non-blocking stages — one exception matters

| Stage | Risk unattended | Recommendation |
|-------|-----------------|----------------|
| architect | Low | Fine |
| design_shotgun | Low — advisory only | Fine |
| mission_plan, scaffold, game, mission_work | Low | Fine |
| security | Low | Fine |
| validator | Low | Fine |
| **deploy** | **HIGH** | **Needs a gate or an opt-in flag** |
| launch | Low — writes files + Telegram only | Fine once Telegram configured |

**DeployAgent is the problem.** It creates GitHub repos, Railway/Render services, and Vercel deployments — all real external resources with real costs — and currently runs unconditionally as `gate=False`. In an unattended scenario where the entire pipeline ran cleanly to this point, deploy is the right next step. But there is no human in the loop to review the generated code before it goes live.

Two options:
1. **Add an `FORGEOS_AUTO_DEPLOY` env flag** — `DeployAgent._execute` checks `os.environ.get("FORGEOS_AUTO_DEPLOY", "0")` and skips if not set to `"1"`. Unattended builds produce everything up to deploy; Padmaja reviews and deploys manually with the flag set.
2. **Add a soft deploy gate** — a new `DeployApprovalGate` that checks `context.metadata["deploy_approved"]`, which can only be set via a Telegram approval reply. This is the proper architecture but requires the Telegram bot to be running.

Option 1 is a one-line change and is safe to ship immediately. Option 2 is the right end state.

---

## Failure Handling

### What exists today

- **Retry**: `hermes.py` retries non-gate stages up to 3 times with exponential backoff; gates get 1 attempt.
- **Alert**: `TelegramNotifier.build_failed()` fires on crash — but Telegram is not configured, so this is silent.
- **Halt**: blocking gates raise `RuntimeError`, which `_run_stage` catches, notifies Telegram, and re-raises to stop the pipeline.

### What is missing for reliable unattended operation

| Gap | Impact | Fix |
|-----|--------|-----|
| Telegram not configured | All failure notifications are silent | Add `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` to `~/.bashrc` |
| No build timeout | A hung Ollama call blocks indefinitely | Add `--timeout` to `llm/ollama.py` requests (already uses `requests`; set `timeout=120`) |
| No dead-letter log | Failed builds leave no aggregated trace | `builds/<id>/FAILED.md` written on pipeline abort (new, minor) |
| No spend cap in headless mode | Claude API spend unbounded per run | Pass `--max-budget-usd` if invoking via `claude -p`; or enforce in LLM router |

---

## Decision

**Recommended approach, in priority order:**

### Step 0 — Prerequisites (blocking; nothing else works without these)

1. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `~/.bashrc`. TelegramNotifier is already wired in hermes.py — it just needs credentials. This unblocks all existing notification paths.
2. Add `FORGEOS_AUTO_DEPLOY=0` guard in `DeployAgent._execute` so unattended builds can run safely without creating external resources.

### Step 1 — On-demand trigger via Windows Task Scheduler (near-term)

Implement a thin Windows Task Scheduler job that:
1. Reads the next idea from `builds/queue.txt` (pop first line).
2. Invokes `wsl.exe -d Ubuntu-22.04 -e bash -lc "cd /home/padmaja/forge/forgeos && PYTHONPATH=. python3 orchestrator.py --idea '$IDEA'"`.
3. Telegram notifications arrive on completion/failure.

This is not a daemon. It is a reliable trigger that works across laptop sleep. Padmaja fills `builds/queue.txt` with ideas; the job drains them on her schedule.

### Step 2 — Telegram bot trigger (medium-term, after Telegram configured)

Implement a lightweight Telegram bot polling process (`agents/telegram_bot.py`) that:
- Listens for messages in the configured chat.
- On receiving an idea string, appends it to `builds/queue.txt` and/or invokes orchestrator directly.
- Reports build progress and gate blocks back to the chat.

This is the intended Telegram-triggered build architecture referenced in `HermesOrchestrator`'s docstring. It is the right long-term model.

### Step 3 — Claude Code Routines (deferred)

Revisit when: (a) Ollama is replaced with a cloud LLM, OR (b) a remote API server wrapping the ForgeOS pipeline is deployed and accessible to Anthropic's infrastructure. Not before.

---

## Consequences

**If this decision is followed:**
- Daemon mode becomes real in two steps: configure Telegram, then wire the queue-draining Task Scheduler job.
- The pipeline is never blocked from running unattended by WSL2 lifecycle issues.
- Deploy stays off by default in unattended mode until `FORGEOS_AUTO_DEPLOY=1` is explicitly set.
- Telegram bot trigger is the intended end state and can be built incrementally on top of Step 1.

**What this ADR deliberately does not decide:**
- The exact Telegram bot library or hosting approach for the polling process.
- Whether `builds/queue.txt` vs a Supabase table vs Telegram-inline is the right queue store.
- The `DeployApprovalGate` design (Step 0 Option 2 above) — deferred to a separate ADR once the bot is running.
- Any code changes. This is a decision record. Implementation starts only after Padmaja reviews and approves this recommendation.

---

## Open Questions for Padmaja

1. **Telegram bot setup**: Do you want to create a new bot via @BotFather now (a 2-minute task), or defer all of Step 0 to when you're ready to wire the full trigger flow?

2. **`FORGEOS_AUTO_DEPLOY` flag vs deploy gate**: The one-line env-var guard (Option 1 above) can ship immediately and safely. The approval gate (Option 2) requires the bot to be running first. Which do you want first?

3. **Queue file vs ad-hoc**: Do you prefer a `builds/queue.txt` queue that you fill in advance, or do you want builds to always be Telegram-triggered with no pre-queued ideas?

4. **WSL2 lifetime**: Are you willing to set `wsl2.shutdownTimeout=0` in `.wslconfig` to keep WSL2 alive continuously (saves process-startup latency on every build trigger), or do you prefer the on-demand start model (slower trigger, no background RAM cost)?

5. **Ollama server lifecycle**: Ollama must be running before any build that uses it. Should the Task Scheduler job start `ollama serve` as a pre-step, or will you keep Ollama running manually?
