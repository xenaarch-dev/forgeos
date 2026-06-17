"""
ForgeOS build queue.

Flat-file FIFO queue for unattended builds:

  builds/queue/pending/<job_id>.json   — waiting to be processed
  builds/queue/archive/<job_id>.json   — completed (archived, never deleted)

Job IDs are UTC-timestamped so alphabetical sort == chronological (FIFO).
Each file is a self-contained JSON record — no database, no lock files.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_DEFAULT_ROOT = Path("builds/queue")


class BuildQueue:
    """Persistent flat-file FIFO queue for ForgeOS build jobs."""

    def __init__(self, root: Path | str | None = None) -> None:
        self._root = Path(root) if root else _DEFAULT_ROOT
        self._pending = self._root / "pending"
        self._archive = self._root / "archive"
        self._pending.mkdir(parents=True, exist_ok=True)
        self._archive.mkdir(parents=True, exist_ok=True)

    def enqueue(self, idea: str, source: str = "manual") -> str:
        """Add a build idea to the queue. Returns the new job_id."""
        now = datetime.now(timezone.utc)
        # %f gives 6-digit microseconds — guarantees chronological sort even
        # within the same second (FIFO by filename == FIFO by creation time).
        job_id = f"{now.strftime('%Y%m%dT%H%M%S_%f')}_{uuid.uuid4().hex[:4]}"
        job: dict[str, Any] = {
            "id": job_id,
            "idea": idea,
            "source": source,
            "queued_at": now.isoformat(),
            "status": "pending",
        }
        (self._pending / f"{job_id}.json").write_text(
            json.dumps(job, indent=2), encoding="utf-8"
        )
        return job_id

    def pop_next(self) -> dict[str, Any] | None:
        """
        Remove and return the oldest pending job, or None if the queue is empty.

        The file is deleted from pending/ immediately on pop — the caller is
        responsible for calling archive() once the build finishes.
        """
        files = sorted(self._pending.glob("*.json"))
        if not files:
            return None
        path = files[0]
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            path.unlink(missing_ok=True)
            return None
        path.unlink()
        return job

    def archive(self, job: dict[str, Any], status: str, error: str = "") -> None:
        """Write a completed (or failed) job to the archive directory."""
        record: dict[str, Any] = {
            **job,
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        if error:
            record["error"] = error[:2000]
        (self._archive / f"{job['id']}.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )

    def list_pending(self) -> list[dict[str, Any]]:
        """Return all pending jobs in FIFO order (oldest first)."""
        jobs: list[dict[str, Any]] = []
        for path in sorted(self._pending.glob("*.json")):
            try:
                jobs.append(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return jobs

    def pending_count(self) -> int:
        return len(list(self._pending.glob("*.json")))


__all__ = ["BuildQueue"]
