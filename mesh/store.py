"""
MeshStore — write-through persistence for the agent mesh.

SPEC_AgentMesh.md §7a and §8 Phase 4. Three tables:

  command_threads   one row per founder command, updated as it progresses
  artifacts         the reviewable output of a capability run
  dashboard_events  every mesh event, mirrored (§5d)

The dashboard_events mirror is the reason the Dashboard ActivityStream and
the /app/agents activity fields start showing real mesh data with no frontend
change at all: `useDashboardEvents` and `/api/metrics` already read that table.

Degradation is deliberate. With no Supabase credentials every method is a
no-op that says so, exactly as OutreachCapability already behaves (Phase 2):
a laptop with no cloud config must still be able to run the mesh, and losing
a draft because a database is unreachable is the worse failure.

Nothing here raises. Persistence is a side effect of a command, never a
precondition for it.
"""

from __future__ import annotations

import logging
import os
from typing import Any

_log = logging.getLogger(__name__)

#: dashboard_events.event_type is check-constrained to these four values
#: (20260707000000_app_foundations.sql). Mesh event names map onto them.
_EVENT_TYPE_ERROR = "error"
_EVENT_TYPE_GATE = "gate"
_EVENT_TYPE_ACTION = "action"
_EVENT_TYPE_INFO = "info"

_COMMAND_ID_KEY = "command_id"


def classify_event_type(payload: dict[str, Any]) -> str:
    """Map one SSE payload onto the dashboard_events.event_type enum."""
    if payload.get("type") != "agent_event":
        return _EVENT_TYPE_INFO  # log / done
    event = payload.get("event")
    if event == "error":
        return _EVENT_TYPE_ERROR
    if event == "gate":
        return _EVENT_TYPE_GATE
    return _EVENT_TYPE_ACTION


def summarise_event(payload: dict[str, Any]) -> str:
    """One human-readable line for dashboard_events.message."""
    kind = payload.get("type")
    if kind == "log":
        return str(payload.get("text", ""))[:500]
    if kind == "done":
        return f"command finished: {payload.get('status', '')}"

    event = payload.get("event", "event")
    agent = payload.get("agent", "mesh")
    if event == "route":
        return str(payload.get("rationale") or f"routed to {payload.get('capability')}")[:500]
    if event == "artifact_ready":
        return f"artifact ready: {payload.get('title', '')}"[:500]
    if event == "error":
        return str(payload.get("error", ""))[:500]
    return f"{agent}: {event}"[:500]


class MeshStore:
    """Supabase-backed persistence. Every method is best-effort."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client
        self._resolved = client is not None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @staticmethod
    def _credentials() -> tuple[str, str]:
        return (
            os.environ.get("SUPABASE_URL", ""),
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

    @property
    def client(self) -> Any | None:
        """The supabase-py client, or None when unconfigured/unavailable."""
        if self._resolved:
            return self._client
        self._resolved = True
        url, key = self._credentials()
        if not (url and key):
            _log.info("Supabase not configured — mesh persistence disabled")
            return None
        try:
            from supabase import create_client

            self._client = create_client(url, key)
        except Exception as exc:  # missing package, bad URL, network
            _log.warning("Supabase client unavailable — persistence disabled: %s", exc)
            self._client = None
        return self._client

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def _table(self, name: str) -> Any | None:
        client = self.client
        return None if client is None else client.table(name)

    # ------------------------------------------------------------------
    # command_threads
    # ------------------------------------------------------------------

    def create_thread(
        self,
        command_id: str,
        input_text: str,
        *,
        workdir: str | None = None,
        user_id: str | None = None,
    ) -> str | None:
        """Insert the thread row. Returns its uuid — the FK artifacts need."""
        table = self._table("command_threads")
        if table is None:
            return None
        payload = {
            "command_id": command_id,
            "input_text": input_text,
            "status": "running",
            "workdir": workdir,
            "user_id": user_id,
        }
        rows = self._rows("create_thread", lambda: table.insert(payload).execute())
        return (rows[0] or {}).get("id") if rows else None

    def update_thread(
        self,
        command_id: str,
        *,
        status: str | None = None,
        routed_capability: str | None = None,
        confidence: float | None = None,
        detail: str | None = None,
        error: str | None = None,
    ) -> bool:
        table = self._table("command_threads")
        if table is None:
            return False
        payload: dict[str, Any] = {}
        for key, value in (
            ("status", status),
            ("routed_capability", routed_capability),
            ("confidence", confidence),
            ("detail", detail),
            ("error", error),
        ):
            if value is not None:
                payload[key] = value
        if not payload:
            return False
        return self._execute(
            "update_thread",
            lambda: table.update(payload).eq("command_id", command_id).execute(),
        )

    def get_thread(self, command_id: str) -> dict[str, Any] | None:
        table = self._table("command_threads")
        if table is None:
            return None
        rows = self._rows(
            "get_thread",
            lambda: table.select("*").eq("command_id", command_id).limit(1).execute(),
        )
        return rows[0] if rows else None

    # ------------------------------------------------------------------
    # artifacts
    # ------------------------------------------------------------------

    def insert_artifact(
        self,
        thread_row_id: str,
        artifact: dict[str, Any],
        *,
        parent_artifact_id: str | None = None,
    ) -> str | None:
        """Insert one artifacts row. Returns its id, or None when disabled."""
        table = self._table("artifacts")
        if table is None:
            return None
        payload = {
            "command_id": thread_row_id,
            "parent_artifact_id": parent_artifact_id,
            "agent": artifact.get("agent", ""),
            "artifact_type": artifact.get("artifact_type", ""),
            "title": artifact.get("title", ""),
            # body is not-null in the schema; never insert a hole.
            "body": artifact.get("body") or artifact.get("preview") or "",
            "status": artifact.get("status", "pending"),
            "workdir_path": artifact.get("workdir_path"),
        }
        rows = self._rows("insert_artifact", lambda: table.insert(payload).execute())
        return (rows[0] or {}).get("id") if rows else None

    def get_artifacts(self, thread_row_id: str) -> list[dict[str, Any]]:
        table = self._table("artifacts")
        if table is None:
            return []
        return self._rows(
            "get_artifacts",
            lambda: table.select("*")
            .eq("command_id", thread_row_id)
            .order("created_at")
            .execute(),
        )

    # ------------------------------------------------------------------
    # dashboard_events (§5d — the secondary, cross-page feed)
    # ------------------------------------------------------------------

    def record_event(self, command_id: str, payload: dict[str, Any]) -> bool:
        table = self._table("dashboard_events")
        if table is None:
            return False
        row = {
            "agent": payload.get("agent") or "mesh",
            "event_type": classify_event_type(payload),
            "message": summarise_event(payload),
            "metadata": {**payload, _COMMAND_ID_KEY: command_id},
        }
        return self._execute("record_event", lambda: table.insert(row).execute())

    def get_events(self, command_id: str) -> list[dict[str, Any]]:
        """Mesh events for one command, oldest first — the replayable transcript."""
        table = self._table("dashboard_events")
        if table is None:
            return []
        return self._rows(
            "get_events",
            lambda: table.select("*")
            .eq(f"metadata->>{_COMMAND_ID_KEY}", command_id)
            .order("created_at")
            .execute(),
        )

    # ------------------------------------------------------------------
    # Internals — nothing escapes
    # ------------------------------------------------------------------

    @staticmethod
    def _result_rows(result: Any) -> list[dict[str, Any]]:
        if getattr(result, "error", None):
            raise RuntimeError(str(result.error))
        return list(getattr(result, "data", None) or [])

    def _execute(self, what: str, call) -> bool:
        try:
            self._result_rows(call())
            return True
        except Exception as exc:
            _log.warning("mesh persistence %s failed: %s", what, exc)
            return False

    def _rows(self, what: str, call) -> list[dict[str, Any]]:
        try:
            return self._result_rows(call())
        except Exception as exc:
            _log.warning("mesh persistence %s failed: %s", what, exc)
            return []


__all__ = ["MeshStore", "classify_event_type", "summarise_event"]
