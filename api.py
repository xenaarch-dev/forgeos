"""
ForgeOS API Server.

FastAPI backend that wraps the orchestrator and exposes:
  POST /builds          → start a new build, returns {id}
  GET  /builds          → list all builds (active + from filesystem)
  GET  /builds/{id}     → build details + status
  GET  /builds/{id}/stream → SSE stream of live output
  POST /command         → route one free-text command through the agent mesh
  GET  /command/{id}    → full transcript (reload / late join)
  GET  /command/{id}/stream → SSE stream of the live command
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
from mesh.auth import (  # noqa: E402
    AuthError,
    RateLimiter,
    auth_required,
    issue_stream_token,
    user_id_from_claims,
    verify_bearer,
    verify_stream_token,
)
from mesh.models import MESH_ARGS_KEY, Capability  # noqa: E402
from mesh.registry import default_registry  # noqa: E402
from mesh.router import MeshRouter  # noqa: E402
from mesh.store import MeshStore  # noqa: E402
from models import AgentStatus, ProjectContext  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_LOG_LINES = 5_000          # cap per-build in-memory log
_MAX_IDEA_LENGTH = 2_000        # characters
_ALLOWED_METHODS = ["GET", "POST", "OPTIONS"]

_MAX_COMMAND_LENGTH = 2_000     # characters
_COMMANDS_SUBDIR = "commands"   # <workdir_root>/commands/<command_id>  (SPEC §7a)
_COMMAND_QUEUE_MAX = 1_000      # wake-up buffer; events[] is authoritative
_STREAM_KEEPALIVE_SECONDS = 15.0

_COMMAND_RUNNING = "running"

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ForgeOS API",
    version="0.1.0",
    description="Autonomous AI product factory",
)

# CORS — explicit allowlist (SPEC_AgentMesh.md §6d). Never "*": credentials
# are in play, and a wildcard with allow_credentials is both unsafe and
# rejected by browsers. The regex covers Vercel preview deployments.
_ALLOWED_ORIGINS = [
    "https://forgeos-eight.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_ALLOWED_ORIGIN_REGEX = r"^https://forgeos-[a-z0-9\-]+\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=_ALLOWED_ORIGIN_REGEX,
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
    """SSE endpoint. Three event shapes:
        {"type": "log",          "text": "<line>"}
        {"type": "agent_event",  "event": "<name>", "agent": "<name>", ...}
        {"type": "done",         "status": "success"|"failed"}

    agent_event fields mirror GBrainLogger entries verbatim:
      start      — {agent, phase}
      llm_call   — {model, purpose, prompt_tokens, completion_tokens, cost_usd}
      artifact   — {relpath, size_bytes}
      gate       — {gate, score, passed, feedback}
      success    — {agent, output_keys}
      error      — {agent, error}
      finish     — {status, duration_seconds, total_cost_usd, ...}
    """
    if not build_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid build ID")
    if build_id not in _builds:
        raise HTTPException(status_code=404, detail="Build not found or already complete")

    async def _events() -> AsyncGenerator[str, None]:
        record = _builds[build_id]
        gbrain_path = Path(record["workdir"]) / "gbrain-events.jsonl"

        def _read_gbrain(offset: int) -> tuple[list[dict], int]:
            """Read new GBrain JSONL events starting at byte offset."""
            if not gbrain_path.exists():
                return [], offset
            try:
                with gbrain_path.open("rb") as f:
                    f.seek(offset)
                    raw = f.read()
                new_offset = offset + len(raw)
                events: list[dict] = []
                for line in raw.decode("utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except (json.JSONDecodeError, ValueError):
                        pass
                return events, new_offset
            except OSError:
                return [], offset

        # Replay existing text log lines
        cursor = 0
        for line in record["log"]:
            yield _sse_event(json.dumps({"type": "log", "text": line}))
        cursor = len(record["log"])

        # Replay any GBrain events already written before we started listening
        gbrain_offset = 0
        gbrain_events, gbrain_offset = _read_gbrain(gbrain_offset)
        for ev in gbrain_events:
            yield _sse_event(json.dumps({"type": "agent_event", **ev}))

        # Stream new events; keepalive comment every 15 s
        ticks_since_data = 0
        while record["status"] == "running":
            await asyncio.sleep(0.5)
            ticks_since_data += 1
            emitted_something = False

            # Text log
            log = record["log"]
            if len(log) > cursor:
                for line in log[cursor:]:
                    yield _sse_event(json.dumps({"type": "log", "text": line}))
                cursor = len(log)
                emitted_something = True

            # GBrain events (byte-offset tail — only reads new bytes)
            gbrain_events, gbrain_offset = _read_gbrain(gbrain_offset)
            for ev in gbrain_events:
                yield _sse_event(json.dumps({"type": "agent_event", **ev}))
                emitted_something = True

            if emitted_something:
                ticks_since_data = 0
            elif ticks_since_data >= 30:  # 30 × 0.5 s = 15 s
                yield ": keepalive\n\n"
                ticks_since_data = 0

        # Flush any final text lines that arrived after status flipped
        log = record["log"]
        for line in log[cursor:]:
            yield _sse_event(json.dumps({"type": "log", "text": line}))

        # Flush any final GBrain events
        gbrain_events, _ = _read_gbrain(gbrain_offset)
        for ev in gbrain_events:
            yield _sse_event(json.dumps({"type": "agent_event", **ev}))

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
# Agent mesh — SPEC_AgentMesh.md §5
#
# Unlike /builds, a mesh command runs IN-PROCESS (§5b): a command is seconds
# rather than half an hour, so process-spawn overhead is a real fraction of its
# latency, and ForgeAgent._emit() already hands over a typed dict that would
# otherwise have to survive a round trip through subprocess stdout and be
# re-parsed.
#
# ForgeAgent.run() is blocking, so it goes to a worker thread and its
# event_callback fires there too — hence call_soon_threadsafe to hand events
# back to the loop. Everything else reuses the /builds SSE contract unchanged.
# ---------------------------------------------------------------------------

_commands: dict[str, dict] = {}

#: Write-through persistence (§7a). Disabled and harmless without Supabase.
_store = MeshStore()

#: Strong refs to in-flight persistence tasks — asyncio only holds weak ones,
#: so without this the GC can collect a task mid-write.
_persist_tasks: set[asyncio.Task] = set()


#: §6e — per-user command quotas, enforced server-side.
_rate_limiter = RateLimiter()

#: Identity used only when auth has been explicitly waived for local dev.
_ANONYMOUS_USER = "local-dev"


def _authenticate(request: Request) -> str:
    """Supabase JWT -> user id, for POST /command and GET /command/{id} (§6c).

    Enforced unless MESH_ALLOW_UNAUTH=true is set, which is for localhost
    development only. The default is closed, so a deployment that forgets to
    configure anything rejects requests rather than serving them openly.
    """
    if not auth_required():
        return _ANONYMOUS_USER
    claims = verify_bearer(request.headers.get("Authorization"))
    return user_id_from_claims(claims)


@app.exception_handler(AuthError)
async def _auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """One shape for 401/403/429 so the transcript can render any of them."""
    return JSONResponse(status_code=exc.status, content={"detail": exc.detail})


def _persist_async(fn, *args, **kwargs) -> None:
    """Fire-and-forget a blocking store write without stalling the event loop.

    Persistence is a side effect of a command, never a precondition: a stalled
    or failing database must not slow the SSE stream or fail the command.
    """
    if not _store.enabled:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        fn(*args, **kwargs)  # no loop (CLI / sync caller) — just do it inline
        return
    task = loop.create_task(asyncio.to_thread(fn, *args, **kwargs))
    _persist_tasks.add(task)
    task.add_done_callback(_persist_tasks.discard)


class CommandRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=_MAX_COMMAND_LENGTH)


class CommandOut(BaseModel):
    command_id: str
    status: str          # running | success | failed | clarify | unsupported | unwired
    route: dict
    dispatched: bool     # false => do not open a stream, nothing is running
    detail: str | None = None
    # §6c — EventSource cannot send an Authorization header, so the stream is
    # authorised by a one-time 5-minute token scoped to this command and user.
    # None when nothing was dispatched: there is no stream to authorise.
    stream_token: str | None = None


def _new_command_record(
    command_id: str, text: str, workdir: str, user_id: str = _ANONYMOUS_USER
) -> dict:
    return {
        "id": command_id,
        "text": text,
        "user_id": user_id,
        "status": _COMMAND_RUNNING,
        "route": None,
        "created_at": _now(),
        "finished_at": None,
        "workdir": workdir,
        "events": [],
        "artifact": None,
        "output": None,
        "detail": None,
        "error": None,
        "thread_row_id": None,
        "queue": asyncio.Queue(maxsize=_COMMAND_QUEUE_MAX),
    }


def _emit_command(record: dict, payload: dict) -> None:
    """Record one SSE payload, wake any live stream, and mirror it to Postgres.

    events[] is authoritative; the queue is only a wake-up signal. A dropped
    wake-up (queue full because nobody is listening) therefore loses nothing —
    a late joiner still replays the full transcript by cursor.
    """
    record["events"].append(payload)
    try:
        record["queue"].put_nowait(payload)
    except asyncio.QueueFull:
        pass
    _mirror_event(record, payload)


def _mirror_event(record: dict, payload: dict) -> None:
    """Every mesh event lands in dashboard_events (§5d); artifacts get a row.

    dashboard_events is what the Dashboard ActivityStream and the /app/agents
    activity fields already read, so this is what lights them up with real mesh
    data and no frontend change at all.
    """
    _persist_async(_store.record_event, record["id"], payload)
    if payload.get("type") == "agent_event" and payload.get("event") == "artifact_ready":
        _persist_async(_persist_artifact, record, dict(payload))


def _read_artifact_body(record: dict, payload: dict) -> str:
    """The artifact body, off disk. Falls back to the preview.

    The SSE payload deliberately carries only a preview (§5a), so the body is
    read from the file the capability already wrote (§7a writes it twice: file
    then row). Same workdir-escape guard as ForgeAgent._write.
    """
    relpath = payload.get("workdir_path")
    if relpath:
        try:
            workdir = Path(record["workdir"]).resolve()
            path = (workdir / relpath).resolve()
            if path.is_relative_to(workdir) and path.exists():
                return path.read_text(encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"[api] could not read artifact body: {exc}\n")
    return str(payload.get("preview") or "")


def _persist_artifact(record: dict, payload: dict) -> None:
    """Insert one artifacts row from an artifact_ready event. Blocking; threaded."""
    thread_row_id = record.get("thread_row_id")
    if not thread_row_id:
        return
    _store.insert_artifact(
        thread_row_id,
        {
            "agent": payload.get("agent", ""),
            "artifact_type": payload.get("artifact_type", ""),
            "title": payload.get("title", ""),
            "body": _read_artifact_body(record, payload),
            "status": "pending",
            "workdir_path": payload.get("workdir_path"),
        },
    )


def _command_event_callback(record: dict, loop: asyncio.AbstractEventLoop):
    """Bridge ForgeAgent events from the worker thread onto the event loop."""

    def _callback(event: str, payload: dict) -> None:
        # Envelope keys go last: `type` is the shape discriminator every client
        # filters on, so a payload field of the same name must never win.
        item = {**payload, "type": "agent_event", "event": event}
        loop.call_soon_threadsafe(_emit_command, record, item)

    return _callback


def _finish_command(
    record: dict,
    status: str,
    *,
    detail: str | None = None,
    error: str | None = None,
) -> None:
    record["status"] = status
    record["finished_at"] = _now()
    if detail is not None:
        record["detail"] = detail
    if error is not None:
        record["error"] = error
    _persist_async(
        _store.update_thread, record["id"], status=status, detail=detail, error=error
    )
    _emit_command(record, {"type": "done", "status": status})


def _command_out(record: dict, *, dispatched: bool) -> dict:
    return {
        "command_id": record["id"],
        "status": record["status"],
        "route": record["route"],
        "dispatched": dispatched,
        "detail": record["detail"],
        # Only meaningful when the stream endpoint actually checks it. In open
        # mode there is nothing to authorise, and minting one would require a
        # secret that localhost development has no reason to configure.
        "stream_token": (
            issue_stream_token(record["id"], record["user_id"])
            if dispatched and auth_required()
            else None
        ),
    }


def _public_command(record: dict) -> dict:
    """The record minus the live queue, which is neither public nor serialisable."""
    public = {k: v for k, v in record.items() if k != "queue"}
    public["source"] = "memory"
    return public


def _command_from_store(command_id: str) -> dict | None:
    """Rebuild a command from Postgres. Blocking; call from a thread.

    This is what makes a reconnect work after a restart or from a second tab
    (§6a): the in-memory record dies with the process, the rows do not. The
    transcript is replayed from the dashboard_events mirror, the artifacts from
    their own table.
    """
    thread = _store.get_thread(command_id)
    if thread is None:
        return None

    artifacts = _store.get_artifacts(thread.get("id", ""))
    events = [row.get("metadata") or {} for row in _store.get_events(command_id)]
    confidence = thread.get("confidence")

    return {
        "id": command_id,
        "text": thread.get("input_text", ""),
        "status": thread.get("status", ""),
        "route": {
            "capability": thread.get("routed_capability"),
            "confidence": float(confidence) if confidence is not None else None,
        },
        "created_at": thread.get("created_at"),
        "finished_at": thread.get("updated_at"),
        "workdir": thread.get("workdir"),
        "events": events,
        "artifact": artifacts[-1] if artifacts else None,
        "artifacts": artifacts,
        "output": None,
        "detail": thread.get("detail"),
        "error": thread.get("error"),
        "thread_row_id": thread.get("id"),
        "source": "postgres",
    }


def _require_command(command_id: str) -> dict:
    if not command_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid command ID")
    record = _commands.get(command_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return record


def _was_dispatched(record: dict) -> bool:
    return record["status"] in (_COMMAND_RUNNING, "success", "failed")


async def _run_command(record: dict, adapter_cls, context, on_event) -> None:
    """Run one capability in a worker thread, streaming its events as they land."""
    try:
        agent = adapter_cls(event_callback=on_event)
        result = await asyncio.to_thread(agent.run, context)
    except Exception as exc:  # adapter construction or an escape from run()
        msg = f"{type(exc).__name__}: {exc}"
        _emit_command(record, {"type": "log", "text": f"[command] {msg}"})
        _finish_command(record, "failed", error=msg)
        return

    if result.status == AgentStatus.SUCCESS.value:
        record["output"] = result.output
        record["artifact"] = (result.output or {}).get("artifact")
        _finish_command(record, "success")
    else:
        _finish_command(record, "failed", error=result.error)


@app.post("/command", response_model=CommandOut, status_code=201)
async def start_command(req: CommandRequest, request: Request) -> dict:
    """Route one free-text command. Dispatches only when the router says to.

    The router runs synchronously (§5e) so the response carries the real
    RouteDecision — the UI can render a truthful routing line immediately and,
    on UNSUPPORTED, render nothing further and never open a stream.
    """
    user_id = _authenticate(request)
    _rate_limiter.check(user_id)

    command_id = uuid.uuid4().hex[:12]
    # Server-controlled workdir; the client never supplies a path.
    workdir = str(Path(RUNTIME.workdir_root) / _COMMANDS_SUBDIR / command_id)
    Path(workdir).mkdir(parents=True, exist_ok=True)

    context = ProjectContext.new(idea=req.text, workdir=workdir, build_id=command_id)
    record = _new_command_record(command_id, req.text, workdir, user_id)
    _commands[command_id] = record

    # Awaited, not fire-and-forget: the row id it returns is the FK every
    # artifacts row for this command needs, and "created on submit" is only
    # true if it happens before anything else can reference it.
    if _store.enabled:
        record["thread_row_id"] = await asyncio.to_thread(
            _store.create_thread,
            command_id,
            req.text,
            workdir=workdir,
            user_id=user_id if auth_required() else None,
        )

    loop = asyncio.get_running_loop()
    on_event = _command_event_callback(record, loop)

    # to_thread keeps the classify call (blocking HTTP) off the event loop.
    router = MeshRouter(event_callback=on_event)
    decision = await asyncio.to_thread(router.route, context, req.text)
    record["route"] = decision.model_dump(mode="json")
    _persist_async(
        _store.update_thread,
        command_id,
        routed_capability=decision.capability.value,
        confidence=decision.confidence,
    )

    if not decision.should_dispatch:
        terminal = (
            "clarify" if decision.capability is Capability.CLARIFY else "unsupported"
        )
        _finish_command(
            record,
            terminal,
            detail=decision.unsupported_reason or decision.rationale,
        )
        return _command_out(record, dispatched=False)

    adapter_cls = default_registry().get(decision.capability)
    if adapter_cls is None:
        _finish_command(
            record,
            "unwired",
            detail=f"{decision.display_name} has no adapter wired yet. Nothing ran.",
        )
        return _command_out(record, dispatched=False)

    context.metadata[MESH_ARGS_KEY] = dict(decision.args)
    asyncio.create_task(_run_command(record, adapter_cls, context, on_event))
    return _command_out(record, dispatched=True)


@app.get("/command/{command_id}")
async def get_command(command_id: str, request: Request) -> dict:
    """Full transcript, for a page reload or a late join.

    Serves the live in-memory record when this process still holds it, and
    falls back to Postgres otherwise — so a reconnect after a restart, or from
    a second browser tab, actually sees history (§6a).
    """
    _authenticate(request)
    if not command_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid command ID")

    record = _commands.get(command_id)
    if record is not None:
        return _public_command(record)

    stored = await asyncio.to_thread(_command_from_store, command_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return stored


@app.get("/command/{command_id}/stream")
async def stream_command(command_id: str, t: str | None = None) -> StreamingResponse:
    """SSE stream for one command. Same three event shapes as /builds/{id}/stream:

        {"type": "log",          "text": "<line>"}
        {"type": "agent_event",  "event": "<name>", "agent": "<name>", ...}
        {"type": "done",         "status": "success"|"failed"|...}

    The mesh adds two agent_event names to the set /builds already emits (§5a):
      route          — {capability, confidence, rationale, dispatch}
      artifact_ready — {agent, artifact_type, title, preview}

    Note on coverage: this stream carries what ForgeAgent's event_callback
    delivers — route, start, artifact_ready, success/error, plus anything a
    capability emits itself. It does NOT carry llm_call / artifact / gate /
    finish: GBrainLogger writes those straight to its JSONL without going
    through _emit(), which is why /builds (which tails that file) sees them and
    an in-process listener does not. Closing that gap means changing
    GBrainLogger fan-out, which is not this phase's business.
    """
    if auth_required():
        # EventSource sends no headers, so the query-string token is the only
        # credential available here (§6c).
        verify_stream_token(t, command_id)

    record = _require_command(command_id)
    if not _was_dispatched(record):
        # Nothing ran, so there is no stream to open (§5e). Saying so beats
        # holding a connection open that will never carry an event.
        raise HTTPException(
            status_code=409,
            detail=record["detail"] or "Command was not dispatched — nothing is running",
        )

    async def _events() -> AsyncGenerator[str, None]:
        queue = record["queue"]
        cursor = 0
        while True:
            while cursor < len(record["events"]):
                yield _sse_event(json.dumps(record["events"][cursor]))
                cursor += 1
            if record["status"] != _COMMAND_RUNNING:
                break
            try:
                # The item is discarded — this is a wake-up, not the transport.
                await asyncio.wait_for(queue.get(), timeout=_STREAM_KEEPALIVE_SECONDS)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

        # Final flush: catches anything appended between the last drain and the
        # status check, including the terminal `done`.
        while cursor < len(record["events"]):
            yield _sse_event(json.dumps(record["events"][cursor]))
            cursor += 1

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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
