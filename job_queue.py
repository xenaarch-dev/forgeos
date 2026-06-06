"""
ForgeOS job queue — Redis + rq.

Usage:
    from queue import enqueue_build, get_job_status
    job = enqueue_build("Build a habit tracker SaaS")
    status = get_job_status(job.id)

Falls back to a synchronous in-process run when Redis is unavailable
(FORGEOS_SYNC_FALLBACK=true or redis not reachable).
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import RUNTIME


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobStatus:
    job_id: str
    status: str          # queued | started | finished | failed
    idea: str
    build_id: str
    result: dict | None = None
    error: str = ""
    enqueued_at: str = ""
    started_at: str = ""
    finished_at: str = ""


def _get_redis():
    """Return a Redis connection, or None if Redis is unavailable."""
    redis_url = RUNTIME.redis_url if hasattr(RUNTIME, "redis_url") else os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        from redis import Redis
        r = Redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        return r
    except Exception:
        return None


def _get_queue(redis_conn=None):
    from rq import Queue as RQQueue
    conn = redis_conn or _get_redis()
    if conn is None:
        raise RuntimeError("Redis unavailable — cannot create queue")
    return RQQueue("forgeos", connection=conn)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def enqueue_build(
    idea: str,
    workdir: str | None = None,
    god_mode: bool = False,
) -> "Any":
    """
    Enqueue a build job.

    Returns an rq.Job when Redis is available.
    Falls back to synchronous run and returns a mock job when not.
    """
    build_id = f"build-{uuid.uuid4().hex[:8]}"
    job_kwargs = {"idea": idea, "build_id": build_id, "workdir": workdir, "god_mode": god_mode}

    redis_conn = _get_redis()
    if redis_conn is None or os.environ.get("FORGEOS_SYNC_FALLBACK", "").lower() == "true":
        # Synchronous fallback
        return _SyncJob(build_id=build_id, kwargs=job_kwargs)

    q = _get_queue(redis_conn)
    job = q.enqueue(
        _run_build_job,
        kwargs=job_kwargs,
        job_id=build_id,
        job_timeout=3600,
        result_ttl=86400,
    )
    return job


def get_job_status(job_id: str) -> JobStatus:
    """Return the current status of a build job."""
    redis_conn = _get_redis()
    if redis_conn is None:
        return JobStatus(
            job_id=job_id,
            status="unknown",
            idea="",
            build_id=job_id,
            error="Redis unavailable",
        )
    try:
        from rq.job import Job
        job = Job.fetch(job_id, connection=redis_conn)
        result = job.result if job.is_finished else None
        error = str(job.exc_info or "") if job.is_failed else ""
        return JobStatus(
            job_id=job_id,
            status=job.get_status(refresh=True),
            idea=str((job.kwargs or {}).get("idea", "")),
            build_id=job_id,
            result=result,
            error=error,
            enqueued_at=str(job.enqueued_at or ""),
            started_at=str(job.started_at or ""),
            finished_at=str(job.ended_at or ""),
        )
    except Exception as e:
        return JobStatus(job_id=job_id, status="error", idea="", build_id=job_id, error=str(e))


def list_jobs(limit: int = 50) -> list[JobStatus]:
    """Return recent jobs from the queue."""
    redis_conn = _get_redis()
    if redis_conn is None:
        return []
    try:
        from rq import Queue as RQQueue
        from rq.job import Job
        q = RQQueue("forgeos", connection=redis_conn)
        jobs = []
        for jid in q.job_ids[:limit]:
            try:
                jobs.append(get_job_status(jid))
            except Exception:
                pass
        return jobs
    except Exception:
        return []


# ------------------------------------------------------------------
# Internal job runner (called by rq worker)
# ------------------------------------------------------------------

def _run_build_job(
    idea: str,
    build_id: str,
    workdir: str | None = None,
    god_mode: bool = False,
) -> dict:
    """
    Actually run the ForgeOS pipeline.
    This function runs inside the rq worker process.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from orchestrator import run_pipeline
    result = run_pipeline(idea=idea, workdir=workdir, build_id=build_id, god_mode=god_mode)
    return result


# ------------------------------------------------------------------
# Synchronous mock job (no Redis)
# ------------------------------------------------------------------

class _SyncJob:
    """Returned when Redis is unavailable — runs synchronously on `.result`."""

    def __init__(self, build_id: str, kwargs: dict) -> None:
        self.id = build_id
        self.kwargs = kwargs
        self._result: dict | None = None
        self._error: str = ""
        self._run()

    def _run(self) -> None:
        try:
            self._result = _run_build_job(**self.kwargs)
        except Exception as e:
            self._error = str(e)

    @property
    def result(self) -> dict | None:
        return self._result

    def get_status(self, refresh=False) -> str:
        if self._error:
            return "failed"
        if self._result is not None:
            return "finished"
        return "started"

    @property
    def is_finished(self) -> bool:
        return self._result is not None

    @property
    def is_failed(self) -> bool:
        return bool(self._error)


__all__ = ["enqueue_build", "get_job_status", "list_jobs", "JobStatus"]
