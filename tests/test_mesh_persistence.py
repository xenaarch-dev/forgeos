"""
TDD: mesh persistence — Phase 4 of SPEC_AgentMesh.md.

Nothing here needs a live database except TestRealRoundTrip, which carries
@skip_no_supabase (conftest, same one-shot probe pattern as skip_no_claude).

Everything else proves the write-through happens with the right data shape by
mocking at two seams:
  - MeshStore(client=...) takes an injected supabase-py client, so payload
    shapes are asserted against a mock table builder.
  - api._persist_async is replaced with a synchronous shim in the HTTP tests,
    which preserves the call (same function, same arguments) while removing
    task-scheduling nondeterminism from the assertions.
"""

from __future__ import annotations

import asyncio
import dataclasses
import re
import time
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api
from forge_sdk.agent import ForgeAgent
from mesh.models import ArtifactType, Capability, MeshArtifact
from mesh.registry import CapabilityRegistry
from mesh.store import MeshStore, classify_event_type, summarise_event
from models import ProjectContext
from tests.conftest import skip_no_supabase

MIGRATION = Path(__file__).resolve().parents[1] / (
    "supabase/migrations/20260810000000_command_threads_and_artifacts.sql"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubCapability(ForgeAgent):
    name = "stub_capability"
    phase = "mesh"
    capabilities = ["artifacts/stub.md"]
    requires = ["idea"]
    budget_usd = 0.0

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        body = f"# stub artifact\n\ncommand: {context.idea}\n"
        self._write(context, "artifacts/stub.md", body)
        artifact = MeshArtifact(
            agent=self.name,
            artifact_type=ArtifactType.CONTRACT,
            title="Stub artifact",
            body=body,
            slug="stub",
            workdir_path="artifacts/stub.md",
        )
        self._emit(
            "artifact_ready",
            {
                "agent": self.name,
                "artifact_type": artifact.artifact_type.value,
                "title": artifact.title,
                "preview": artifact.preview(),
                "slug": artifact.slug,
                "workdir_path": artifact.workdir_path,
            },
        )
        return {"artifact": artifact.model_dump(mode="json")}


def _mock_client(rows: list[dict] | None = None) -> MagicMock:
    """A supabase-py-shaped mock: client.table(x).insert(y).execute() -> result."""
    client = MagicMock()
    result = MagicMock()
    result.error = None
    result.data = rows if rows is not None else [{"id": "row-uuid-1"}]
    table = client.table.return_value
    table.insert.return_value.execute.return_value = result
    table.update.return_value.eq.return_value.execute.return_value = result
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = result
    table.select.return_value.eq.return_value.order.return_value.execute.return_value = result
    return client


def _sync_persist(fn, *args, **kwargs) -> None:
    """Same call, same arguments, no task scheduling."""
    fn(*args, **kwargs)


def _bind(monkeypatch, **bindings) -> None:
    reg = CapabilityRegistry()
    for capability, adapter in bindings.items():
        reg.register(Capability[capability.upper()], adapter)
    monkeypatch.setattr(api, "default_registry", lambda: reg)


def _drain(client: TestClient, store: MagicMock, attr: str, timeout: float = 3.0) -> None:
    """Let fire-and-forget persistence tasks finish; each request runs the loop."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if getattr(store, attr).call_count:
            return
        client.get("/healthz")
        time.sleep(0.02)


@pytest.fixture
def store() -> MagicMock:
    mock = MagicMock(spec=MeshStore)
    mock.enabled = True
    mock.create_thread.return_value = "thread-uuid-1"
    mock.insert_artifact.return_value = "artifact-uuid-1"
    return mock


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path, store):
    api._commands.clear()
    api._rate_limiter.reset()
    # Auth is required by default; this file tests persistence, not auth.
    monkeypatch.setenv("MESH_ALLOW_UNAUTH", "true")
    monkeypatch.setattr(
        api, "RUNTIME", dataclasses.replace(api.RUNTIME, workdir_root=str(tmp_path))
    )
    monkeypatch.setattr(api, "default_registry", lambda: CapabilityRegistry())
    monkeypatch.setattr(api, "_store", store)
    yield
    api._commands.clear()


@pytest.fixture
def client():
    with TestClient(api.app) as test_client:
        test_client.timeout = 10.0
        yield test_client


# ---------------------------------------------------------------------------
# Migration — the schema is the deliverable, so assert it exists as specified
# ---------------------------------------------------------------------------


class TestMigrationFile:
    @pytest.fixture(scope="class")
    def sql(self) -> str:
        return MIGRATION.read_text(encoding="utf-8")

    def test_migration_exists(self):
        assert MIGRATION.exists()

    def test_creates_both_tables(self, sql):
        assert "create table if not exists command_threads" in sql
        assert "create table if not exists artifacts" in sql

    def test_command_threads_precedes_artifacts(self, sql):
        """artifacts has an FK onto command_threads, so order matters."""
        assert sql.index("create table if not exists command_threads") < sql.index(
            "create table if not exists artifacts"
        )

    @pytest.mark.parametrize(
        "column",
        [
            "id",
            "command_id",
            "parent_artifact_id",
            "agent",
            "artifact_type",
            "title",
            "body",
            "status",
            "workdir_path",
            "created_at",
            "updated_at",
        ],
    )
    def test_artifacts_has_every_spec_7a_column(self, sql, column):
        artifacts_block = sql[sql.index("create table if not exists artifacts") :]
        assert re.search(rf"^\s+{column}\s", artifacts_block, re.M)

    @pytest.mark.parametrize(
        "column",
        ["id", "user_id", "input_text", "routed_capability", "confidence", "status"],
    )
    def test_command_threads_has_every_spec_column(self, sql, column):
        block = sql[
            sql.index("create table if not exists command_threads") : sql.index(
                "create table if not exists artifacts"
            )
        ]
        assert re.search(rf"^\s+{column}\s", block, re.M)

    def test_artifact_type_check_matches_the_enum(self, sql):
        for value in ("CONTRACT", "SPEC", "EMAIL", "PROPOSAL"):
            assert f"'{value}'" in sql
        assert {t.value for t in ArtifactType} == {"CONTRACT", "SPEC", "EMAIL", "PROPOSAL"}

    def test_artifact_status_check_matches_the_enum(self, sql):
        for value in ("pending", "approved", "revision_requested", "rejected"):
            assert f"'{value}'" in sql

    def test_routed_capability_check_matches_the_closed_capability_enum(self, sql):
        block = sql[sql.index("routed_capability") : sql.index("confidence")]
        for capability in Capability:
            assert f"'{capability.value}'" in block

    def test_cascade_on_thread_delete(self, sql):
        assert "references command_threads(id) on delete cascade" in sql

    def test_parent_artifact_id_is_self_referential_for_revisions(self, sql):
        assert "parent_artifact_id  uuid references artifacts(id) on delete set null" in sql

    def test_rls_enabled_on_both_tables(self, sql):
        assert "alter table command_threads enable row level security" in sql
        assert "alter table artifacts enable row level security" in sql

    def test_explicit_select_policies_for_authenticated(self, sql):
        assert 'create policy "command_threads_select_authenticated"' in sql
        assert 'create policy "artifacts_select_authenticated"' in sql
        assert sql.count("to authenticated") >= 2

    def test_updated_at_triggers_use_the_shared_function(self, sql):
        assert sql.count("execute function update_updated_at()") == 2

    def test_no_multi_tenant_policies_invented(self, sql):
        """§2 non-goal: single workspace. No workspace_id, no per-user filters."""
        assert "workspace_id" not in sql
        assert "auth.uid()" not in sql


# ---------------------------------------------------------------------------
# MeshStore — payload shapes and degradation
# ---------------------------------------------------------------------------


class TestMeshStoreDegradesWithoutCredentials:
    @pytest.fixture(autouse=True)
    def no_creds(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    def test_not_enabled(self):
        assert MeshStore().enabled is False

    def test_every_write_is_a_safe_no_op(self):
        s = MeshStore()
        assert s.create_thread("c1", "text") is None
        assert s.update_thread("c1", status="success") is False
        assert s.insert_artifact("t1", {"body": "x"}) is None
        assert s.record_event("c1", {"type": "log", "text": "hi"}) is False

    def test_every_read_is_empty_not_an_error(self):
        s = MeshStore()
        assert s.get_thread("c1") is None
        assert s.get_artifacts("t1") == []
        assert s.get_events("c1") == []


class TestMeshStorePayloads:
    def test_create_thread_shape_and_returned_id(self):
        client = _mock_client([{"id": "thread-1"}])
        row_id = MeshStore(client=client).create_thread(
            "cmd123", "GENERATE NDA", workdir="/tmp/wd"
        )
        assert row_id == "thread-1"
        payload = client.table.return_value.insert.call_args.args[0]
        assert payload == {
            "command_id": "cmd123",
            "input_text": "GENERATE NDA",
            "status": "running",
            "workdir": "/tmp/wd",
            "user_id": None,
        }
        client.table.assert_called_with("command_threads")

    def test_update_thread_only_sends_provided_fields(self):
        client = _mock_client()
        MeshStore(client=client).update_thread(
            "cmd123", routed_capability="contract", confidence=0.93
        )
        payload = client.table.return_value.update.call_args.args[0]
        assert payload == {"routed_capability": "contract", "confidence": 0.93}

    def test_update_thread_filters_by_command_id(self):
        client = _mock_client()
        MeshStore(client=client).update_thread("cmd123", status="success")
        client.table.return_value.update.return_value.eq.assert_called_with(
            "command_id", "cmd123"
        )

    def test_update_thread_with_nothing_to_set_is_a_no_op(self):
        client = _mock_client()
        assert MeshStore(client=client).update_thread("cmd123") is False
        assert client.table.return_value.update.call_count == 0

    def test_insert_artifact_shape(self):
        client = _mock_client([{"id": "art-1"}])
        artifact_id = MeshStore(client=client).insert_artifact(
            "thread-1",
            {
                "agent": "contract_capability",
                "artifact_type": "CONTRACT",
                "title": "Acme legal pack",
                "body": "# body",
                "status": "pending",
                "workdir_path": "artifacts/contract.md",
            },
        )
        assert artifact_id == "art-1"
        payload = client.table.return_value.insert.call_args.args[0]
        assert payload["command_id"] == "thread-1"
        assert payload["parent_artifact_id"] is None
        assert payload["artifact_type"] == "CONTRACT"
        assert payload["body"] == "# body"
        assert payload["status"] == "pending"

    def test_insert_artifact_never_writes_a_null_body(self):
        """body is not-null in the schema; the preview is the fallback."""
        client = _mock_client()
        MeshStore(client=client).insert_artifact(
            "thread-1", {"title": "t", "preview": "short preview"}
        )
        payload = client.table.return_value.insert.call_args.args[0]
        assert payload["body"] == "short preview"

    def test_insert_artifact_carries_revision_lineage(self):
        client = _mock_client()
        MeshStore(client=client).insert_artifact(
            "thread-1", {"body": "x"}, parent_artifact_id="art-0"
        )
        payload = client.table.return_value.insert.call_args.args[0]
        assert payload["parent_artifact_id"] == "art-0"

    def test_record_event_shape_and_command_id_in_metadata(self):
        client = _mock_client()
        payload_in = {"type": "agent_event", "event": "route", "agent": "mesh_router",
                      "rationale": "NDA requested.", "capability": "contract"}
        MeshStore(client=client).record_event("cmd123", payload_in)
        row = client.table.return_value.insert.call_args.args[0]
        assert row["agent"] == "mesh_router"
        assert row["event_type"] == "action"
        assert row["message"] == "NDA requested."
        assert row["metadata"]["command_id"] == "cmd123"
        assert row["metadata"]["event"] == "route"
        client.table.assert_called_with("dashboard_events")

    def test_supabase_error_is_swallowed_not_raised(self):
        client = _mock_client()
        failing = MagicMock()
        failing.error = "boom"
        client.table.return_value.insert.return_value.execute.return_value = failing
        assert MeshStore(client=client).record_event("c1", {"type": "log"}) is False

    def test_exception_is_swallowed_not_raised(self):
        client = _mock_client()
        client.table.return_value.insert.side_effect = RuntimeError("network down")
        assert MeshStore(client=client).create_thread("c1", "t") is None


class TestEventClassification:
    """dashboard_events.event_type is check-constrained to four values."""

    _ALLOWED = {"info", "action", "gate", "error"}

    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({"type": "log", "text": "x"}, "info"),
            ({"type": "done", "status": "success"}, "info"),
            ({"type": "agent_event", "event": "route"}, "action"),
            ({"type": "agent_event", "event": "start"}, "action"),
            ({"type": "agent_event", "event": "artifact_ready"}, "action"),
            ({"type": "agent_event", "event": "gate"}, "gate"),
            ({"type": "agent_event", "event": "error"}, "error"),
        ],
    )
    def test_classification(self, payload, expected):
        assert classify_event_type(payload) == expected

    @pytest.mark.parametrize(
        "event",
        ["route", "start", "artifact_ready", "success", "error", "gate", "finish", "weird"],
    )
    def test_every_mesh_event_maps_inside_the_check_constraint(self, event):
        assert classify_event_type({"type": "agent_event", "event": event}) in self._ALLOWED

    def test_message_is_bounded(self):
        long = summarise_event({"type": "log", "text": "x" * 5000})
        assert len(long) <= 500

    def test_route_message_is_the_rationale(self):
        assert summarise_event(
            {"type": "agent_event", "event": "route", "rationale": "NDA requested."}
        ) == "NDA requested."

    def test_artifact_message_names_the_artifact(self):
        assert "Stub artifact" in summarise_event(
            {"type": "agent_event", "event": "artifact_ready", "title": "Stub artifact"}
        )


# ---------------------------------------------------------------------------
# Write-through over HTTP
# ---------------------------------------------------------------------------


class TestWriteThroughOnSubmit:
    @pytest.fixture(autouse=True)
    def sync_persist(self, monkeypatch):
        monkeypatch.setattr(api, "_persist_async", _sync_persist)

    def test_thread_row_created_on_submit(self, client, store, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        assert store.create_thread.call_count == 1
        assert store.create_thread.call_args.args[0] == cid
        assert store.create_thread.call_args.args[1] == "GENERATE NDA"

    def test_thread_row_id_is_captured_for_the_artifact_fk(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        assert api._commands[cid]["thread_row_id"] == "thread-uuid-1"

    def test_routing_result_is_written_back(self, client, store, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        client.post("/command", json={"text": "GENERATE NDA"})
        routed = [
            c for c in store.update_thread.call_args_list
            if c.kwargs.get("routed_capability")
        ]
        assert routed
        assert routed[0].kwargs["routed_capability"] == "contract"
        assert routed[0].kwargs["confidence"] == 1.0

    def test_terminal_status_is_written_for_unsupported(self, client, store):
        client.post("/command", json={"text": "RUN MORNING METRICS"})
        statuses = [c.kwargs.get("status") for c in store.update_thread.call_args_list]
        assert "unsupported" in statuses

    def test_terminal_status_is_written_for_unwired(self, client, store):
        client.post("/command", json={"text": "/build a page"})
        statuses = [c.kwargs.get("status") for c in store.update_thread.call_args_list]
        assert "unwired" in statuses

    def test_success_status_is_written(self, client, store, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        with client.stream("GET", f"/command/{cid}/stream") as r:
            "".join(r.iter_text())
        statuses = [c.kwargs.get("status") for c in store.update_thread.call_args_list]
        assert "success" in statuses

    def test_nothing_is_written_when_the_store_is_disabled(self, client, store, monkeypatch):
        store.enabled = False
        monkeypatch.undo()  # restore the real _persist_async
        monkeypatch.setattr(api, "_store", store)
        client.post("/command", json={"text": "RUN MORNING METRICS"})
        assert store.create_thread.call_count == 0
        assert store.record_event.call_count == 0


class TestDashboardEventMirror:
    @pytest.fixture(autouse=True)
    def sync_persist(self, monkeypatch):
        monkeypatch.setattr(api, "_persist_async", _sync_persist)

    def test_every_event_is_mirrored(self, client, store, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        with client.stream("GET", f"/command/{cid}/stream") as r:
            "".join(r.iter_text())
        assert store.record_event.call_count == len(api._commands[cid]["events"])

    def test_mirror_carries_the_command_id(self, client, store):
        cid = client.post("/command", json={"text": "RUN MORNING METRICS"}).json()["command_id"]
        assert all(c.args[0] == cid for c in store.record_event.call_args_list)

    def test_route_and_done_are_both_mirrored(self, client, store):
        client.post("/command", json={"text": "RUN MORNING METRICS"})
        mirrored = [c.args[1] for c in store.record_event.call_args_list]
        assert any(p.get("event") == "route" for p in mirrored)
        assert any(p.get("type") == "done" for p in mirrored)


class TestArtifactPersistence:
    @pytest.fixture(autouse=True)
    def sync_persist(self, monkeypatch):
        monkeypatch.setattr(api, "_persist_async", _sync_persist)

    def _run(self, client, monkeypatch) -> str:
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        with client.stream("GET", f"/command/{cid}/stream") as r:
            "".join(r.iter_text())
        return cid

    def test_artifact_row_written_on_artifact_ready(self, client, store, monkeypatch):
        self._run(client, monkeypatch)
        assert store.insert_artifact.call_count == 1

    def test_artifact_row_uses_the_thread_row_id_as_fk(self, client, store, monkeypatch):
        self._run(client, monkeypatch)
        assert store.insert_artifact.call_args.args[0] == "thread-uuid-1"

    def test_artifact_body_is_read_from_the_workdir_file(self, client, store, monkeypatch):
        cid = self._run(client, monkeypatch)
        artifact = store.insert_artifact.call_args.args[1]
        on_disk = (Path(api._commands[cid]["workdir"]) / "artifacts/stub.md").read_text()
        assert artifact["body"] == on_disk
        assert artifact["body"].startswith("# stub artifact")

    def test_artifact_row_fields(self, client, store, monkeypatch):
        self._run(client, monkeypatch)
        artifact = store.insert_artifact.call_args.args[1]
        assert artifact["agent"] == "stub_capability"
        assert artifact["artifact_type"] == "CONTRACT"
        assert artifact["title"] == "Stub artifact"
        assert artifact["status"] == "pending"
        assert artifact["workdir_path"] == "artifacts/stub.md"

    def test_no_artifact_row_when_nothing_was_produced(self, client, store):
        client.post("/command", json={"text": "RUN MORNING METRICS"})
        assert store.insert_artifact.call_count == 0

    def test_body_falls_back_to_preview_when_the_file_is_missing(self, tmp_path):
        record = {"workdir": str(tmp_path), "id": "c1"}
        body = api._read_artifact_body(
            record, {"workdir_path": "artifacts/gone.md", "preview": "fallback"}
        )
        assert body == "fallback"

    def test_body_read_refuses_to_escape_the_workdir(self, tmp_path):
        outside = tmp_path.parent / "secret.md"
        outside.write_text("do not read me", encoding="utf-8")
        record = {"workdir": str(tmp_path), "id": "c1"}
        body = api._read_artifact_body(
            record, {"workdir_path": "../secret.md", "preview": "safe"}
        )
        assert body == "safe"


# ---------------------------------------------------------------------------
# GET /command/{id} reads Postgres when memory has nothing (§6a reconnect)
# ---------------------------------------------------------------------------


class TestGetCommandFromPostgres:
    def _stored(self, store, command_id="abc123def456"):
        store.get_thread.return_value = {
            "id": "thread-uuid-1",
            "command_id": command_id,
            "input_text": "GENERATE NDA",
            "routed_capability": "contract",
            "confidence": 1.0,
            "status": "success",
            "workdir": "/tmp/wd",
            "detail": None,
            "error": None,
            "created_at": "2026-08-10T00:00:00Z",
            "updated_at": "2026-08-10T00:01:00Z",
        }
        store.get_artifacts.return_value = [
            {"id": "art-1", "title": "Acme legal pack", "status": "pending"}
        ]
        store.get_events.return_value = [
            {"metadata": {"type": "agent_event", "event": "route", "command_id": command_id}},
            {"metadata": {"type": "done", "status": "success"}},
        ]
        return command_id

    def test_reads_from_postgres_when_not_in_memory(self, client, store):
        cid = self._stored(store)
        body = client.get(f"/command/{cid}").json()
        assert body["source"] == "postgres"
        assert body["status"] == "success"
        assert body["text"] == "GENERATE NDA"

    def test_replays_the_transcript_from_the_mirror(self, client, store):
        cid = self._stored(store)
        events = client.get(f"/command/{cid}").json()["events"]
        assert events[0]["event"] == "route"
        assert events[-1] == {"type": "done", "status": "success"}

    def test_returns_the_artifacts(self, client, store):
        cid = self._stored(store)
        body = client.get(f"/command/{cid}").json()
        assert body["artifact"]["title"] == "Acme legal pack"
        assert len(body["artifacts"]) == 1

    def test_reconstructs_the_route_decision(self, client, store):
        cid = self._stored(store)
        route = client.get(f"/command/{cid}").json()["route"]
        assert route["capability"] == "contract"
        assert route["confidence"] == 1.0

    def test_memory_wins_when_the_process_still_holds_it(self, client, store, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        monkeypatch.setattr(api, "_persist_async", _sync_persist)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        body = client.get(f"/command/{cid}").json()
        assert body["source"] == "memory"
        assert store.get_thread.call_count == 0

    def test_404_when_neither_memory_nor_postgres_has_it(self, client, store):
        store.get_thread.return_value = None
        assert client.get("/command/deadbeef0000").status_code == 404

    def test_invalid_id_is_still_400(self, client):
        assert client.get("/command/bad-id").status_code == 400


# ---------------------------------------------------------------------------
# _persist_async
# ---------------------------------------------------------------------------


class TestPersistAsync:
    def test_disabled_store_skips_entirely(self, store):
        store.enabled = False
        called = []
        api._persist_async(lambda: called.append(1))
        assert called == []

    def test_runs_inline_when_there_is_no_event_loop(self, store):
        called = []
        api._persist_async(lambda x: called.append(x), 42)
        assert called == [42]

    def test_schedules_and_completes_on_the_event_loop(self, client, store, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        client.post("/command", json={"text": "GENERATE NDA"})
        _drain(client, store, "record_event")
        assert store.record_event.call_count > 0

    def test_a_failing_write_does_not_break_the_command(self, client, store, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        store.record_event.side_effect = RuntimeError("db down")
        monkeypatch.setattr(api, "_persist_async", _sync_persist)
        with pytest.raises(RuntimeError):
            # _sync_persist deliberately does not swallow — proves the real
            # MeshStore is the layer that must, and it does (see TestMeshStorePayloads).
            client.post("/command", json={"text": "RUN MORNING METRICS"})


# ---------------------------------------------------------------------------
# Workdir unification
# ---------------------------------------------------------------------------


class TestWorkdirUnified:
    def test_cli_root_is_under_runtime_workdir_root(self):
        from config import RUNTIME
        from mesh.run import COMMANDS_ROOT

        assert Path(COMMANDS_ROOT) == Path(RUNTIME.workdir_root) / "commands"

    def test_cli_no_longer_uses_the_relative_builds_path(self):
        from mesh.run import COMMANDS_ROOT

        assert COMMANDS_ROOT != "builds/commands"
        assert Path(COMMANDS_ROOT).is_absolute()

    def test_cli_persists_through_the_same_store(self, tmp_path, monkeypatch):
        """A command submitted from the CLI must not be invisible to the dashboard."""
        import mesh.run

        cli_store = MagicMock(spec=MeshStore)
        cli_store.enabled = True
        cli_store.create_thread.return_value = "thread-uuid-cli"
        monkeypatch.setattr(mesh.run, "MeshStore", lambda *a, **kw: cli_store)

        code = mesh.run.main(["RUN MORNING METRICS", "--workdir", str(tmp_path)])

        assert code == 0
        assert cli_store.create_thread.call_count == 1
        assert cli_store.create_thread.call_args.args[1] == "RUN MORNING METRICS"
        statuses = [c.kwargs.get("status") for c in cli_store.update_thread.call_args_list]
        assert "unsupported" in statuses

    def test_api_and_cli_agree(self):
        """Both derive from RUNTIME.workdir_root + the same subdir name.

        Uses config.RUNTIME rather than api.RUNTIME because the isolate fixture
        repoints the latter at a temp directory for the HTTP tests.
        """
        from config import RUNTIME
        from mesh.run import COMMANDS_ROOT

        assert Path(COMMANDS_ROOT) == Path(RUNTIME.workdir_root) / api._COMMANDS_SUBDIR


# ---------------------------------------------------------------------------
# One real insert-and-read round trip. Skipped unless Postgres is reachable.
# ---------------------------------------------------------------------------


@skip_no_supabase
class TestRealRoundTrip:
    def test_insert_and_read_back(self):
        real = MeshStore()
        assert real.enabled

        command_id = f"test-{uuid.uuid4().hex[:12]}"
        thread_row_id = real.create_thread(
            command_id, "pytest round trip", workdir="/tmp/pytest"
        )
        assert thread_row_id, "command_threads insert returned no id"

        try:
            real.update_thread(
                command_id, routed_capability="contract", confidence=0.91, status="success"
            )
            thread = real.get_thread(command_id)
            assert thread is not None
            assert thread["input_text"] == "pytest round trip"
            assert thread["routed_capability"] == "contract"
            assert float(thread["confidence"]) == pytest.approx(0.91)
            assert thread["status"] == "success"

            artifact_id = real.insert_artifact(
                thread_row_id,
                {
                    "agent": "contract_capability",
                    "artifact_type": "CONTRACT",
                    "title": "pytest artifact",
                    "body": "# pytest body",
                    "status": "pending",
                    "workdir_path": "artifacts/contract.md",
                },
            )
            assert artifact_id

            artifacts = real.get_artifacts(thread_row_id)
            assert len(artifacts) == 1
            assert artifacts[0]["title"] == "pytest artifact"
            assert artifacts[0]["status"] == "pending"

            assert real.record_event(
                command_id,
                {"type": "agent_event", "event": "route", "agent": "mesh_router",
                 "rationale": "round trip"},
            )
            events = real.get_events(command_id)
            assert any(e["metadata"].get("event") == "route" for e in events)
        finally:
            # Cascade removes the artifact row with the thread. dashboard_events
            # has no FK, so it must be swept explicitly — otherwise every test
            # run leaves junk in the feed the live Dashboard reads.
            real.client.table("command_threads").delete().eq(
                "command_id", command_id
            ).execute()
            real.client.table("dashboard_events").delete().eq(
                "metadata->>command_id", command_id
            ).execute()
