# NightlyReasoningAgent — Specification

> Status: SPEC ONLY — no implementation. Review before any code is written.
> Spec date: 2026-08-02 (Day 195, per STATE.md HANDOFF cadence)
> Author: Padmaja Kotoky + Claude Sonnet 5
> Runs on: GitHub Actions cron — NOT local WSL2. This is the deliberate
> counterpart to [[SPEC_LocalCron_GBrainIndexing]], which is the local half
> of the same closed loop.

---

## 0. Discrepancies found during research — read this before the rest

The request named specific tables, a specific file, and a specific existing
workflow to match conventions with. I verified each against the actual repo
state rather than assume they exist. Three don't, as specified:

1. **`daily-agents.yml` does not exist.** `.github/workflows/` currently has
   only `ci.yml` (push/PR-triggered test runner, no cron). This spec
   therefore *proposes* a new workflow file, `nightly-reasoning-agent.yml`,
   modeled on `ci.yml`'s job structure (checkout → setup-python →
   `PYTHONPATH=.` install → run), since there's no existing cron-workflow
   convention in this repo to match yet.

2. **`agent_logs` is not the right table.** A table literally named
   `agent_logs` does exist in the live Supabase project, but per the
   as-built migration comment at
   `supabase/migrations/20260707000002_agent_logs_as_built_reference.sql`,
   it has an **incompatible schema** (`agent_name`, `run_at`, `status`,
   `summary`, `error_message`, `duration_ms`) and **no application code
   anywhere in the repo reads or writes it** — confirmed by the migration
   author's own grep note. The table that's actually live — written by the
   Python pipeline via service-role key, read by the founder dashboard — is
   `dashboard_events` (`supabase/migrations/20260707000000_app_foundations.sql`).
   This spec reads `dashboard_events`, not `agent_logs`. If you specifically
   want the old `agent_logs` table's data too, say so and I'll add it as a
   second read — right now nothing writes to it, so it would return empty.

3. **Lemon Squeezy and Resend raw events are not persisted anywhere queryable
   today.** `agents/scaffold.py` generates a `/api/billing/webhook` handler
   *per built product*, but that's scaffolded into each generated project's
   own backend — it is not wired to report back into the ForgeOS platform's
   own Supabase project. The only platform-level financial/engagement signal
   that exists today is `product_metrics` (`mrr_inr`, `signups`,
   `conversions`, snapshotted per `product_slug`), which is an aggregate, not
   raw webhook events. There is no Resend event table at all. **This is an
   open dependency, not something this spec can silently paper over** — see
   §2.3.

4. **`FORGE_BRAIN.md` does not exist**, and the existing `ForgeBrain` class
   (`forge_brain.py`) writes markdown notes to a *local* Obsidian vault path
   (`~/ObsidianVault/ForgeOS/wiki/patterns/*.md`, controlled by
   `RUNTIME.obsidian_vault`) — a path that does not exist on a GitHub Actions
   runner. A cron job running in Actions cannot write there. §5 proposes
   `FORGE_BRAIN.md` as a **new, separate, git-committed file** at repo root,
   distinct from the existing `forge_brain.py` → Obsidian pipeline. Whether
   these two knowledge stores should eventually merge is an open question
   (§7, OQ-1) — out of scope to resolve here.

None of this blocks writing the spec — it just means the spec targets the
tables and files that actually exist, and flags the two genuine gaps
(webhook persistence, Obsidian-vs-repo brain) as prerequisites or open
questions rather than inventing answers.

---

## 1. Purpose

NightlyReasoningAgent is the platform's own self-reflection step. Once a
day, independent of whether anyone's laptop is on, it reads the last 30 days
of everything ForgeOS and its generated products have done — agent runs,
product metrics, git activity — looks for patterns and anomalies a human
hasn't noticed yet, proposes rule updates, records them, and pings Discord
with a same-day-readable brief.

It must run on GitHub Actions specifically because reliability here depends
on not depending on a laptop being powered on — that constraint is the
entire reason this spec and [[SPEC_LocalCron_GBrainIndexing]] are split into
two documents instead of one.

---

## 2. Trigger Schedule

### 2.1 New workflow file: `.github/workflows/nightly-reasoning-agent.yml`

```yaml
name: Nightly Reasoning Agent

on:
  schedule:
    - cron: "30 0 * * *"   # 00:30 UTC daily
  workflow_dispatch: {}     # manual trigger for testing, matches ci.yml's
                             # philosophy of not hiding behind cron-only triggers

env:
  PYTHONPATH: .

jobs:
  reason:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install ForgeOS dependencies
        run: pip install -e ".[all,dev]"
      - name: Run nightly reasoning pass
        env:
          GLM_API_KEY: ${{ secrets.GLM_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: PYTHONPATH=. python3 -m agents.nightly_reasoning
      - name: Commit FORGE_BRAIN.md updates
        if: always()
        run: |
          git config user.name "forgeos-bot"
          git config user.email "bot@forgeos.local"
          git add FORGE_BRAIN.md
          git diff --staged --quiet || git commit -m "chore: nightly reasoning update ($(date -u +%Y-%m-%d))"
          git push
```

### 2.2 Why 00:30 UTC

Chosen to run after any late-evening India-timezone (IST = UTC+5:30) work
session has landed commits, so the git-activity read in §2.3 has that day's
work included, not a stale snapshot from the prior day.

### 2.3 What this trigger schedule assumes (open dependency, not resolved here)

The Lemon Squeezy/Resend gap from §0.3 means the "closed-loop artifact
corpus" as literally described in the request is currently: `dashboard_events`
+ `product_metrics` + git commits. Real per-transaction Lemon Squeezy/Resend
signal would need a webhook-receiver → Supabase table added first (a small,
separate piece of work — a `billing_events` or similar table, written to by
the platform's own backend, analogous to how each *generated* product already
has one). Recommend building that as a prerequisite, or explicitly scoping
v1 of NightlyReasoningAgent to `dashboard_events` + `product_metrics` +
git log and revisiting when there's real revenue to reason about.

---

## 3. Supabase Tables and Queries Read

All reads use the service-role key (`SUPABASE_SERVICE_ROLE_KEY`), same
pattern as `tools/supabase_admin.py` — read-only for this agent, it never
writes to these three tables.

### 3.1 `dashboard_events`

```sql
select agent, event_type, message, metadata, created_at
from dashboard_events
where created_at >= now() - interval '30 days'
order by created_at asc;
```

Gives every agent action (`info` / `action` / `gate` / `error`) across all
builds in the window — this is the primary anomaly-detection input (error
rate spikes, gate failure clusters, repeated agent names in error events).

### 3.2 `product_metrics`

```sql
select product_slug, mrr_inr, signups, conversions, recorded_at
from product_metrics
where recorded_at >= now() - interval '30 days'
order by product_slug, recorded_at asc;
```

Gives per-product MRR/signup/conversion trend lines over the window —
day-over-day deltas per `product_slug` are computed in Python after fetch,
not in SQL (small enough row count that this is simpler than a window-
function query, and keeps the SQL side dumb and auditable).

### 3.3 `workspaces`

```sql
select id, name, created_at
from workspaces;
```

Small lookup table (per §0's migration note, there is exactly one real
workspace today) — read once per run to resolve `product_slug` → workspace
context if/when multi-tenancy becomes real. Effectively a no-op today but
keeping the join point defined now avoids a schema surprise later.

### 3.4 Git commits (not Supabase — direct git read)

```bash
git log --since="30 days ago" --pretty=format:"%h|%ad|%s" --date=short
```

Run inside the Actions checkout, no external call needed. Commit subject
lines feed the "what changed" half of the reasoning prompt, correlated
against `dashboard_events` error clusters and `product_metrics` deltas from
the same window.

---

## 4. LLM Call Structure

Routed through the existing `llm.router.complete()` (`llm/router.py`) —
**not** a new client. This automatically gets GLM-5.2 as Tier 1 with Sonnet
fallback, cost ledger recording (if a `ProjectContext` is passed — see note
below), and the retry/streaming handling already built into `GLMClient`.

```python
from llm.router import complete as llm_complete

resp = llm_complete(
    user=reasoning_prompt,          # built from §3's fetched data, see below
    system_extra=NIGHTLY_REASONING_SYSTEM,
    task_complexity="hard",
    task_type="review",             # not "architecture"/"security" — stays
                                     # off the gated Fable-5 frontier tier;
                                     # this is a recurring low-stakes job,
                                     # not a one-shot high-stakes gate
    purpose="nightly_reasoning.analyze",
    stream=False,                   # unattended cron run, no terminal to stream to
    max_tokens=4000,
    temperature=0.3,                # slightly above the 0.2 pipeline default —
                                     # pattern-spotting benefits from a little
                                     # more variation than code generation does
)
```

Note: `llm_complete(context=...)` is how token/cost ledger entries get
recorded today (`context.record_tokens(...)` inside `complete()` in
`llm/router.py`), but that requires a live `ProjectContext`, which doesn't
exist outside a build pipeline run. NightlyReasoningAgent runs standalone,
so it will not get automatic cost-ledger recording unless a lightweight
adapter is built for it — flagged as **OQ-2** in §7, not resolved here.

### 4.1 System prompt (`NIGHTLY_REASONING_SYSTEM`)

```
You are the nightly reasoning pass for ForgeOS, an autonomous multi-agent
product factory. You review 30 days of agent activity, product metrics, and
git history to find patterns a human hasn't noticed yet — not to restate
what's already obvious in the raw data.

Output strict JSON matching this schema:
{
  "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "findings": [
    {
      "title": "short (3-8 words)",
      "category": "anomaly | trend | risk | opportunity",
      "evidence": "what in the data supports this — cite specific agent
                    names, event counts, or commit hashes",
      "confidence": "high | medium | low"
    }
  ],
  "proposed_rule_updates": [
    {
      "target": "gbrain/patterns/technical.json | CLAUDE.md | other",
      "proposal": "one sentence, concrete and actionable",
      "rationale": "why, grounded in evidence above"
    }
  ],
  "summary": "2-3 sentences, plain language, for a Discord brief"
}

Do not fabricate findings to fill the schema. An empty findings array on a
quiet week is a correct, honest output.
```

### 4.2 User prompt assembly

```python
reasoning_prompt = (
    f"DASHBOARD EVENTS (30d, {len(events)} rows):\n{json.dumps(events_summary)}\n\n"
    f"PRODUCT METRICS (30d, by product_slug):\n{json.dumps(metrics_summary)}\n\n"
    f"GIT COMMITS (30d, {len(commits)} commits):\n{commit_log_text}\n"
)
```

`events_summary` and `metrics_summary` are pre-aggregated in Python before
the prompt is built (event-type counts per agent, MRR/signup deltas per
product) rather than sending 30 days of raw rows verbatim — keeps the prompt
bounded regardless of how much activity accumulates, and matches the
RepairLoop spec's existing precedent of truncating/summarizing rather than
dumping raw data (`forge_sdk/specs/SPEC_RepairLoop.md` §5).

---

## 5. Output Schema — `FORGE_BRAIN.md`

New file, repo root, git-committed by the Actions workflow itself (§2.1's
final step). Not the same store as `gbrain/patterns/*.json` (those are
per-build-technical-pattern JSON, consumed by ArchitectAgent) or the
Obsidian vault (local, human-curated wiki). `FORGE_BRAIN.md` is specifically
the nightly agent's own append-only log — human-readable, git-diffable,
reviewable in a PR-like way even though it's pushed directly.

### 5.1 Format — append-only, newest entry on top

```markdown
# FORGE BRAIN — Nightly Reasoning Log

Append-only. Newest entry first. Each entry is one nightly run's output,
verbatim from the LLM's JSON response, rendered to markdown.

---

## 2026-08-02

**Summary:** <summary field>

### Findings

- **[anomaly] <title>** (confidence: high)
  <evidence>

### Proposed rule updates

- **Target:** `gbrain/patterns/technical.json`
  **Proposal:** <proposal>
  **Rationale:** <rationale>

---

## 2026-08-01
...
```

### 5.2 Proposed rule updates are proposals, not auto-applied

Nothing in this spec writes to `gbrain/patterns/technical.json` or
`CLAUDE.md` directly. `proposed_rule_updates` entries sit in
`FORGE_BRAIN.md` for a human to read and manually apply — same
human-in-the-loop posture as `agents/outreach.py`'s
`queue_for_approval`/nothing-auto-sends pattern. Auto-applying rule changes
from an unattended nightly LLM call is a materially different risk profile
and not something this spec proposes.

---

## 6. Discord Message Format

Reuses the exact embed pattern already live in
`agents/outreach.py::send_approval_notification` — same webhook env var
(`DISCORD_WEBHOOK_URL`), same `httpx.AsyncClient` + `resp.status_code == 204`
success check, same never-raises posture.

```python
payload = {
    "content": "🧠 **ForgeOS — Nightly Reasoning Brief**",
    "embeds": [{
        "title": f"{period_start} → {period_end}",
        "description": summary,          # from §4.1's "summary" field
        "fields": [
            {
                "name": f"Findings ({len(findings)})",
                "value": "\n".join(f"• {f['title']}" for f in findings[:5]) or "None this run.",
                "inline": False,
            },
            {
                "name": f"Proposed rule updates ({len(proposals)})",
                "value": "\n".join(f"• {p['target']}: {p['proposal']}" for p in proposals[:3]) or "None this run.",
                "inline": False,
            },
        ],
        "footer": {"text": "Full detail in FORGE_BRAIN.md"},
        "color": 5793266,   # distinct from outreach's orange (15105570) —
                             # blurple, to read as "system", not "action needed"
    }],
}
```

Discord embed field `value` has a 1024-char limit and embeds cap at 25
fields total — capping findings/proposals previews to 5/3 items with "full
detail in FORGE_BRAIN.md" keeps this safely under both limits regardless of
how large a given night's output is.

---

## 7. Failure / Retry Behavior

| Failure point | Behavior |
|---|---|
| Supabase read fails (any of §3.1–3.3) | Log error, abort run, **no** Discord message, **no** FORGE_BRAIN.md write. A partial-data reasoning pass is worse than a skipped one — same "don't silently pass" principle as RepairLoop §4's exhaustion behavior. Workflow step fails, GitHub Actions surfaces it as a red run — that failure itself is the alert (visible in the repo's Actions tab; optionally also wire a second, minimal Discord ping on workflow failure via `if: failure()`, not the main brief). |
| `llm_complete()` raises `LLMError` (both GLM and Sonnet fail — see `llm/router.py`'s chain) | Same as above: abort, no partial write. `llm_complete` already retries within each provider (`_retry` in `GLMClient`) and falls back GLM→Sonnet automatically — no additional retry logic needed at this layer, that would duplicate what the router already does. |
| LLM returns malformed JSON (doesn't match §4.1 schema) | One re-ask with the parse error appended to the prompt ("Your previous response was not valid JSON: `<error>`. Return only the JSON object, no prose."). If the retry also fails to parse, abort and log the raw response for manual inspection — do not guess at partial parsing. |
| Discord post fails (webhook down, rate limited) | Non-fatal. `FORGE_BRAIN.md` has already been committed by this point (commit happens before the Discord step in the workflow) — the brief lives in git either way. Log and continue; matches `send_approval_notification`'s existing never-raises contract. |
| `git push` fails (e.g., another commit landed between checkout and push) | Workflow step fails visibly. No silent loss — the LLM response is in the job log even if the commit didn't land, so nothing is unrecoverable. Do not force-push. Retry-on-next-scheduled-run is acceptable; this is not time-critical to the minute. |
| Cron doesn't fire at all (GitHub Actions scheduled-workflow delays, which are common under platform load) | Accepted risk — GitHub documents that `schedule` triggers are best-effort, not guaranteed-exact. `workflow_dispatch` in §2.1 exists specifically so a missed night can be manually re-run. No self-healing "did I run today" check is proposed here — would add complexity disproportionate to the actual stakes of a delayed reasoning brief. |

---

## 8. Estimated GLM-5.2 Token Cost Per Run

GLM-5.2 pricing (from `llm/glm.py` header comment, verified July 2026):
**~$1.20 / MTok input, ~$4.10 / MTok output.**

### 8.1 Estimate, with assumptions stated explicitly

This repo has no real 30-day activity history yet to measure against (early
stage, per `product_metrics`' single-workspace note) — so this is a
worked-example estimate, not a measurement. Re-derive once a few weeks of
real `dashboard_events` volume exists.

| Component | Assumption | Est. tokens |
|---|---|---|
| System prompt (§4.1) | ~350 words | ~500 |
| `events_summary` (aggregated, not raw) | ~50 agent/event-type count pairs | ~800 |
| `metrics_summary` (aggregated) | handful of products × 30 days of deltas | ~1,500 |
| Git commit log (30 days) | ~30-60 commits × one-line subjects, per recent `git log` pace | ~1,200 |
| **Input total** | | **~4,000 tokens** |
| Output (JSON: findings + proposals + summary) | `max_tokens=4000` cap, typical actual usage well under cap for a quiet-to-moderate night | ~800–1,500 tokens |

**Cost per run:** (4,000 / 1,000,000 × $1.20) + (1,200 / 1,000,000 × $4.10)
≈ $0.0048 + $0.0049 ≈ **~$0.01/run**.

**Monthly cost (30 runs):** ≈ **$0.30/month**. Trivial relative to the
$1.20/$4.10 MTok rate — the binding cost driver here is `max_tokens`, not
input size; if findings routinely fill the 4000-token cap, monthly cost
rises to roughly $0.50, still trivial. Worth re-checking this estimate
against real `resp.prompt_tokens`/`resp.completion_tokens` after the first
few live runs rather than treating this table as final.

---

## 9. Open Questions (do not resolve in implementation without a decision)

- **OQ-1:** Should `FORGE_BRAIN.md` (this spec, git-committed, Actions-writable)
  eventually merge with the existing `ForgeBrain` class's Obsidian-vault
  output, or stay permanently separate (one is "system nightly log", the
  other is "human-curated pattern wiki")? Recommend staying separate — they
  have different audiences and update cadences — but flagging since the
  naming collision (`forge_brain.py` vs `FORGE_BRAIN.md`) will confuse future
  sessions if not documented.
- **OQ-2:** Cost-ledger recording (`context.record_tokens`) requires a
  `ProjectContext`, which doesn't exist for a standalone cron agent. Build a
  minimal adapter, or accept that nightly-reasoning spend is tracked only via
  §8's estimate + manual OpenRouter dashboard checks?
- **OQ-3 (blocks true "closed-loop" per the original request):** Lemon
  Squeezy/Resend raw event ingestion (§2.3) doesn't exist. Build it as a
  prerequisite, or explicitly scope v1 without it?

---

## 10. Known Limitations

Single, explicit statement of what this spec's v1 does **not** cover —
consolidating the gaps already noted inline (§0.3, §2.3) into one place so
they can't be missed on a skim of the spec.

- **Lemon Squeezy and Resend events are not currently persisted to Supabase.**
  No table in the platform's own Supabase project stores raw Lemon Squeezy
  webhook payloads or Resend email events. `agents/scaffold.py` only wires a
  `/api/billing/webhook` handler into each *generated product's own* backend
  — never into the ForgeOS platform's own project. This was confirmed by grep
  across the repo, not assumed (§0.3).
- **Pattern detection in this spec is scoped to `dashboard_events`,
  `product_metrics`, and git commit history only** (§3.1–§3.4), until Lemon
  Squeezy/Resend ingestion is built as a prerequisite (§2.3; OQ-3 above). Any
  reading of "closed-loop artifact corpus" against this spec should be
  understood as scoped to these three sources for v1 — not as reasoning over
  every data source the request named.
- Building Lemon Squeezy/Resend ingestion into the platform's own Supabase
  project is explicitly **out of scope for this document**. It is a separate,
  smaller spec/implementation task that should land before
  NightlyReasoningAgent can honestly claim to reason over payment or email
  signal, not something this spec silently substitutes for.
