# Local Cron — GBrain Indexing — Specification

> Status: SPEC ONLY — no implementation. Review before any code is written.
> Spec date: 2026-08-02 (Day 195)
> Author: Padmaja Kotoky + Claude Sonnet 5
> Runs on: local WSL2 (Ollama, RTX 4050) — the deliberate opposite of
> [[SPEC_NightlyReasoningAgent]], which runs on GitHub Actions specifically
> so it doesn't depend on the laptop. This job depends on the laptop by
> design (it needs the local GPU) — the spec's job is to make that
> dependency visible and non-silent, not to hide it.

---

## 0. What "index GBrain content" means here — and what doesn't exist yet

`gbrain/README.md`'s own roadmap lists as **not yet done**: "Vector-search
index (pgvector in Supabase) for semantic pattern retrieval." That roadmap
item is this spec. Confirmed nothing has been built toward it: no `pgvector`
extension reference, no embeddings table, no embedding-generation code
anywhere in the repo. This spec is the first concrete design for it, not a
description of something partially built.

Scope: this job reads `gbrain/patterns/technical.json` and
`gbrain/patterns/legal.json`, generates an embedding per pattern entry using
Qwen2.5-coder:7b via local Ollama, and upserts `(pattern_id, embedding,
metadata)` rows into a new Supabase table. It does not modify the source
JSON files — same read-only-toward-source posture as ArchitectAgent's
existing consumption of these files.

**Open question up front (OQ-1, §8):** Qwen2.5-coder:7b is a *code/chat*
model — `llm/ollama.py`'s client calls Ollama's `/api/chat` endpoint, which
returns generated text, not embedding vectors. Ollama separately exposes
`/api/embeddings`, which needs an embedding-capable model pulled locally
(e.g. `nomic-embed-text`, ~270MB, fits easily alongside qwen2.5-coder on a
6GB RTX 4050). This spec assumes a second, small embedding model gets
pulled for this specific job — flagged clearly rather than silently
assumed, since "via Ollama" in the request named the chat model, not an
embedding model, and those are different model classes.

---

## 1. Trigger: WSL2 cron vs Windows Task Scheduler

Two independent scheduling paths were requested. They are not redundant —
they cover different failure modes:

- **WSL2 cron** only fires while the WSL2 VM is running. WSL2 VMs typically
  stop shortly after the last attached terminal/process exits (a few minutes
  of inactivity, `wsl.exe --shutdown` behavior), so `cron` inside WSL2 is
  **not** reliable for anything scheduled while the user isn't actively
  working — the guest OS itself may not be up.
- **Windows Task Scheduler**, running on the Windows 11 host, can wake and
  launch a task regardless of whether WSL2 is currently running — it invokes
  `wsl.exe` directly, which boots the WSL2 VM on demand.

**Recommendation: Windows Task Scheduler is the actual trigger; WSL2 cron
is not used for the primary schedule.** WSL2 `cron` is listed below anyway
per the request, with the reliability caveat made explicit, since it's a
reasonable fallback for an already-running long session.

### 1.1 Windows Task Scheduler (primary)

Create via `schtasks` (run from an elevated Windows terminal, not inside
WSL2):

```cmd
schtasks /create /tn "ForgeOS-GBrainIndex" /tr "wsl.exe -d Ubuntu-22.04 -- bash -lc '/home/padmaja/forge/forgeos/scripts/gbrain_index.sh'" /sc daily /st 02:00 /rl LIMITED /f
```

- `/sc daily /st 02:00` — daily at 02:00 local time (deliberately offset
  from the 00:30 UTC nightly reasoning cron — see §3 for why the ordering
  matters).
- `/rl LIMITED` — runs with standard (non-admin) privileges; this task only
  needs to invoke `wsl.exe` and write local files, no elevation needed.
- Task Scheduler's own "Wake the computer to run this task" option (set via
  the GUI, `Properties → Conditions`, not exposed in the one-line `schtasks
  /create`) should be **left unchecked** — per §2, a sleeping/off machine is
  an expected, handled case, not something to fight by waking hardware.
- `wsl.exe -d Ubuntu-22.04` matches the distro named in
  `docs/adr/ADR-001-daemon-mode.md` (§, "WSL2 distro | Ubuntu-22.04").

### 1.2 WSL2 cron (fallback / redundant path, reliability caveat applies)

```cron
# crontab -e inside WSL2 — only fires if the WSL2 VM happens to be running
# at :00 that hour. Not the primary trigger; see §1's reliability note.
0 2 * * * /home/padmaja/forge/forgeos/scripts/gbrain_index.sh >> /home/padmaja/forge/forgeos/logs/gbrain_index.log 2>&1
```

`cron` is not started automatically in most WSL2 distros — `service cron
status` after any fresh WSL2 boot to confirm, and add `sudo service cron
start` to shell profile startup if it's meant to run opportunistically
during active sessions (not relied upon as the sole trigger, per §1).

---

## 2. Machine-Off Behavior

This is the core design constraint the request called out, and it's
handled at two points: **detection** (did the scheduled run actually happen)
and **catch-up** (what happens once the machine is back).

### 2.1 Detection — Windows Task Scheduler's own history

Task Scheduler records a missed run automatically if the machine is off/
asleep at 02:00 — visible in `Task Scheduler → Task Scheduler Library →
ForgeOS-GBrainIndex → History` tab, and queryable via:

```powershell
Get-ScheduledTaskInfo -TaskName "ForgeOS-GBrainIndex"
```

`LastTaskResult` will show a non-zero/skip indicator if it never launched.
This spec does not duplicate that bookkeeping — it's already Task
Scheduler's job — but the job script itself must not assume it ran at
exactly 02:00 (see §2.2).

### 2.2 What `scripts/gbrain_index.sh` must log on every invocation

```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="/home/padmaja/forge/forgeos/.forgeos/gbrain_index_state.json"
NOW_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LAST_RUN="$(jq -r '.last_run_utc // empty' "$STATE_FILE" 2>/dev/null || echo "")"

if [ -n "$LAST_RUN" ]; then
  HOURS_SINCE=$(( ( $(date -u -d "$NOW_UTC" +%s) - $(date -u -d "$LAST_RUN" +%s) ) / 3600 ))
  if [ "$HOURS_SINCE" -gt 36 ]; then
    echo "[gbrain-index] $NOW_UTC catch-up run — last successful run was ${HOURS_SINCE}h ago (>36h threshold), machine was likely off at one or more scheduled times"
  fi
fi

echo "[gbrain-index] $NOW_UTC starting indexing run"
# ... indexing logic (§4) ...
echo "[gbrain-index] $NOW_UTC completed — $PATTERN_COUNT patterns indexed, $UPSERT_COUNT rows upserted"
jq -n --arg t "$NOW_UTC" --arg n "$PATTERN_COUNT" '{last_run_utc: $t, last_pattern_count: ($n|tonumber)}' > "$STATE_FILE"
```

Key points:
- `.forgeos/gbrain_index_state.json` lives under the existing `.forgeos/`
  state directory (already gitignored — "ForgeOS state" section of
  `.gitignore`), so it's local-only, not something that needs syncing itself.
- **36-hour threshold, not 24** — a daily job with a 2-hour late tolerance
  before flagging "machine was probably off" avoids false-positive "skipped"
  logs from an ordinary few-hours-late run (laptop opened at 9am instead of
  2am, still same calendar day).
- This is explicitly the "log a clear 'skipped — machine off,' don't fail
  silently" requirement — it doesn't try to detect *why* the machine was
  off (asleep vs. shut down vs. WSL2 not running are all indistinguishable
  from inside the script that only runs once the machine is back), it just
  makes the gap visible in the log with a real elapsed-time number.

### 2.3 Catch-up vs. wait-for-next-run — resolved as: always catch up, but idempotently

Given Ollama indexing is cheap (local, no API cost, a few seconds per
pattern on an RTX 4050) and `gbrain/patterns/*.json` rarely changes more
than a few times a week, **the job always runs fully on next boot/next
schedule fire rather than trying to "catch up" multiple missed days
individually** — there's nothing to catch up *per missed day*, since each
run re-indexes the full current state of `gbrain/patterns/*.json`, not a
diff since last run. A missed run just means the Supabase index was stale
for longer; the next run (whenever it happens) brings it fully current.
This is simpler and correct because indexing is idempotent (§4.2's upsert
key), unlike, say, a log-shipping job where missed intervals genuinely lose
data.

---

## 3. Syncing Results Back to Supabase — Ordering vs. NightlyReasoningAgent

This is the piece that makes the two specs one closed loop instead of two
disconnected halves.

### 3.1 New table: `gbrain_embeddings`

Proposed migration (not applied — spec only, per file scope):

```sql
-- gbrain_embeddings: vector index over gbrain/patterns/*.json, written by
-- the local WSL2/Ollama indexing job, read by anything needing semantic
-- pattern retrieval (ArchitectAgent's future upgrade path per gbrain/README.md
-- roadmap; NightlyReasoningAgent could optionally query it too, though v1
-- of that spec doesn't — see SPEC_NightlyReasoningAgent §9 OQ-1 scope note).
create extension if not exists vector;

create table if not exists gbrain_embeddings (
    id           uuid primary key default gen_random_uuid(),
    pattern_id   text not null unique,   -- matches gbrain pattern "id" field
    category     text not null check (category in ('technical', 'legal')),
    title        text not null,
    embedding    vector(768),            -- nomic-embed-text output dim; confirm
                                          -- against actual model before creating
    source_hash  text not null,          -- sha256 of the pattern's JSON, so a
                                          -- re-run can skip unchanged entries
    indexed_at   timestamptz not null default now()
);

alter table gbrain_embeddings enable row level security;

create policy "gbrain_embeddings_select_authenticated"
    on gbrain_embeddings for select
    to authenticated
    using (true);

create index if not exists gbrain_embeddings_vector_idx
    on gbrain_embeddings using ivfflat (embedding vector_cosine_ops);
```

Written to by the local job via `SUPABASE_SERVICE_ROLE_KEY` (same pattern as
`tools/supabase_admin.py` and the generated products' backends) — the local
machine needs outbound network access to Supabase's API, which it already
has for every other ForgeOS Supabase interaction, so no new connectivity
requirement.

### 3.2 Why this answers "how does the Actions-run Nightly agent see local results"

Because indexing writes **to Supabase, not to any local-only file**, the
GitHub Actions runner in `SPEC_NightlyReasoningAgent.md` can read
`gbrain_embeddings` the same way it reads `dashboard_events` — a normal
Supabase query, no dependency on the laptop being on *at read time*, only a
dependency on the laptop having been on *at some point* to have written the
rows. This is the same principle as `product_metrics`: written locally or
by whatever process, read by anything with the service-role key, regardless
of where that reader runs.

### 3.3 Scheduling ordering: local job before nightly reasoning job

Local indexing is scheduled at 02:00 local time (§1.1); NightlyReasoningAgent
runs at 00:30 UTC. Whether local-02:00 happens before or after Actions-00:30
UTC on a given calendar day depends on IST offset and isn't guaranteed
either way — and **this doesn't matter for v1**, because
`SPEC_NightlyReasoningAgent.md` doesn't currently read `gbrain_embeddings` at
all (see its §9 OQ-1 scope note — it reads `dashboard_events` +
`product_metrics` + git log only). If a future revision of that spec adds a
`gbrain_embeddings` read, ordering would need to be revisited then — flagged
here so it isn't forgotten, not solved prematurely for a dependency that
doesn't exist yet.

---

## 4. Indexing Logic

### 4.1 Read

```python
import json
from pathlib import Path

patterns = []
for f in Path("gbrain/patterns").glob("*.json"):
    category = f.stem  # "technical" or "legal"
    for entry in json.loads(f.read_text()):
        patterns.append({**entry, "category": category})
```

Matches the schema documented in `gbrain/README.md` §"Schema" — each entry
already has `id`, `title`, `tags`, `pattern`, `when_to_use`, `example`,
`related`.

### 4.2 Embed — skip unchanged entries via `source_hash`

```python
import hashlib

for p in patterns:
    content = json.dumps(p, sort_keys=True)
    source_hash = hashlib.sha256(content.encode()).hexdigest()
    existing = supabase.table("gbrain_embeddings").select("source_hash").eq("pattern_id", p["id"]).execute()
    if existing.data and existing.data[0]["source_hash"] == source_hash:
        continue  # unchanged since last index — skip embedding call, save GPU time
    embed_text = f"{p['title']}\n{p['pattern']}\n{p['when_to_use']}"
    embedding = ollama_embed(embed_text)  # POST http://localhost:11434/api/embeddings
    supabase.table("gbrain_embeddings").upsert({
        "pattern_id": p["id"],
        "category": p["category"],
        "title": p["title"],
        "embedding": embedding,
        "source_hash": source_hash,
    }, on_conflict="pattern_id").execute()
```

`upsert(..., on_conflict="pattern_id")` is what makes §2.3's "always
re-run fully, don't try to catch up per-missed-day" safe — re-running
against unchanged patterns is a fast no-op (hash check short-circuits
before any embedding call), and re-running against changed patterns just
overwrites the stale row. No missed-day bookkeeping needed.

### 4.3 Ollama embedding call

```bash
curl -s http://127.0.0.1:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "<embed_text>"
}'
```

Requires `ollama pull nomic-embed-text` once, ahead of first run — not
covered by the existing `OLLAMA_MODEL=qwen2.5-coder:7b` env var in
CLAUDE.md's `.env` reference, since that names the chat model, not this
job's embedding model (per §0's OQ-1).

---

## 5. Failure Behavior (indexing run itself, machine assumed on)

| Failure | Behavior |
|---|---|
| Ollama daemon not running (`curl` to 11434 fails) | Log `[gbrain-index] ERROR: Ollama not reachable on 127.0.0.1:11434 — is 'ollama serve' running?`, exit non-zero, do not update `.forgeos/gbrain_index_state.json` (so §2.2's staleness check correctly still reports this as not-yet-recovered on the next run). |
| `nomic-embed-text` not pulled | Same as above — Ollama returns a model-not-found error; log it explicitly with the exact `ollama pull nomic-embed-text` fix command, don't just surface the raw HTTP error. |
| Supabase upsert fails (network, auth) | Log and continue to next pattern rather than aborting the whole run — one bad row shouldn't block indexing the rest. Collect failures, log a final `$FAILED_COUNT failed` summary line so it's visible without needing to grep per-row. |
| `gbrain/patterns/*.json` fails to parse | Abort entirely — matches `gbrain/README.md`'s existing CI validation step (`python3 -c "import json, pathlib; [json.loads(p.read_text()) for p in pathlib.Path('gbrain/patterns').glob('*.json')]"`); a malformed source file is a repo-state bug, not something to index around. |

---

## 6. Scripts/Files This Spec Introduces

| Path | Purpose |
|---|---|
| `scripts/gbrain_index.sh` | Entry point invoked by both cron and Task Scheduler (§1, §2.2) |
| `scripts/gbrain_index.py` | Actual read/embed/upsert logic (§4), invoked by the `.sh` wrapper with `PYTHONPATH=.` |
| `.forgeos/gbrain_index_state.json` | Local last-run marker (§2.2) — gitignored, not synced |
| `supabase/migrations/<timestamp>_gbrain_embeddings.sql` | New table (§3.1) — not created by this spec, proposed for a follow-up implementation session |

None of these are created by this document — spec only, per your instruction.

---

## 7. What This Spec Deliberately Does Not Do

- Does not attempt to wake the machine (§1.1 — Task Scheduler's wake option
  left off on purpose; a sleeping laptop staying asleep is correct behavior,
  not a bug to route around).
- Does not try to reconstruct which *specific* scheduled times were missed
  while the machine was off — only "how long has it been since last
  success" (§2.2), which is sufficient because indexing is idempotent
  full-state, not incremental (§2.3).
- Does not have NightlyReasoningAgent read `gbrain_embeddings` yet (§3.3) —
  that table existing is a prerequisite for a future capability, not
  something this spec wires into the nightly reasoning prompt itself.

---

## 8. Open Questions

- **OQ-1 (from §0):** Confirm `nomic-embed-text` (or another Ollama
  embedding model) is the intended embedding model — the original request
  named Qwen2.5-coder:7b, which is a chat/code model without an embeddings
  endpoint. Needs a decision before implementation, not an assumption.
- **OQ-2:** `vector(768)` in §3.1 assumes `nomic-embed-text`'s output
  dimension — verify the exact figure against the model actually chosen in
  OQ-1 before writing the real migration; different embedding models have
  different output dimensions and the column width must match exactly.
- **OQ-3:** Should Windows Task Scheduler's "wake to run" be revisited once
  there's a real cost to staleness (e.g., once `gbrain_embeddings` is
  actually consumed by something time-sensitive)? Left off for now per §7,
  but worth a deliberate re-check rather than a permanent default.
