"""
TDD: mesh HTTP surface + SSE — Phase 3 of SPEC_AgentMesh.md.

Nothing here needs live API credit. Two techniques, both already used elsewhere
in this suite:

  - Prefilter-matched inputs (quick actions, slash commands) reach a routing
    decision with zero LLM calls, so the full POST -> stream -> done sequence
    runs end to end for real.
  - The LLM-classification path mocks MeshRouter._structured_llm, per the
    pattern in test_mesh_router.py.

Dispatch is always aimed at a stub capability. A module-level autouse fixture
replaces the registry with an empty one so a mistake in any single test can
never fire the real ContractCapability at the Anthropic API.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import api
from forge_sdk.agent import ForgeAgent
from mesh.models import ArtifactType, Capability, MeshArtifact, RouteDecision
from mesh.registry import CapabilityRegistry
from mesh.router import MeshRouter
from models import ProjectContext

WAITLIST = "Build a simple waitlist landing page for a productivity app"


# ---------------------------------------------------------------------------
# Stub capabilities — real ForgeAgents, no network
# ---------------------------------------------------------------------------


#: True if _execute ran on the event loop, False if it ran in a worker thread.
_RAN_ON_EVENT_LOOP: list[bool] = []


class _StubCapability(ForgeAgent):
    name = "stub_capability"
    phase = "mesh"
    capabilities = ["artifacts/stub.md"]
    requires = ["idea"]
    budget_usd = 0.0
    delay_seconds = 0.0

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        # A worker thread has no running loop; the event loop's thread does.
        try:
            asyncio.get_running_loop()
            _RAN_ON_EVENT_LOOP.append(True)
        except RuntimeError:
            _RAN_ON_EVENT_LOOP.append(False)

        if self.delay_seconds:
            time.sleep(self.delay_seconds)
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
            },
        )
        return {"artifact": artifact.model_dump(mode="json")}


class _SlowStubCapability(_StubCapability):
    name = "slow_stub_capability"
    delay_seconds = 0.25


class _FailingCapability(ForgeAgent):
    name = "failing_capability"
    phase = "mesh"
    capabilities: list[str] = []
    requires = ["idea"]
    budget_usd = 0.0

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        raise RuntimeError("stub failure")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registry(**bindings) -> CapabilityRegistry:
    reg = CapabilityRegistry()
    for capability, adapter in bindings.items():
        reg.register(Capability[capability.upper()], adapter)
    return reg


def _bind(monkeypatch, **bindings) -> None:
    reg = _registry(**bindings)
    monkeypatch.setattr(api, "default_registry", lambda: reg)


def _payloads(raw: str) -> list[dict]:
    return [json.loads(line[6:]) for line in raw.splitlines() if line.startswith("data: ")]


def _events_of(payloads: list[dict], name: str) -> list[dict]:
    return [p for p in payloads if p.get("type") == "agent_event" and p.get("event") == name]


def _stream(client: TestClient, command_id: str) -> tuple[int, list[dict]]:
    with client.stream("GET", f"/command/{command_id}/stream") as resp:
        if resp.status_code != 200:
            resp.read()
            return resp.status_code, []
        return resp.status_code, _payloads("".join(resp.iter_text()))


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    """Fresh command registry, temp workdir root, and NO real adapters bound."""
    api._commands.clear()
    _RAN_ON_EVENT_LOOP.clear()
    monkeypatch.setattr(
        api, "RUNTIME", dataclasses.replace(api.RUNTIME, workdir_root=str(tmp_path))
    )
    monkeypatch.setattr(api, "default_registry", lambda: CapabilityRegistry())
    yield
    api._commands.clear()


@pytest.fixture
def client():
    """One portal for the whole test.

    Without the context manager Starlette builds a fresh portal per request and
    tears it down on the way out, which orphans the asyncio.create_task that
    POST /command fires — the command would never leave `running` and the
    stream would keepalive forever. The read timeout turns any such hang into a
    fast failure instead of a stuck suite.
    """
    with TestClient(api.app) as test_client:
        test_client.timeout = 10.0
        yield test_client


# ---------------------------------------------------------------------------
# POST /command — routing decision comes back on the response (§5e)
# ---------------------------------------------------------------------------


class TestPostCommand:
    def test_quick_action_returns_201_with_the_real_decision(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        r = client.post("/command", json={"text": "GENERATE NDA"})
        assert r.status_code == 201
        body = r.json()
        assert body["route"]["capability"] == "contract"
        assert body["route"]["confidence"] == 1.0
        assert body["dispatched"] is True
        assert body["command_id"]

    def test_response_carries_the_spec_5e_shape(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        body = client.post("/command", json={"text": "GENERATE NDA"}).json()
        assert set(body) == {"command_id", "status", "route", "dispatched", "detail"}

    def test_prefilter_costs_zero_llm_calls_over_http(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        with patch.object(MeshRouter, "_structured_llm") as classify:
            client.post("/command", json={"text": "GENERATE NDA"})
        assert classify.call_count == 0

    def test_slash_command_routes_directly(self, client, monkeypatch):
        _bind(monkeypatch, outreach=_StubCapability)
        body = client.post("/command", json={"text": "/outreach for CA firms"}).json()
        assert body["route"]["capability"] == "outreach"
        assert body["route"]["args"] == {"idea": "for CA firms"}

    def test_rejects_empty_text(self, client):
        assert client.post("/command", json={"text": ""}).status_code == 422

    def test_rejects_oversized_text(self, client):
        r = client.post("/command", json={"text": "x" * 5000})
        assert r.status_code == 422

    def test_rejects_missing_field(self, client):
        assert client.post("/command", json={}).status_code == 422

    def test_workdir_is_server_controlled(self, client, monkeypatch, tmp_path):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        workdir = Path(api._commands[cid]["workdir"])
        assert workdir.is_relative_to(tmp_path)
        assert workdir.name == cid


class TestPostCommandTerminalOutcomes:
    def test_unsupported_does_not_dispatch(self, client):
        body = client.post("/command", json={"text": "RUN MORNING METRICS"}).json()
        assert body["route"]["capability"] == "unsupported"
        assert body["status"] == "unsupported"
        assert body["dispatched"] is False
        assert "Nothing ran." in body["detail"]

    def test_clarify_does_not_dispatch(self, client):
        body = client.post("/command", json={"text": "   "}).json()
        assert body["route"]["capability"] == "clarify"
        assert body["status"] == "clarify"
        assert body["dispatched"] is False
        assert body["detail"].count("?") == 1

    @pytest.mark.parametrize("text,capability", [("/build a waitlist page", "build"), ("/spec for an app", "spec")])
    def test_unwired_capability_does_not_crash_the_http_layer(self, client, text, capability):
        r = client.post("/command", json={"text": text})
        assert r.status_code == 201
        body = r.json()
        assert body["route"]["capability"] == capability
        assert body["status"] == "unwired"
        assert body["dispatched"] is False
        assert "no adapter wired yet" in body["detail"]

    def test_unwired_capability_still_routed_correctly(self, client):
        """Routing succeeds even with nothing bound — Phase 2 left these unbound."""
        body = client.post("/command", json={"text": "/build a waitlist page"}).json()
        assert body["route"]["args"] == {"idea": "a waitlist page"}
        assert body["route"]["confidence"] == 1.0


# ---------------------------------------------------------------------------
# GET /command/{id}/stream — the three shapes, plus the two new event names
# ---------------------------------------------------------------------------


class TestStream:
    def test_full_event_sequence_end_to_end(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        code, payloads = _stream(client, cid)
        assert code == 200
        names = [p.get("event") for p in payloads if p.get("type") == "agent_event"]
        assert "route" in names
        assert "start" in names
        assert "artifact_ready" in names
        assert "success" in names
        assert payloads[-1] == {"type": "done", "status": "success"}

    def test_only_the_three_documented_shapes_are_emitted(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        _, payloads = _stream(client, cid)
        assert {p["type"] for p in payloads} <= {"log", "agent_event", "done"}

    def test_route_event_payload(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        _, payloads = _stream(client, cid)
        route = _events_of(payloads, "route")[0]
        assert route["capability"] == "contract"
        assert route["confidence"] == 1.0
        assert route["rationale"]
        assert route["dispatch"] is True

    def test_artifact_ready_event_payload(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        _, payloads = _stream(client, cid)
        ready = _events_of(payloads, "artifact_ready")[0]
        assert ready["type"] == "agent_event", "envelope discriminator must survive"
        assert ready["artifact_type"] == "CONTRACT"
        assert ready["title"] == "Stub artifact"
        assert ready["preview"]

    def test_route_event_precedes_the_capability_start(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        _, payloads = _stream(client, cid)
        names = [p.get("event") for p in payloads if p.get("type") == "agent_event"]
        assert names.index("route") < names.index("start")

    def test_stream_opened_while_still_running_receives_the_terminal_done(
        self, client, monkeypatch
    ):
        _bind(monkeypatch, contract=_SlowStubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        assert api._commands[cid]["status"] == "running"
        code, payloads = _stream(client, cid)
        assert code == 200
        assert payloads[-1] == {"type": "done", "status": "success"}

    def test_failed_capability_streams_done_failed(self, client, monkeypatch):
        _bind(monkeypatch, contract=_FailingCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        code, payloads = _stream(client, cid)
        assert code == 200
        assert payloads[-1] == {"type": "done", "status": "failed"}
        assert _events_of(payloads, "error")

    def test_late_join_replays_the_whole_transcript(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        first = _stream(client, cid)[1]
        second = _stream(client, cid)[1]
        assert second == first

    def test_unknown_command_is_404(self, client):
        assert client.get("/command/deadbeef0000/stream").status_code == 404

    def test_invalid_command_id_is_400(self, client):
        assert client.get("/command/bad-id/stream").status_code == 400

    def test_path_traversal_never_reaches_the_handler(self, client):
        """Decodes to a slash, so routing 404s it before the id validator runs."""
        assert client.get("/command/..%2Fetc%2Fpasswd/stream").status_code == 404


class TestUnsupportedNeverOpensAStream:
    """§5e — on UNSUPPORTED the UI renders nothing further and never opens a stream."""

    def test_stream_is_refused_for_unsupported(self, client):
        cid = client.post("/command", json={"text": "RUN MORNING METRICS"}).json()["command_id"]
        code, payloads = _stream(client, cid)
        assert code == 409
        assert payloads == []

    def test_refusal_explains_that_nothing_ran(self, client):
        cid = client.post("/command", json={"text": "RUN MORNING METRICS"}).json()["command_id"]
        r = client.get(f"/command/{cid}/stream")
        assert "Nothing ran." in r.json()["detail"]

    def test_no_capability_is_run_for_unsupported(self, client):
        with patch.object(api, "_run_command") as runner:
            client.post("/command", json={"text": "RUN MORNING METRICS"})
        assert runner.call_count == 0

    def test_stream_is_refused_for_clarify(self, client):
        cid = client.post("/command", json={"text": "   "}).json()["command_id"]
        assert _stream(client, cid)[0] == 409

    def test_stream_is_refused_for_unwired_capability(self, client):
        cid = client.post("/command", json={"text": "/build a page"}).json()["command_id"]
        code, _ = _stream(client, cid)
        assert code == 409

    def test_unwired_refusal_does_not_500(self, client):
        r = client.get(
            f"/command/{client.post('/command', json={'text': '/spec x'}).json()['command_id']}/stream"
        )
        assert r.status_code == 409
        assert "no adapter wired yet" in r.json()["detail"]


# ---------------------------------------------------------------------------
# GET /command/{id} — transcript for reload / late join
# ---------------------------------------------------------------------------


class TestGetCommand:
    def test_returns_the_transcript(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        _stream(client, cid)
        body = client.get(f"/command/{cid}").json()
        assert body["id"] == cid
        assert body["text"] == "GENERATE NDA"
        assert body["status"] == "success"
        assert body["route"]["capability"] == "contract"
        assert body["events"]
        assert body["artifact"]["title"] == "Stub artifact"

    def test_transcript_matches_the_streamed_payloads(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        _, streamed = _stream(client, cid)
        assert client.get(f"/command/{cid}").json()["events"] == streamed

    def test_does_not_leak_the_asyncio_queue(self, client):
        cid = client.post("/command", json={"text": "RUN MORNING METRICS"}).json()["command_id"]
        assert "queue" not in client.get(f"/command/{cid}").json()

    def test_available_for_undispatched_commands_too(self, client):
        cid = client.post("/command", json={"text": "RUN MORNING METRICS"}).json()["command_id"]
        body = client.get(f"/command/{cid}").json()
        assert body["status"] == "unsupported"
        assert body["events"][-1] == {"type": "done", "status": "unsupported"}

    def test_unknown_command_is_404(self, client):
        assert client.get("/command/deadbeef0000").status_code == 404

    def test_invalid_id_is_400(self, client):
        assert client.get("/command/bad-id").status_code == 400


# ---------------------------------------------------------------------------
# The classification path, mocked (test_mesh_router.py pattern)
# ---------------------------------------------------------------------------


class TestClassifyPathOverHttp:
    def test_waitlist_input_classifies_to_build(self, client):
        decision = RouteDecision(
            capability=Capability.BUILD,
            confidence=0.93,
            rationale="Software to be built.",
            args={"idea": WAITLIST},
        )
        with patch.object(MeshRouter, "_structured_llm", return_value=decision) as classify:
            body = client.post("/command", json={"text": WAITLIST}).json()
        assert classify.call_count == 1
        assert body["route"]["capability"] == "build"
        assert body["status"] == "unwired"

    def test_classified_capability_dispatches_when_bound(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        decision = RouteDecision(
            capability=Capability.CONTRACT, confidence=0.9, rationale="NDA requested."
        )
        with patch.object(MeshRouter, "_structured_llm", return_value=decision):
            cid = client.post("/command", json={"text": "sort the paperwork"}).json()["command_id"]
        code, payloads = _stream(client, cid)
        assert code == 200
        assert payloads[-1] == {"type": "done", "status": "success"}

    def test_low_confidence_becomes_clarify_over_http(self, client):
        decision = RouteDecision(
            capability=Capability.CONTRACT, confidence=0.20, rationale="Not sure."
        )
        with patch.object(MeshRouter, "_structured_llm", return_value=decision):
            body = client.post("/command", json={"text": "do the thing"}).json()
        assert body["route"]["capability"] == "clarify"
        assert body["dispatched"] is False

    def test_classifier_failure_surfaces_as_500_not_a_hang(self, client):
        from models import LLMError

        with patch.object(MeshRouter, "_structured_llm", side_effect=LLMError("no key")):
            with pytest.raises(LLMError):
                client.post("/command", json={"text": "something ambiguous"})


# ---------------------------------------------------------------------------
# §5b — in-process, no subprocess
# ---------------------------------------------------------------------------


class TestRunsInProcess:
    def test_no_subprocess_is_spawned(self, client, monkeypatch):
        _bind(monkeypatch, contract=_StubCapability)
        with patch.object(asyncio, "create_subprocess_exec") as spawn:
            cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
            _stream(client, cid)
        assert spawn.call_count == 0

    def test_capability_runs_off_the_event_loop(self, client, monkeypatch):
        """A blocking ForgeAgent.run must go to a worker thread, not the loop.

        If it ran on the loop the SSE stream could not flush while it worked.
        """
        _bind(monkeypatch, contract=_StubCapability)
        cid = client.post("/command", json={"text": "GENERATE NDA"}).json()["command_id"]
        _stream(client, cid)
        assert _RAN_ON_EVENT_LOOP == [False]


# ---------------------------------------------------------------------------
# Regression — /builds is untouched
# ---------------------------------------------------------------------------


class TestBuildsEndpointsStillWork:
    def test_healthz(self, client):
        assert client.get("/healthz").json()["status"] == "ok"

    def test_list_builds(self, client):
        assert client.get("/builds").status_code == 200

    def test_build_stream_shapes_are_documented_unchanged(self):
        doc = api.stream_build.__doc__ or ""
        assert '{"type": "log"' in doc
        assert '{"type": "agent_event"' in doc
        assert '{"type": "done"' in doc

    def test_unknown_build_is_404(self, client):
        assert client.get("/builds/deadbeef0000").status_code == 404
