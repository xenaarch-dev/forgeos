# LaunchAgent — Specification

> Status: SPEC ONLY — no implementation (agents/launch.py does not exist)
> Spec date: 2026-06-15 (Day 157)
> Author: Padmaja Kotoky + Claude Sonnet 4.6
> Ready for: implementation review

---

## 1. Purpose

LaunchAgent produces go-to-market draft assets for the product that ForgeOS just built and deployed. It runs **after** DeployAgent and writes a single `LAUNCH.md` artifact containing ready-to-edit drafts — nothing is posted or submitted automatically.

**The gap it fills:**  
DeployAgent ends with `DEPLOYMENT.md` (live URLs, CI status, runbook). The pipeline then terminates. There's no agent that takes those URLs and drafts the announcement copy, the outreach seed list, or the Product Hunt listing in a product-aware way. `agents/distribution/` has CLI tools for this (PostAgent, ProspectAgent, OutreachQueue), but they're manual and product-agnostic — Padmaja runs them by hand after the build. LaunchAgent generates the product-specific content at build time so drafts are ready when she's ready to launch.

**LaunchAgent is scoped to:** draft production for LAUNCH.md.  
**LaunchAgent is NOT scoped to:** sending, submitting, or publishing anything.

---

## 2. Pipeline Position

| Attribute | Value |
|-----------|-------|
| Stage number | 20 (final stage) |
| Name key | `"launch"` |
| Class | `LaunchAgent` |
| Gate | `False` — never blocks the pipeline |
| Left neighbor | DeployAgent (stage 19) |
| Right neighbor | terminal — end of pipeline |

### Placement in `hermes.py._build_pipeline()`

```python
# After the existing deploy entry:
{"name": "deploy",  "cls": DeployAgent,  "gate": False},
# Add:
{"name": "launch",  "cls": LaunchAgent,  "gate": False},
```

**Gate rationale:** LaunchAgent can't block a deploy — the product is already live. Failure degrades gracefully (LAUNCH.md omitted, context records `"launch_skipped": True`).

---

## 3. Contract

### 3a. `requires`

```python
requires = ["idea", "project_id", "spec", "frontend_url", "backend_url", "repo_url"]
```

All six fields are populated by the time DeployAgent exits. `frontend_url` / `backend_url` may be empty strings if DeployAgent degraded — LaunchAgent must handle both cases without raising.

### 3b. `capabilities`

```python
capabilities = ["LAUNCH.md"]
```

Written to `<workdir>/LAUNCH.md`. Also written to `<workdir>/project/LAUNCH.md` (mirrors DEPLOYMENT.md pattern from DeployAgent).

### 3c. `budget_usd`

```python
budget_usd = 0.0   # unlimited — late pipeline, all meaningful spend already incurred
```

**Reasoning:** By stage 20, every expensive agent (ArchitectAgent, MissionWorkerLoop, SecurityAgent, EvalAgent) has already run. A budget cap at this stage is meaningless — there's nothing to protect. Matching DeployAgent's pattern: `budget_usd = 0.0`.

---

## 4. What `_execute` Produces

`_execute` makes **one LLM call** with the product context and generates three draft sections. All three land in `LAUNCH.md`.

### 4a. Product Hunt Listing Draft

```
Name:       <product name, ≤ 60 chars>
Tagline:    <one-liner, ≤ 60 chars — no emoji, no "revolutionary">
Description: <3–4 sentences, what it does, who it's for, why now — ≤ 260 chars>
Gallery captions: <3 captions, one per screenshot placeholder>
First comment: <founder's comment from Padmaja — personal, builder-to-builder tone>
```

**Product Hunt gate (non-goal):** LaunchAgent drafts the listing. It does NOT submit. The actual PH submission is gated on 10 paying customers — that's a human decision point, not a pipeline decision.

### 4b. Outreach Seed List

5–10 ICP (ideal customer profile) entries seeded from the product's SPEC.md description. Each entry has:
```json
{
  "handle": "<suggested X/LinkedIn handle pattern or named prospect>",
  "platform": "x | linkedin",
  "context": "<why they'd be interested — 1 sentence>"
}
```

This list is written as a `## Outreach Seed` section in LAUNCH.md. Padmaja runs `agents/distribution/outreach_queue.py add` manually for each entry she wants to act on — LaunchAgent does NOT call `OutreachQueue.add()`.

### 4c. Launch Announcement Thread Draft

A 3–5 tweet thread using PostAgent's voice rules (Xena's voice):
- Direct and specific. Real numbers. Real tech.
- No "excited to announce", "game-changer", "🚀", "💡"
- Lowercase is fine. Fragments are fine.
- Thread[0]: the product and what it does (≤ 280 chars)
- Thread[1]: what ForgeOS actually built — tech stack detail
- Thread[2]: live URL + CTA

This is written as `## Launch Thread` in LAUNCH.md. Padmaja copies it into PostAgent's interactive review or posts manually — LaunchAgent does NOT call PostAgent.

---

## 5. LAUNCH.md Structure

```markdown
# LAUNCH.md — <product name>

> DRAFT — all content requires Padmaja's review before posting.
> Generated: <ISO timestamp>
> ForgeOS build: <project_id>

---

## Product Hunt Draft

**Name:** ...
**Tagline:** ...
**Description:** ...

### Gallery captions
1. ...
2. ...
3. ...

### First comment (from Padmaja)
...

---

## Outreach Seed

| Handle | Platform | Context |
|--------|----------|---------|
| ...    | ...      | ...     |

Run for each entry you want to queue:
    python3 agents/distribution/outreach_queue.py add --handle "<handle>" --platform "<platform>"

---

## Launch Thread

**[1/3]** ...

**[2/3]** ...

**[3/3]** ...

---

## Checklist

- [ ] Padmaja reviewed Product Hunt draft
- [ ] Padmaja reviewed outreach seed list
- [ ] Padmaja reviewed launch thread
- [ ] Live URL confirmed working: <frontend_url or backend_url>
- [ ] Product Hunt submission (when ≥ 10 paying customers)
```

---

## 6. Human-in-Loop Touchpoints

LaunchAgent generates drafts; Padmaja approves before anything goes public.

| Content | Human gate | Where |
|---------|-----------|-------|
| Product Hunt listing | Required before submitting | PH dashboard |
| Outreach DMs | Required before OutreachQueue.add() | CLI |
| X launch thread | Required before posting | PostAgent interactive review |
| PH submission itself | Gated on ≥ 10 paying customers | Manual decision |

**Implementation rule:** `_execute` must write `LAUNCH.md` with a prominent `> DRAFT` header. It must also set `context.metadata["launch_draft_ready"] = True` and `context.metadata["launch_needs_review"] = True` — these flags are what the SSE stream and ForgeOS UI use to surface the approval prompt to Padmaja.

---

## 7. ForgeAgent Skeleton

```python
from forge_sdk.agent import ForgeAgent

class LaunchAgent(ForgeAgent):
    name         = "launch"
    phase        = "launch"
    capabilities = ["LAUNCH.md"]
    requires     = ["idea", "project_id", "spec", "frontend_url", "backend_url", "repo_url"]
    budget_usd   = 0.0
    tools        = []  # no external tools — LLM + file write only

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        raise NotImplementedError
```

---

## 8. Explicit Non-Goals

1. **Does not post to X** — drafts only; PostAgent CLI handles posting after Padmaja reviews.
2. **Does not submit to Product Hunt** — gated on 10 paying customers; Padmaja decides when.
3. **Does not call OutreachQueue.add()** — writes the seed list; Padmaja queues manually.
4. **Does not duplicate DEPLOYMENT.md** — no infrastructure or URL runbook content.
5. **Does not overlap with PostAgent** — PostAgent is event-driven (any event, any time); LaunchAgent is build-time only, for the just-shipped product.
6. **Does not do market research** — reads SPEC.md and the idea string only; no web search.

---

## 9. LLM Strategy

Single call, medium-complexity prompt (SPEC.md + product URLs → structured LAUNCH.md content). Route via standard LLM router: Ollama first, Claude haiku-4-5 fallback.

Expected cost: <$0.01 per build on Claude haiku (few-hundred-token completion).

---

## 10. Open Questions for Padmaja Before Implementation

1. **LAUNCH.md location**: Write to `<workdir>/LAUNCH.md` only, or also commit it into `<workdir>/project/` (alongside DEPLOYMENT.md)? The project repo is already on GitHub by stage 20.

2. **Outreach seed scope**: Seed list based solely on SPEC.md + idea string, or should LaunchAgent also read `context.metadata["pm_output"]` (PMAgent's ICP analysis) to get richer persona data?

3. **Product Hunt draft model**: Product Hunt requires a maker account and a listed product. Should the spec include a `ph_product_slug` field in context for future auto-submit, or keep PH submission permanently manual?

4. **Gate vs. terminal**: Current spec says `gate=False`. If Padmaja wants the pipeline to pause and surface LAUNCH.md for in-session review before closing, should this be a soft gate (score always passes, but triggers a Telegram notification to Padmaja)?

5. **VoiceAgent integration**: VoiceAgent exists as a standalone TTS utility (`agents/voice_agent.py`). Should LaunchAgent call VoiceAgent to produce a 30-second pitch audio file and attach it to LAUNCH.md as a "podcast-style intro" asset, or is that a separate phase?
