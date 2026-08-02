---
name: secrets-rotation-check
description: "Monthly read-only re-verification of credentials that have known exposure risk — the Discord webhook used by agents/outreach.py, plus any credential ever exposed in a screenshot, chat log, or commit (discovered fresh each run from git history and session notes, since no static exposure list exists in this repo). Confirms whether each one is still live/unrotated. Never modifies files, never rotates anything itself — flags for human rotation. Use monthly, or immediately after any suspected exposure."
---

# Secrets Rotation Check

Read-only. This skill never rotates, revokes, or edits anything — it only
checks status and reports what a human needs to rotate. Same spirit as
[[security-audit]], narrower and recurring: security-audit is a point-in-time
full sweep; this is a monthly targeted re-check of things already known (or
newly found) to carry exposure risk.

## When to Apply

- Monthly, on a fixed cadence (recommend: first session of each calendar month)
- Immediately after any suspected exposure — a screenshot shared externally,
  a paste, a screen-share, a commit later found to contain a secret
- Before onboarding a new collaborator with repo or channel access

## Why there's no static credential list here

The repo has no existing record of a specific past exposure incident (checked
`STATE.md`, `SOUL.md`, `README.md`, `docs/adr/`, `memory/`). Rather than invent
one, this routine treats "credentials ever exposed" as something to
**rediscover each run**, so it stays correct as new incidents happen instead of
silently going stale. Every run must reconstruct the candidate list from
source before checking it.

## Routine

Run a read-only credential rotation check. Do not modify, rotate, or revoke
anything — report only, prioritized CRITICAL / HIGH / LOW.

1. **Discord webhook (always check this one by name).** Locate the live
   webhook consumer at `agents/outreach.py` (currently reads
   `DISCORD_WEBHOOK_URL` from the environment — confirm this path is still
   accurate, code moves). Confirm:
   - The webhook URL is not present anywhere in tracked files or git history
     (`git grep -n "discord.com/api/webhooks"` across all commits, not just HEAD).
   - The value currently configured is not the same value that has ever
     appeared in a commit, PR description, issue, or chat/session log pasted
     into the repo (`STATE.md`, `memory/`, `docs/`).
   - If any past exposure is found: flag CRITICAL, recommend regenerating the
     webhook in the Discord channel's Integrations settings (old URL becomes
     dead immediately on regeneration).

2. **Rebuild the "ever exposed" candidate list fresh, this run:**
   - `git log --all -p | grep` for the same secret-shaped patterns as
     [[security-audit]] step 1 (`sk-`, `AIza`, `discord.com/api/webhooks`,
     `-----BEGIN`, `SUPABASE`, `LEMON`, `RESEND`, `DOPPLER`, plus generic
     `_KEY=`, `_TOKEN=`, `_SECRET=` assignments with non-empty values).
   - Grep `STATE.md`, `docs/`, `memory/`, and any handoff/session notes for
     the words "screenshot", "exposed", "leaked", "pasted", "shared" within a
     few lines of anything credential-shaped, to catch exposures that
     happened outside git (screen-share, image, chat) but got noted in docs.
   - Treat every hit as a candidate needing a liveness/rotation check below,
     even if it looks like a placeholder — confirm placeholder status, don't
     assume it.

3. **For each candidate credential found in step 2**, determine:
   - Is this value still the one live in the current environment/Doppler
     config (i.e., unrotated since exposure)? Report CRITICAL if yes.
   - Does the corresponding provider offer a cheap liveness probe (e.g. a
     read-only API call) to confirm the key is still active? Note it in the
     finding rather than executing anything destructive or state-changing.

4. **Cross-check against `.env.example` / `agents/scaffold.py` env templates**
   — confirm no real value has ever been committed in place of a placeholder
   (`LEMONSQUEEZY_API_KEY=`, `RESEND_API_KEY=`, etc. should always be empty
   in tracked files).

5. Summarize: for every credential checked, report last-known-exposure date
   (if any), current rotation status, and a recommended action. Do not take
   the action — this skill reports, a human rotates.

Do not fix, rotate, or revoke anything. Just report.
