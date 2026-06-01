"""Dataset collector — logs every ForgeOS run for fine-tuning flywheel.

After 100 runs: fine-tune Qwen locally.
After 500 runs: write the research paper.

Storage layout:
    dataset/runs/<run_id>.json   — full run record
    dataset/runs_index.json      — array of {run_id, timestamp, idea, eval_score, success}
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_DEFAULT_BASE = Path.home() / "forge" / "forgeos" / "dataset"


class DatasetCollector:
    """Write structured run records to disk."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self._base = Path(base_dir) if base_dir else _DEFAULT_BASE
        self._runs_dir = self._base / "runs"
        self._index_path = self._base / "runs_index.json"

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record_run(self, run_data: dict[str, Any]) -> str:
        """Persist a run record. Returns the run_id (generated if absent)."""
        run_id = run_data.get("run_id") or str(uuid.uuid4())
        record = {**run_data, "run_id": run_id}
        if "timestamp" not in record:
            record["timestamp"] = datetime.now(timezone.utc).isoformat()

        self._runs_dir.mkdir(parents=True, exist_ok=True)
        (self._runs_dir / f"{run_id}.json").write_text(
            json.dumps(record, indent=2, default=str), encoding="utf-8"
        )
        self._update_index(run_id, record)
        return run_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> dict[str, Any]:
        """Load a single run record by ID."""
        path = self._runs_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Run not found: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_runs(self) -> list[dict[str, Any]]:
        """Return the index array (lightweight summary of every run)."""
        if not self._index_path.exists():
            return []
        return json.loads(self._index_path.read_text(encoding="utf-8"))

    def get_stats(self) -> dict[str, Any]:
        """Aggregate statistics across all recorded runs."""
        runs = self.list_runs()
        if not runs:
            return {"total_runs": 0, "avg_score": 0.0, "success_rate": 0.0, "top_ideas": []}

        scores = [r["eval_score"] for r in runs if r.get("eval_score") is not None]
        successes = sum(1 for r in runs if r.get("success", False))
        top = sorted(runs, key=lambda r: r.get("eval_score", 0) or 0, reverse=True)
        return {
            "total_runs": len(runs),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
            "success_rate": round(successes / len(runs), 3),
            "top_ideas": [r.get("idea", "") for r in top[:5]],
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_index(self, run_id: str, record: dict[str, Any]) -> None:
        index = self.list_runs()
        index.append({
            "run_id": run_id,
            "timestamp": record.get("timestamp", ""),
            "idea": record.get("idea", ""),
            "eval_score": record.get("eval_score"),
            "success": record.get("success", False),
        })
        self._index_path.write_text(
            json.dumps(index, indent=2, default=str), encoding="utf-8"
        )


__all__ = ["DatasetCollector"]
