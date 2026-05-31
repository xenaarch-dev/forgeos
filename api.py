"""
ForgeOS API Server.

FastAPI backend that wraps the orchestrator and exposes:
  POST /builds          → start a new build, returns {id}
  GET  /builds          → list all builds (active + from filesystem)
  GET  /builds/{id}     → build details + status
  GET  /builds/{id}/stream → SSE stream of live output
  GET  /healthz         → liveness check

Authentication
--------------
Set FORGEOS_API_KEY in .env to require a Bearer token on every request.
Leave it unset to run in open mode (localhost dev only — do NOT expose
port 8000 to the internet without an auth key set).

Run with:
  PYTHONPATH=. uvicorn api:app --host 127.0.0.1 --port 8000 \\
    --reload-dir agents --reload-dir llm --reload-dir tools
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

# --- FastAPI ---
try:
    from fastapi import FastAPI, HTTPException, Request, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    print(
        "FastAPI not installed. Run:\n"
        "  pip install fastapi uvicorn[standard]\n",
        file=sys.stderr,
    )
    sys.exit(1)

# --- ForgeOS ---
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from config import RUNTIME  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_LOG_LINES = 5_000          # cap per-build in-memory log
_MAX_IDEA_LENGTH = 2_000        # characters
_ALLOWED_METHODS = ["GET", "POST", "OPTIONS"]

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ForgeOS API",
    version="0.1.0",
    description="Autonomous AI product factory",
)

# CORS — restrict to localhost UI only; allow only the methods we expose.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=_ALLOWED_METHODS,
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ---------------------------------------------------------------------------
# Optional API key authentication
# ---------------------------------------------------------------------------

_API_KEY: str = os.environ.get("FORGEOS_API_KEY", "")


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Require Bearer token when FORGEOS_API_KEY is configured."""
    if not _API_KEY:
        return await call_next(request)
    # Health check is always public
    if request.url.path in ("/healthz", "/health"):
        return await call_next(request)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != _API_KEY:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Unauthorized — set Authorization: Bearer <FORGEOS_API_KEY>"},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# In-memory build registry
# ---------------------------------------------------------------------------

_builds: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class BuildRequest(BaseModel):
    idea: str = Field(..., min_length=1, max_length=_MAX_IDEA_LENGTH)
    # workdir is intentionally not exposed — callers cannot choose the workdir.
    # Removes path-traversal risk entirely.

    @field_validator("idea")
    @classmethod
    def _strip_idea(cls, v: str) -> str:
        return v.strip()


class BuildOut(BaseModel):
    id: str
    idea: str
    status: str          # pending | running | success | failed
    started_at: str
    finished_at: str | None = None
    workdir: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sse_event(payload: str) -> str:
    """Format a single SSE event with the required double-newline terminator."""
    return "data: " + payload + "\n\n"


def _append_log(build_id: str, line: str) -> None:
    """Append a line to the build log, respecting the size cap."""
    log = _builds[build_id]["log"]
    if len(log) < _MAX_LOG_LINES:
        log.append(line)
    elif len(log) == _MAX_LOG_LINES:
        log.append(f"[log truncated at {_MAX_LOG_LINES} lines]")


# ---------------------------------------------------------------------------
# Helpers: load builds from filesystem (past runs)
# ---------------------------------------------------------------------------


def _scan_fs_builds() -> list[dict]:
    """Walk the workdir root for context.json files from previous runs."""
    results: list[dict] = []
    root = Path(RUNTIME.workdir_root)
    if not root.exists():
        return results
    for d in sorted(root.iterdir(), reverse=True):
        if not d.is_dir() or d.name in _builds:
            continue
        ctx_file = d / "context.json"
        if not ctx_file.exists():
            continue
        try:
            ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
            # Derive actual status from agent_results rather than hardcoding "success".
            agent_results = ctx.get("agent_results") or []
            failed = any(r.get("status") == "failed" for r in agent_results)
            derived_status = "failed" if failed else "success"
            results.append(
                {
                    "id": d.name,
                    "idea": ctx.get("idea", "—"),
                    "status": derived_status,
                    "started_at": ctx.get("started_at", ""),
                    "finished_at": ctx.get("updated_at", ""),
                    "workdir": str(d),
                }
            )
        except Exception as exc:
            # Log but don't surface — a corrupt context.json should not break the list.
            sys.stderr.write(f"[api] warning: could not parse {ctx_file}: {exc}\n")
    return results


# ---------------------------------------------------------------------------
# Background: run orchestrator subprocess
# ---------------------------------------------------------------------------


async def _run_build(build_id: str, idea: str, workdir: str) -> None:
    """Spawn orchestrator.py and pipe its output into _builds[build_id]['log']."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_HERE)
    env["FORGEOS_ENABLE_OBSIDIAN"] = "false"

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(_HERE / "orchestrator.py"),
        "--idea", idea,
        "--workdir", workdir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=str(_HERE),
    )

    async def _drain(stream: asyncio.StreamReader) -> None:
        while True:
            raw = await stream.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip()
            if build_id in _builds:
                _append_log(build_id, line)

    await asyncio.gather(_drain(proc.stdout), _drain(proc.stderr))
    await proc.wait()

    if build_id in _builds:
        _builds[build_id]["status"] = "success" if proc.returncode == 0 else "failed"
        _builds[build_id]["finished_at"] = _now()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/healthz")
@app.get("/health")
async def healthz() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.post("/builds", response_model=BuildOut, status_code=201)
async def start_build(req: BuildRequest) -> dict:
    build_id = uuid.uuid4().hex[:12]
    # Workdir is always server-controlled — never accept a path from the client.
    workdir = str(Path(RUNTIME.workdir_root) / build_id)
    Path(workdir).mkdir(parents=True, exist_ok=True)

    record: dict = {
        "id": build_id,
        "idea": req.idea,
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "workdir": workdir,
        "log": [],
    }
    _builds[build_id] = record

    # Fire-and-forget; don't await
    asyncio.create_task(_run_build(build_id, req.idea, workdir))

    return record


@app.get("/builds")
async def list_builds() -> list[dict]:
    active = list(_builds.values())
    past = _scan_fs_builds()
    seen = {b["id"] for b in active}
    return active + [b for b in past if b["id"] not in seen]


@app.get("/builds/{build_id}")
async def get_build(build_id: str) -> dict:
    # Validate build_id is safe (hex only)
    if not build_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid build ID")

    if build_id in _builds:
        return _builds[build_id]

    # Try filesystem
    ctx_file = Path(RUNTIME.workdir_root) / build_id / "context.json"
    if ctx_file.exists():
        try:
            ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
            agent_results = ctx.get("agent_results") or []
            failed = any(r.get("status") == "failed" for r in agent_results)
            return {
                "id": build_id,
                "idea": ctx.get("idea", "—"),
                "status": "failed" if failed else "success",
                "started_at": ctx.get("started_at", ""),
                "finished_at": ctx.get("updated_at", ""),
                "workdir": str(ctx_file.parent),
                "log": [],
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(status_code=404, detail="Build not found")


@app.get("/builds/{build_id}/stream")
async def stream_build(build_id: str) -> StreamingResponse:
    """SSE endpoint. Each event is a JSON object:
        {"type": "log",  "text": "<line>"}
        {"type": "done", "status": "success"|"failed"}
    """
    if not build_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid build ID")
    if build_id not in _builds:
        raise HTTPException(status_code=404, detail="Build not found or already complete")

    async def _events() -> AsyncGenerator[str, None]:
        record = _builds[build_id]

        # Replay existing lines first
        cursor = 0
        for line in record["log"]:
            yield _sse_event(json.dumps({"type": "log", "text": line}))
        cursor = len(record["log"])

        # Stream new lines; send a keepalive comment every 15 s to prevent
        # the Next.js proxy and browser from timing out on idle SSE.
        ticks_since_data = 0
        while record["status"] == "running":
            await asyncio.sleep(0.5)
            ticks_since_data += 1
            log = record["log"]
            if len(log) > cursor:
                for line in log[cursor:]:
                    yield _sse_event(json.dumps({"type": "log", "text": line}))
                cursor = len(log)
                ticks_since_data = 0
            elif ticks_since_data >= 30:  # 30 × 0.5 s = 15 s
                yield ": keepalive\n\n"
                ticks_since_data = 0

        # Flush any final lines that arrived after the status flipped
        log = record["log"]
        for line in log[cursor:]:
            yield _sse_event(json.dumps({"type": "log", "text": line}))

        # Terminal event
        yield _sse_event(json.dumps({"type": "done", "status": record["status"]}))

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/builds/{build_id}/log")
async def get_log(build_id: str) -> dict:
    """Return the full log as a list of strings (for past builds)."""
    if not build_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid build ID")
    if build_id in _builds:
        return {"log": _builds[build_id]["log"]}

    workdir = Path(RUNTIME.workdir_root) / build_id
    summary_file = workdir / "SUMMARY.md"
    if summary_file.exists():
        return {"log": summary_file.read_text(encoding="utf-8").splitlines()}

    raise HTTPException(status_code=404, detail="Build not found")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed. Run: pip install uvicorn[standard]", file=sys.stderr)
        sys.exit(1)

    # Only watch source dirs — exclude .forgeos/ build output so Uvicorn
    # does not restart mid-build when CoderAgent writes .py files there.
    uvicorn.run(
        "api:app",
        host="127.0.0.1",   # localhost only; use a reverse proxy for production
        port=8000,
        reload=True,
        reload_dirs=[
            str(_HERE / "agents"),
            str(_HERE / "llm"),
            str(_HERE / "tools"),
            str(_HERE / "templates"),
        ],
        log_level="info",
    )
