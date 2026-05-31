# ForgeOS — Session Handoff (2026-05-15)

## Repo
`https://github.com/padmajakotoky73-hash/forgeos` — branch `main`, commit `d73cc21`

## What ForgeOS is
Fully autonomous 5-agent product factory: give it one English sentence, it returns a
built + tested + deployed SaaS. Runs on WSL2 Ubuntu with Ollama (qwen2.5-coder:7b on
RTX 4050) as primary LLM, Claude haiku-4-5 as fallback.

Pipeline: **architect → scaffold → coder → (game, skipped) → security → deploy**

---

## What was done this session

### Full pipeline is working end-to-end
Two builds ran to completion:
- `5a3768d39ef3` — "link-in-bio SaaS" (1,719 log lines, 18 min)
- `afe5064c3c8d` — "habit tracker SaaS" (2,419 log lines, 19 min)

Both reached deploy. GitHub repos were created successfully on each.

### Code fixes shipped (all in `main`)

| File | Fix |
|------|-----|
| `tools/http.py` | Added default `User-Agent: ForgeOS/0.2` — fixes Railway Cloudflare 403 |
| `tools/railway.py` | Added `get_project_environments(project_id)` — Railway auto-creates a "production" env on `projectCreate`; fetching it instead of re-creating avoids the 409 "environment already exists" error |
| `agents/deploy.py` | `_step_railway`: uses `get_project_environments` instead of `create_environment` |
| `agents/deploy.py` | `_step`: now logs full `APIError.body` (no more silent 400s) |
| `agents/deploy.py` | `_step_vercel`: catches "Login Connection" 400 and raises an actionable message |
| `forgeos-ui/hooks/useStream.ts` | SSE format fix: handles `done`/`build_complete` and `text`/`message` |
| `forgeos-ui/app/page.tsx` | v0.2 badge, hero headline "One sentence. Full SaaS." at 6xl |
| `forgeos-ui/components/build/IdeaInput.tsx` | Terminal aesthetic: `❯` prompt, monospace, no glassmorphism |

### UI is live
```bash
# Start backend (WSL2)
cd ~/forge/forgeos && PYTHONPATH=. python3 api.py   # port 8000

# Start frontend (WSL2)
cd ~/forge/forgeos/forgeos-ui && npm run dev         # port 3000
```

---

## What is blocked (deploy URLs not yet working)

### 1. Railway — "Not Authorized" on `serviceCreate`

**Status**: `projectCreate` ✅ works. `get_project_environments` ✅ works.  
`serviceCreate` (linking GitHub repo to a service) ❌ returns "Not Authorized".

**Diagnosis**: The Railway token can create projects and query envs but cannot create
services. The Railway web UI shows "0 days or $5.00 left" in red — the trial has
likely expired. The API token's scope may be limited on the free/expired tier.

**Railway GitHub App**: IS installed (the web UI at railway.com/new/github showed all
repos — padmajakotoky73-hash repos were listed). So the GitHub connection is fine.
The blocker is purely the `serviceCreate` authorization on the token/plan.

**How to fix (try in order)**:
1. Go to railway.app → Account → Billing → add a card (Hobby is $5/month, you get
   $5 free credit each month so it's effectively free if usage stays low)
2. After upgrading, regenerate the Railway API token and update `RAILWAY_TOKEN` in
   `.env` (WSL path: `/home/padmaja/forge/forgeos/.env`)
3. Re-run the deploy step (see "Re-running deploy" below)

**Alternative if Railway stays broken**: Switch to Fly.io or Render.com — both have
genuinely free tiers and REST APIs that are simpler. Ask Claude to swap out
`tools/railway.py` for a `tools/fly.py` implementation.

---

### 2. Vercel — GitHub App not installed

**Status**: Vercel account connected GitHub login (Authentication step done ✅).
But `create_project` with a `gitRepository` still returns:
> "To link a GitHub repository, you need to install the GitHub integration first."

**How to fix**:
1. Go to: **https://github.com/apps/vercel** → click **Install** → select the
   `padmajakotoky73-hash` account → authorize all repos (or specific repos)
2. That's it — no code changes needed. The Vercel API will work after this.

---

## Re-running deploy after fixes

```bash
# Option A: fresh build (cleanest)
cd ~/forge/forgeos
PYTHONPATH=. python3 api.py &         # ensure API is running
curl -s -X POST http://localhost:8000/builds \
  -H 'Content-Type: application/json' \
  -d '{"idea":"Build a habit tracker SaaS with user auth and a Pro plan via Lemon Squeezy"}'

# Watch status
curl -s http://localhost:8000/builds/<new-id> | python3 -m json.tool | grep -E 'status|repo_url|backend_url|frontend_url'
```

The next build should produce:
- `repo_url`: `https://github.com/padmajakotoky73-hash/...`
- `backend_url`: `https://railway.app/project/...`
- `frontend_url`: `https://something.vercel.app`

---

## Environment (quick ref)

```
Machine:    ASUS TUF + RTX 4050, Windows 11, WSL2 Ubuntu
Primary LLM: Ollama qwen2.5-coder:7b (port 11434)
Fallback:   Claude haiku-4-5 (ANTHROPIC_API_KEY in .env)
WSL path:   /home/padmaja/forge/forgeos
Windows path: C:\Users\PADMAJA\OneDrive\Documents\Claude\Projects\Claude + Obsidian as second Brain\forgeos
GitHub:     https://github.com/padmajakotoky73-hash/forgeos
Build logs: /home/padmaja/forge/forgeos/.forgeos/<build-id>/
API:        http://localhost:8000
UI:         http://localhost:3000
```

**File sync**: Edit in OneDrive → `cp '/mnt/c/Users/PADMAJA/OneDrive/...' ~/forge/forgeos/...`

---

## Railway token in .env

```bash
# .env location (WSL)
/home/padmaja/forge/forgeos/.env

# After regenerating Railway token:
# Edit .env, update RAILWAY_TOKEN=<new-token>
# No server restart needed — loaded fresh each build
```

---

## Known issues / watch list

- `serviceCreate` mutation: `branch` field is at `ServiceCreateInput` level, NOT
  inside `source` — this was already fixed in `tools/railway.py` (the old code passed
  `branch` inside `source` which is an invalid field on `ServiceSourceInput`)
- CI check: GitHub Actions is set up in generated projects but often fails
  (`_poll_ci` skips on failure) — not a blocker, deploy still runs
- Railway project cleanup: all test projects deleted, Railway is at 0 projects

---

## Starting message for tomorrow's session

Paste this at the start of the next Claude session:

```
Hi Claude! I'm Xena, resuming ForgeOS v0.2 work. Fresh context below.

REPO: https://github.com/padmajakotoky73-hash/forgeos (branch main, commit d73cc21)
HANDOFF: see HANDOFF.md in the repo root

WHAT WORKS:
- Full 5-agent pipeline (architect→scaffold→coder→security→deploy) runs end-to-end
- GitHub repos are created on every build ✅
- Railway project + environment creation works ✅
- SSE streaming UI works ✅

TWO BLOCKERS remaining before we get live Railway + Vercel URLs:

1. RAILWAY serviceCreate "Not Authorized"
   - Likely: trial expired ("0 days or $5.00 left" shown in red on railway.app)
   - Fix: add billing card on railway.app → regenerate API token → update RAILWAY_TOKEN in .env
   - After fixing: run a fresh build and check backend_url in context.json

2. VERCEL GitHub App not installed
   - Fix: go to https://github.com/apps/vercel → Install → select padmajakotoky73-hash account
   - After fixing: run a fresh build and check frontend_url in context.json

ENVIRONMENT:
- WSL2 Ubuntu at /home/padmaja/forge/forgeos
- Ollama qwen2.5-coder:7b on port 11434 (GPU, RTX 4050)
- API: PYTHONPATH=. python3 api.py (port 8000)
- UI: cd forgeos-ui && npm run dev (port 3000)

TODAY'S GOAL: fix both blockers and get the first live Railway URL + Vercel URL from a ForgeOS build.
```
