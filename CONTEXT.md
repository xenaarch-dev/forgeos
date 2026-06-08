# ForgeOS — Current Context
> Last updated: 2026-05-20. Read this before touching anything.

## What ForgeOS does
One English sentence in → full SaaS out.
It runs a 5-agent pipeline that architects, scaffolds, codes, secures, and deploys a working product.

## Repo
`https://github.com/padmajakotoky73-hash/forgeos` — branch `main`

## Environment
| Thing | Value |
|---|---|
| Machine | ASUS TUF, RTX 4050 6GB, Windows 11 + WSL2 Ubuntu |
| Primary LLM | Ollama `qwen2.5-coder:7b` on port 11434 (GPU) |
| Fallback LLM | Anthropic `claude-haiku-4-5` |
| WSL path | `/home/padmaja/forge/forgeos` |
| Windows path | `C:\Users\PADMAJA\OneDrive\Documents\Claude\Projects\Claude + Obsidian as second Brain\forgeos` |
| API server | `http://localhost:8000` (FastAPI) |
| UI | `http://localhost:3000` (Next.js) |
| Build logs | `/home/padmaja/forge/forgeos/.forgeos/<build-id>/` |

## Start servers
```bash
# WSL2 — backend
cd ~/forge/forgeos && PYTHONPATH=. python3 api.py

# WSL2 — frontend
cd ~/forge/forgeos/forgeos-ui && npm run dev
```

## Trigger a build
```bash
curl -X POST http://localhost:8000/builds \
  -H 'Content-Type: application/json' \
  -d '{"idea":"Build a habit tracker SaaS with user auth and a Pro plan"}'
```

## Check build status
```bash
curl -s http://localhost:8000/builds/<id> | python3 -m json.tool | grep -E 'status|repo_url|backend_url|frontend_url'
```

---

## Pipeline — current status

| Agent | Status | Notes |
|---|---|---|
| ArchitectAgent | ✅ Working | Produces SPEC.md, ARCH.md, TASKS.json, STACK.json |
| ScaffoldAgent | ✅ Working | Creates full project directory tree |
| CoderAgent | ✅ Working | ~18 min, generates all tasks in TASKS.json |
| GameAgent | ✅ Working | Auto-skips if no game keywords in idea |
| SecurityAgent | ✅ Working | Produces SECURITY.md (runs fast, near no-op currently) |
| DeployAgent | ✅ Working | GitHub ✅, Render ✅, Vercel ✅ — URLs generated every build |

## Deploy — what works and what needs fixing

### GitHub ✅
- Repo created, code pushed, CI triggered on every build
- Idempotent: if repo already exists it reuses it

### Render.com ✅ (backend)
- `tools/render.py` — `RenderClient` with `create_web_service`, `get_owner_id`, `trigger_deploy`
- Service created at `https://{repo-name}.onrender.com` every build
- **Known issue**: Generated FastAPI app often has no root `/` route → "Not Found" at root
- **Root cause**: Coder agent prompt doesn't mandate a `/healthz` endpoint
- **Fix needed**: Prompt engineering in coder agent, not infrastructure

### Vercel ✅ (frontend)
- `tools/vercel.py` — `VercelClient` with `create_project`, `trigger_deployment`
- Project created at `https://{repo-name}.vercel.app` every build
- **Known issue**: `DEPLOYMENT_NOT_FOUND` — Vercel can't build the frontend
- **Root cause**: Generated code puts frontend in `frontend/` subdirectory but Vercel deploy trigger doesn't correctly configure root directory, OR repo is private
- **Fix needed**: Either make repos public, or fix `trigger_deployment` to pass correct git source config

### Railway ❌ REMOVED
- Replaced by Render.com. `tools/railway.py` deleted.

---

## File structure
```
forgeos/
├── orchestrator.py        # entry point — runs the full pipeline
├── api.py                 # FastAPI server + SSE streaming on :8000
├── models.py              # LLMClient, LLMError, LLMResponse, ProjectContext
├── config.py              # ToolsConfig dataclass (all API keys + endpoints)
├── agents/
│   ├── base.py            # BaseAgent ABC
│   ├── architect.py       # ArchitectAgent
│   ├── scaffold.py        # ScaffoldAgent
│   ├── coder.py           # CoderAgent
│   ├── game.py            # GameAgent
│   ├── security.py        # SecurityAgent
│   └── deploy.py          # DeployAgent (GitHub + Render + Vercel)
├── llm/
│   ├── router.py          # route() — picks Ollama → Claude
│   ├── ollama.py          # OllamaClient
│   └── claude.py          # ClaudeClient (haiku-4-5)
├── tools/
│   ├── http.py            # http_request() — all HTTP calls go through here
│   ├── github.py          # GitHubClient
│   ├── render.py          # RenderClient ← NEW (replaced railway.py)
│   ├── vercel.py          # VercelClient
│   ├── supabase_admin.py  # SupabaseAdminClient
│   ├── sentry.py          # SentryClient
│   └── uptimerobot.py     # UptimeRobotClient
├── forgeos-ui/            # Next.js 14 frontend
│   ├── app/page.tsx       # Main build page with hero + agent cards
│   ├── hooks/useStream.ts # SSE streaming hook
│   ├── components/build/  # AgentCard, BuildLog, IdeaInput, StatusBadge
│   └── components/sidebar/# Sidebar, BuildHistory
└── .forgeos/              # Runtime build outputs (gitignored)
    └── <build-id>/
        ├── context.json   # Full pipeline state
        ├── SPEC.md
        ├── ARCH.md
        ├── TASKS.json
        └── project/       # Generated codebase
```

## Environment variables (.env in WSL)
```bash
# LLM
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_MODEL=qwen2.5-coder:7b

# Deploy
GITHUB_TOKEN=ghp_...
RENDER_API_KEY=rnd_...
RENDER_OWNER_ID=tea-...
VERCEL_TOKEN=...

# Supabase (for generated projects)
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
```

## Code conventions
- Absolute imports only: `from models import X` not `from .models import X`
- Always run with `PYTHONPATH=.`
- All HTTP goes through `tools/http.py:http_request()`
- Agents inherit from `agents/base.py:BaseAgent`
- No truncation — always write full files

## Known bugs to fix (in priority order)
1. **Coder prompt**: must always generate `/healthz` route in FastAPI backend
2. **Vercel deployment**: `trigger_deployment` needs correct `rootDirectory` config for `frontend/` subdir
3. **Security agent**: near no-op — needs real RLS policy generation and secrets audit
4. **CI always fails**: generated GitHub Actions workflow has issues — `_poll_ci` always skips on failure

---

## Next focus: Missions Architecture
See `SPEC.md` for the full ForgeOS product vision and Missions spec.
