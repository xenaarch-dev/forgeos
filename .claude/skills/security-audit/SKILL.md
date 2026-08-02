---
name: security-audit
description: "Read-only security audit of the ForgeOS repo. Searches full git history for leaked secrets, verifies .gitignore coverage and that no .env is tracked, runs npm audit / pip-audit for HIGH+CRITICAL CVEs, flags risky GitHub Actions workflow patterns (pull_request_target + untrusted checkout), flags hardcoded IPs/URLs/credentials, and confirms secrets are Doppler-backed rather than ad hoc os.environ/process.env reads. Reports CRITICAL/HIGH/LOW findings with file:line references. Never modifies files. Use before a release, before a security review, or any time you need a point-in-time read on repo secret hygiene."
---

# Security Audit

Read-only repo security audit. This skill never edits, deletes, or commits
anything — it only reads and reports.

## When to Apply

- Before pushing to `origin/main` on a day with dependency or workflow changes
- Before a release, demo, or external review
- After any commit that touches `.github/workflows/`, `.gitignore`, `config.py`,
  or anything under `tools/`
- Any time you want a current point-in-time read on secret hygiene, independent
  of the monthly [[secrets-rotation-check]] cadence

## Context (repo-specific, read before reporting)

- Documented target state (`README.md`, `SOUL.md`, `memory/glossary.md`) is
  **Doppler for production secrets**. `docs/adr/ADR-001-daemon-mode.md` records
  that, as of that ADR, actual local/dev secrets live in `~/.bashrc` exports —
  **not** Doppler. Step 7 of the routine below must report what is actually
  true at audit time, not what the docs aspire to — if `~/.bashrc` or plain
  `os.environ`/`process.env` reads are still the reality, that is a finding,
  not a pass.
- `.gitignore` already contains `.claude/*.lock`, which covers
  `.claude/scheduled_tasks.lock` specifically — confirm this pattern still
  matches rather than assuming the literal filename must appear.

## Routine

Run a read-only security audit of this repo. Do not modify any files.
Report findings with file:line references, prioritized CRITICAL / HIGH / LOW.

1. Search the FULL git history (not just HEAD) for likely leaked secrets:
   API keys, tokens, webhook URLs, private keys, passwords. Check patterns
   like sk-, AIza, discord.com/api/webhooks, -----BEGIN, SUPABASE, LEMON,
   RESEND, DOPPLER. Use git log -p or git grep across all commits.
2. Confirm .gitignore covers: .env*, .env.local, *.pem, *.key,
   node_modules, .next, __pycache__, .claude/scheduled_tasks.lock.
3. Confirm no .env file is tracked: git ls-files | grep -i env
4. Run npm audit --production (or pip-audit) and summarize HIGH/CRITICAL
   CVEs only.
5. Flag any GitHub Actions workflow using pull_request_target combined
   with checkout of untrusted/fork code.
6. Flag any hardcoded IPs, internal URLs, or credentials outside of
   Doppler/env-var handling.
7. Confirm Doppler is the only source of secrets — grep for
   os.environ / process.env not backed by a Doppler-injected variable.

Do not fix anything. Just report.
