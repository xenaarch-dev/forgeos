"""
ForgeOS API Server.

FastAPI backend that wraps the orchestrator and exposes:
  POST /builds          → start a new build, returns {id}
  GET  /builds          → list all builds (active + from filesystem)
  GET  /builds/{id}     → build details + status
  GET  /builds/{id}/stream → SSE stream of live output
  GET  /health          → liveness check

Run with:
  cd ~/forge/forgeos
  PYTHONPATH=. python3 api.py

Or via uvicorn directly:
  PYTHONPATH=. uvicorn api:app --host 0.0.0.0 --port 8000 --reload
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
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
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
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ForgeOS API",
    version="1.0.0",
    description="Autonomous AI product factory",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory build registry
# Active builds: id → {id, idea, status, started_at, finished_at, workdir, log}
# ---------------------------------------------------------------------------

_builds: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class BuildRequest(BaseModel):
    idea: str
    workdir: str | None = None


class BuildOut(BaseModel):
    id: str
    idea: str
    status: str          # pending | running | success | failed
    started_at: str
    finished_at: str | None = None
    workdir: str


# ---------------------------------------------------------------------------
# Helper: UTC ISO timestamp
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Helper: load builds from filesystem (past runs)
# ---------------------------------------------------------------------------


def _scan_fs_builds() -> list[dict]:
    """Walk .forgeos workdir root for context.json files."""
    results: list[dict] = []
    root = Path(RUNTIME.workdir_root)
    if not root.exists():
        return results
    for d in sorted(root.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        if d.name in _builds:
            continue  # already tracked in-memory
        ctx_file = d / "context.json"
        if not ctx_file.exists():
            continue
        try:
            ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
            results.append(
                {
                    "id": d.name,
                    "idea": ctx.get("idea", "—"),
                    "status": "success",
                    "started_at": ctx.get("started_at", ""),
                    "finished_at": ctx.get("updated_at", ""),
                    "workdir": str(d),
                }
            )
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# Background: run orchestrator subprocess
# ---------------------------------------------------------------------------


async def _run_build(build_id: str, idea: str, workdir: str) -> None:
    """Spawn orchestrator.py and pipe its output into _builds[build_id]['log']."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_HERE)
    env["FORGEOS_ENABLE_OBSIDIAN"] = "false"  # skip during API-driven builds

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
                _builds[build_id]["log"].append(line)

    await asyncio.gather(_drain(proc.stdout), _drain(proc.stderr))
    await proc.wait()

    if build_id in _builds:
        _builds[build_id]["status"] = "success" if proc.returncode == 0 else "failed"
        _builds[build_id]["finished_at"] = _now()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


@app.post("/builds", response_model=BuildOut, status_code=201)
async def start_build(req: BuildRequest) -> dict:
    build_id = uuid.uuid4().hex[:12]
    workdir = req.workdir or str(Path(RUNTIME.workdir_root) / build_id)
    Path(workdir).mkdir(parents=True, exist_ok=True)

    record: dict = {
        "id": build_id,
        "idea": req.idea.strip(),
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "workdir": workdir,
        "log": [],
    }
    _builds[build_id] = record

    # Fire-and-forget; don't await
    asyncio.create_task(_run_build(build_id, req.idea.strip(), workdir))

    return record


@app.get("/builds")
async def list_builds() -> list[dict]:
    active = list(_builds.values())
    past = _scan_fs_builds()
    # Return active first (most recent), then past
    seen = {b["id"] for b in active}
    return active + [b for b in past if b["id"] not in seen]


@app.get("/builds/{build_id}")
async def get_build(build_id: str) -> dict:
    if build_id in _builds:
        return _builds[build_id]

    # Try filesystem
    ctx_file = Path(RUNTIME.workdir_root) / build_id / "context.json"
    if ctx_file.exists():
        try:
            ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
            return {
                "id": build_id,
                "idea": ctx.get("idea", "—"),
                "status": "success",
                "started_at": ctx.get("started_at", ""),
                "finished_at": ctx.get("updated_at", ""),
                "workdir": str(ctx_file.parent),
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
    if build_id not in _builds:
        raise HTTPException(status_code=404, detail="Build not found or already complete")

    async def _events() -> AsyncGenerator[str, None]:
        record = _builds[build_id]
        SSE_END = "\n\n"  # SSE requires double newline after each event

        # Replay existing lines first
        cursor = 0
        for line in record["log"]:
            payload = json.dumps({"type": "log", "text": line})
            yield "data: " + payload + SSE_END
        cursor = len(record["log"])

        # Stream new lines with keepalive heartbeat every 15s
        # Prevents Next.js proxy and browser from timing out idle SSE
        ticks_since_data = 0
        while record["status"] == "running":
            await asyncio.sleep(0.5)
            ticks_since_data += 1
            log = record["log"]
            if len(log) > cursor:
                for line in log[cursor:]:
                    payload = json.dumps({"type": "log", "text": line})
                    yield "data: " + payload + SSE_END
                cursor = len(log)
                ticks_since_data = 0
            elif ticks_since_data >= 30:  # 30 * 0.5s = 15s
                yield ": keepalive" + SSE_END
                ticks_since_data = 0

        # Flush any final lines
        log = record["log"]
        if len(log) > cursor:
            for line in log[cursor:]:
                payload = json.dumps({"type": "log", "text": line})
                yield "data: " + payload + SSE_END

        # Terminal event
        done_payload = json.dumps({"type": "done", "status": record["status"]})
        yield "data: " + done_payload + SSE_END


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
    if build_id in _builds:
        return {"log": _builds[build_id]["log"]}

    # Try summary file
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

    # Only watch source dirs — exclude .forgeos/ build output so
    # Uvicorn does not restart mid-build when CoderAgent writes .py files.
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
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
