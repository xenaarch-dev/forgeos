"""
GBrainLogger — per-agent structured event logger for the GBrain flywheel.

Writes two artefacts per agent run:

  sessions/  <project_id>_<agent>.jsonl   — append-only event stream
  summary/   <project_id>_<agent>.json    — closed-run summary (written on finish)

The summary schema is intentionally compatible with ForgeBrain.compile() so
any single agent run can be replayed as an Obsidian wiki note without
re-executing the full build.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import AgentResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GBrainLogger:
    """Append-only structured event log for a single ForgeAgent run.

    Usage::

        logger = GBrainLogger(agent_name="architect")
        logger.start(project_id)
        ...
        logger.log_event("step", {"msg": "parsing spec"})
        logger.log_llm_call("claude-sonnet-4-6", "spec_parse", 1200, 800, 0.012)
        logger.log_artifact("SPEC.md", 4096)
        logger.finish(result)
    """

    def __init__(
        self,
        agent_name: str,
        root: str | None = None,
    ) -> None:
        self.agent_name = agent_name
        self._root = Path(root or "~/.forgeos/gbrain").expanduser()
        self._sessions_dir = self._root / "sessions"
        self._summary_dir = self._root / "summary"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._summary_dir.mkdir(parents=True, exist_ok=True)

        self._project_id: str = ""
        self._events: list[dict[str, Any]] = []
        self._started_at: str = ""
        self._session_path: Path | None = None
        self._workdir_events_path: Path | None = None
        self._total_cost: float = 0.0
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, project_id: str, workdir: str | None = None) -> None:
        """Begin a new logging session.

        workdir — when provided, events are also appended to
        ``<workdir>/gbrain-events.jsonl`` so the API server can tail
        that file across the subprocess boundary.
        """
        self._project_id = project_id
        self._started_at = _now()
        self._events.clear()
        self._total_cost = 0.0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

        slug = f"{project_id}_{self.agent_name}"
        self._session_path = self._sessions_dir / f"{slug}.jsonl"

        self._workdir_events_path = None
        if workdir:
            self._workdir_events_path = Path(workdir) / "gbrain-events.jsonl"

    def finish(self, result: AgentResult) -> None:
        """Close the session and write the summary JSON."""
        self.log_event(
            "finish",
            {
                "status": result.status,
                "duration_seconds": result.duration_seconds,
                "error": result.error,
                "total_cost_usd": round(self._total_cost, 6),
                "total_prompt_tokens": self._total_prompt_tokens,
                "total_completion_tokens": self._total_completion_tokens,
            },
        )
        self._write_summary(result)

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------

    def log_event(self, event: str, payload: dict[str, Any]) -> None:
        """Append a generic event to the session log."""
        entry: dict[str, Any] = {
            "ts": _now(),
            "event": event,
            "agent": self.agent_name,
            "project_id": self._project_id,
        }
        entry.update(payload)
        self._events.append(entry)
        self._append_jsonl(entry)

    def log_llm_call(
        self,
        model: str,
        purpose: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> None:
        """Record a single LLM invocation and accumulate cost/token totals."""
        self._total_cost += cost_usd
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self.log_event(
            "llm_call",
            {
                "model": model,
                "purpose": purpose,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost_usd,
                "cumulative_cost_usd": round(self._total_cost, 6),
            },
        )

    def log_artifact(self, relpath: str, size_bytes: int) -> None:
        """Record that an artifact was written."""
        self.log_event("artifact", {"relpath": relpath, "size_bytes": size_bytes})

    def log_gate(self, gate_name: str, score: float, passed: bool, feedback: str) -> None:
        """Record a quality-gate verdict."""
        self.log_event(
            "gate",
            {
                "gate": gate_name,
                "score": round(score, 2),
                "passed": passed,
                "feedback": feedback[:500],
            },
        )

    # ------------------------------------------------------------------
    # Read-only accessors
    # ------------------------------------------------------------------

    @property
    def total_cost_usd(self) -> float:
        return round(self._total_cost, 6)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def events_by_type(self, event: str) -> list[dict[str, Any]]:
        return [e for e in self._events if e.get("event") == event]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _append_jsonl(self, entry: dict[str, Any]) -> None:
        serialised = json.dumps(entry, default=str) + "\n"
        for path in (self._session_path, self._workdir_events_path):
            if path is None:
                continue
            try:
                with path.open("a", encoding="utf-8") as f:
                    f.write(serialised)
            except OSError:
                pass

    def _write_summary(self, result: AgentResult) -> None:
        if not self._project_id:
            return
        slug = f"{self._project_id}_{self.agent_name}"
        summary_path = self._summary_dir / f"{slug}.json"
        llm_events = self.events_by_type("llm_call")
        artifact_events = self.events_by_type("artifact")
        summary = {
            "project_id": self._project_id,
            "agent": self.agent_name,
            "started_at": self._started_at,
            "finished_at": _now(),
            "status": result.status,
            "duration_seconds": result.duration_seconds,
            "error": result.error,
            "total_cost_usd": round(self._total_cost, 6),
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "llm_call_count": len(llm_events),
            "models_used": list({e["model"] for e in llm_events if "model" in e}),
            "artifacts_written": [e["relpath"] for e in artifact_events if "relpath" in e],
            "event_count": len(self._events),
            "output_keys": list(result.output.keys()),
        }
        try:
            summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        except OSError:
            pass


__all__ = ["GBrainLogger"]
