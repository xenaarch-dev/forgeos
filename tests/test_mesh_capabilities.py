"""
TDD: mesh capability adapters — Phase 2 of SPEC_AgentMesh.md.

ContractCapability adapts LegalAgent's bespoke run(ctx, output_dir) signature;
OutreachCapability wraps OutreachForgeAgent, which is already a ForgeAgent.

The two load-bearing assertions, in the spec's words:
  - "one real end-to-end contract generation writing a file to a temp workdir"
    TestContractEndToEnd runs the adapter, LegalAgent, the compose step and the
    file writes for real, with only the HTTP transport stubbed so the run is
    deterministic. TestLiveContractGeneration does the same against the live
    Anthropic API, and is skipped without a working key.
  - "outreach path asserted to draft-only, never send"
    TestOutreachNeverSends asserts the negative directly: no mark_approved, no
    mark_sent, no status transition off 'drafted', no outbound HTTP.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import mesh.capabilities.outreach as outreach_module
from agents.legal_agent import LegalAgent
from agents.outreach import OutreachForgeAgent
from llm.claude import ClaudeClient
from mesh.capabilities.contract import ContractCapability
from mesh.capabilities.outreach import OutreachCapability
from mesh.models import (
    MESH_ARGS_KEY,
    ArtifactStatus,
    ArtifactType,
    Capability,
    MeshArtifact,
)
from mesh.registry import CapabilityRegistry, default_registry
from models import LLMResponse, ProjectContext
from models.outputs.legal_output import ProductContext
from tests.conftest import skip_no_claude


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INDIA_LAW = (
    "This agreement is governed by the Indian Contract Act 1872 and the "
    "Information Technology Act 2000 (as amended 2008). Exclusive jurisdiction "
    "of the Courts of Mumbai, Maharashtra. DPDP Act 2023 compliance applies to "
    "all personal data. Consumer Protection Act 2019 rights are preserved. "
)


def _doc(kind: str) -> str:
    """A distinct, valid document per call so the fold can be checked per part."""
    return (
        f"## {kind} DOCUMENT\n\n"
        f"UNIQUE-MARKER-{kind}\n\n" + _INDIA_LAW + f"{kind} clause text. " * 120
    )


def _fake_complete(self, messages, system=None, **kwargs):
    prompt = messages[0]["content"]
    if "Terms and Conditions" in prompt:
        kind = "TERMS"
    elif "Privacy Policy" in prompt:
        kind = "PRIVACY"
    else:
        kind = "REFUND"
    return LLMResponse(text=_doc(kind), model="test")


def _ctx(tmp_path: Path, idea: str, args: dict | None = None) -> ProjectContext:
    ctx = ProjectContext.new(idea=idea, workdir=str(tmp_path))
    if args:
        ctx.metadata[MESH_ARGS_KEY] = args
    return ctx


def _mock_supabase() -> MagicMock:
    client = MagicMock()
    ok = MagicMock()
    ok.error = None
    ok.data = [{"id": "uuid-1", "status": "drafted"}]
    client.table.return_value.insert.return_value.execute.return_value = ok
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = ok
    return client


# ---------------------------------------------------------------------------
# ContractCapability — real end-to-end run
# ---------------------------------------------------------------------------


class TestContractEndToEnd:
    """Adapter, LegalAgent, compose and disk writes all execute for real."""

    @pytest.fixture(autouse=True)
    def stub_transport(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
        monkeypatch.setattr(ClaudeClient, "complete", _fake_complete)

    @pytest.fixture
    def run(self, tmp_path):
        ctx = _ctx(tmp_path, "Generate the legal pack for Acme Legal")
        result = ContractCapability().run(ctx)
        assert result.status == "success", f"adapter failed: {result.error}"
        return result

    def test_run_succeeds(self, run):
        assert run.status == "success"

    def test_writes_the_artifact_to_the_workdir(self, run, tmp_path):
        artifact_file = tmp_path / "artifacts" / "contract.md"
        assert artifact_file.exists()
        assert artifact_file.stat().st_size > 0

    def test_declared_capability_matches_the_path_actually_written(self, run, tmp_path):
        for relpath in ContractCapability.capabilities:
            assert (tmp_path / relpath).exists(), f"declared but not written: {relpath}"

    def test_legal_agents_own_documents_are_kept_on_disk(self, run, tmp_path):
        legal = tmp_path / "artifacts" / "legal"
        assert (legal / "terms.md").exists()
        assert (legal / "privacy.md").exists()
        assert (legal / "refund.md").exists()

    def test_artifact_body_folds_in_all_three_documents_verbatim(self, run, tmp_path):
        body = (tmp_path / "artifacts" / "contract.md").read_text(encoding="utf-8")
        for kind in ("TERMS", "PRIVACY", "REFUND"):
            assert f"UNIQUE-MARKER-{kind}" in body, f"{kind} missing from the fold"

    def test_folded_text_is_not_rewritten(self, run, tmp_path):
        """ContractForge's proven prompts are reused verbatim, not paraphrased."""
        body = (tmp_path / "artifacts" / "contract.md").read_text(encoding="utf-8")
        terms = (tmp_path / "artifacts" / "legal" / "terms.md").read_text(encoding="utf-8")
        assert terms.strip() in body

    def test_artifact_is_pending_not_approved(self, run):
        assert run.output["artifact"]["status"] == ArtifactStatus.PENDING.value

    def test_artifact_type_is_contract(self, run):
        assert run.output["artifact"]["artifact_type"] == ArtifactType.CONTRACT.value

    def test_output_reports_the_artifact_path(self, run, tmp_path):
        assert run.output["artifact_path"] == str(tmp_path / "artifacts" / "contract.md")

    def test_artifact_ready_event_is_emitted(self, tmp_path):
        seen: list[tuple[str, dict]] = []
        ctx = _ctx(tmp_path, "Generate the legal pack for Acme Legal")
        ContractCapability(event_callback=lambda e, p: seen.append((e, p))).run(ctx)
        events = {e for e, _ in seen}
        assert "artifact_ready" in events
        payload = next(p for e, p in seen if e == "artifact_ready")
        # Not "type": that key is the SSE envelope's shape discriminator in
        # api.py, so a payload field of the same name would overwrite it.
        assert payload["artifact_type"] == "CONTRACT"
        assert payload["preview"]

    def test_india_law_content_survives_the_adapter(self, run, tmp_path):
        body = (tmp_path / "artifacts" / "contract.md").read_text(encoding="utf-8")
        lowered = body.lower()
        assert "indian contract act 1872" in lowered
        assert "dpdp act 2023" in lowered
        assert "mumbai" in lowered


class TestContractCallsLegalAgentUnmodified:
    """The adapter absorbs the bespoke signature; legal_agent.py stays untouched."""

    @pytest.fixture(autouse=True)
    def stub_transport(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
        monkeypatch.setattr(ClaudeClient, "complete", _fake_complete)

    def test_legal_agent_is_called_with_its_own_signature(self, tmp_path):
        with patch.object(LegalAgent, "run", wraps=LegalAgent().run) as spy:
            ContractCapability().run(_ctx(tmp_path, "legal pack for Acme"))
        assert spy.call_count == 1
        product_ctx = spy.call_args.args[0]
        assert isinstance(product_ctx, ProductContext)
        assert "output_dir" in spy.call_args.kwargs

    def test_legal_agent_output_dir_is_inside_the_command_workdir(self, tmp_path):
        with patch.object(LegalAgent, "run", wraps=LegalAgent().run) as spy:
            ContractCapability().run(_ctx(tmp_path, "legal pack for Acme"))
        output_dir = Path(spy.call_args.kwargs["output_dir"]).resolve()
        assert output_dir.is_relative_to(tmp_path.resolve())

    def test_legal_agent_remains_a_plain_class_not_a_forgeagent(self):
        from forge_sdk.agent import ForgeAgent

        assert not issubclass(LegalAgent, ForgeAgent)

    def test_legal_agent_failure_fails_the_capability(self, tmp_path):
        from models import AgentResult, AgentStatus

        failed = AgentResult.started("legal_agent")
        failed.finalize(AgentStatus.FAILED, error="boom")
        with patch.object(LegalAgent, "run", return_value=failed):
            result = ContractCapability().run(_ctx(tmp_path, "legal pack for Acme"))
        assert result.status == "failed"
        assert "boom" in result.error


class TestContractNormalisation:
    def test_product_name_derived_from_the_command(self):
        assert ContractCapability._derive_product_name(
            "generate the legal pack for Acme Legal"
        ) == "Acme Legal"

    def test_product_name_falls_back_to_contractforge(self):
        assert ContractCapability._derive_product_name("draft an NDA") == "ContractForge"

    def test_args_override_the_derivation(self, tmp_path):
        ctx = _ctx(tmp_path, "legal pack for Acme", {"product_name": "Zephyr"})
        product = ContractCapability()._product_context(ctx, {"product_name": "Zephyr"})
        assert product.product_name == "Zephyr"

    def test_contact_email_defaults_from_the_domain(self, tmp_path):
        ctx = _ctx(tmp_path, "legal pack")
        product = ContractCapability()._product_context(ctx, {"domain": "acme.in"})
        assert product.contact_email == "legal@acme.in"

    def test_comma_separated_args_become_lists(self, tmp_path):
        ctx = _ctx(tmp_path, "legal pack")
        product = ContractCapability()._product_context(
            ctx, {"data_collected": "email, phone , GST"}
        )
        assert product.data_collected == ["email", "phone", "GST"]

    def test_declares_the_spec_metadata(self):
        assert ContractCapability.name == "contract_capability"
        assert ContractCapability.phase == "mesh"
        assert ContractCapability.requires == ["idea"]
        assert ContractCapability.budget_usd == 0.35


# ---------------------------------------------------------------------------
# OutreachCapability — the negative is the point
# ---------------------------------------------------------------------------


class _OutreachHarness:
    """Shared fixtures: Claude stubbed, Supabase mocked, Discord disarmed."""

    @pytest.fixture(autouse=True)
    def stub_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
        monkeypatch.setattr(
            ClaudeClient,
            "complete",
            lambda *a, **kw: LLMResponse(text="  Saw your post about unpaid work.  ", model="test"),
        )

    @pytest.fixture
    def supabase(self, monkeypatch):
        client = _mock_supabase()
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test")
        monkeypatch.setattr(
            OutreachForgeAgent, "_supabase_client", staticmethod(lambda: client)
        )
        return client


class TestOutreachDrafts(_OutreachHarness):
    def test_run_succeeds(self, tmp_path, supabase):
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.status == "success", result.error

    def test_writes_the_artifact_to_the_workdir(self, tmp_path, supabase):
        OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert (tmp_path / "artifacts" / "outreach.md").exists()

    def test_draft_text_reaches_the_artifact(self, tmp_path, supabase):
        OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        body = (tmp_path / "artifacts" / "outreach.md").read_text(encoding="utf-8")
        assert "Saw your post about unpaid work." in body

    def test_artifact_type_is_email(self, tmp_path, supabase):
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.output["artifact"]["artifact_type"] == ArtifactType.EMAIL.value

    def test_queues_for_approval_when_supabase_is_configured(self, tmp_path, supabase):
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.output["queued_for_approval"] is True
        supabase.table.assert_called_with("outreach_leads")


class TestOutreachNeverSends(_OutreachHarness):
    """Drafts only. Every assertion here is a negative."""

    def test_never_calls_mark_approved(self, tmp_path, supabase):
        with patch.object(OutreachForgeAgent, "mark_approved") as approved:
            OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert approved.call_count == 0

    def test_never_calls_mark_sent(self, tmp_path, supabase):
        with patch.object(OutreachForgeAgent, "mark_sent") as sent:
            OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert sent.call_count == 0

    def test_row_is_inserted_at_status_drafted(self, tmp_path, supabase):
        OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        payload = supabase.table.return_value.insert.call_args.args[0]
        assert payload["status"] == "drafted"
        assert payload["status"] not in ("approved", "sent")

    def test_no_status_transition_is_attempted(self, tmp_path, supabase):
        """update() is how a row leaves 'drafted'. It must never be called here."""
        OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert supabase.table.return_value.update.call_count == 0

    def test_no_outbound_http_request_is_made(self, tmp_path, supabase):
        import httpx

        with patch.object(httpx.AsyncClient, "post", new=AsyncMock()) as post:
            OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert post.await_count == 0

    def test_artifact_is_pending(self, tmp_path, supabase):
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.output["artifact"]["status"] == ArtifactStatus.PENDING.value

    def test_output_states_the_invariant_explicitly(self, tmp_path, supabase):
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.output["sent"] is False
        assert result.output["approved"] is False

    def test_artifact_body_says_it_was_not_sent(self, tmp_path, supabase):
        OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        body = (tmp_path / "artifacts" / "outreach.md").read_text(encoding="utf-8")
        assert "NOT SENT" in body

    def test_adapter_has_no_send_call_site_at_all(self):
        """A structural pin on the hard rule: no call site can regress into one."""
        src = Path(outreach_module.__file__).read_text(encoding="utf-8")
        assert ".mark_approved(" not in src
        assert ".mark_sent(" not in src


class TestOutreachDegradesWithoutSupabase(_OutreachHarness):
    @pytest.fixture(autouse=True)
    def no_supabase(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    def test_still_produces_a_draft(self, tmp_path):
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.status == "success", result.error
        assert (tmp_path / "artifacts" / "outreach.md").exists()

    def test_reports_that_it_did_not_queue(self, tmp_path):
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.output["queued_for_approval"] is False
        assert "SUPABASE_URL" in result.output["queue_error"]

    def test_still_did_not_send(self, tmp_path):
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.output["sent"] is False

    def test_queue_failure_degrades_rather_than_losing_the_draft(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test")
        monkeypatch.setattr(
            OutreachForgeAgent,
            "queue_for_approval",
            lambda self, lead, draft: (_ for _ in ()).throw(RuntimeError("supabase down")),
        )
        result = OutreachCapability().run(_ctx(tmp_path, "draft outreach for CA firms"))
        assert result.status == "success"
        assert result.output["queued_for_approval"] is False
        assert "supabase down" in result.output["queue_error"]
        assert (tmp_path / "artifacts" / "outreach.md").exists()


class TestOutreachNormalisation(_OutreachHarness):
    def test_lead_name_derived_from_the_command(self, tmp_path):
        lead = OutreachCapability()._lead(_ctx(tmp_path, "draft outreach for CA firms"), {})
        assert lead["name"] == "CA firms"

    def test_fit_context_falls_back_to_the_founders_own_words(self, tmp_path):
        idea = "draft outreach for CA firms in Pune who file GST returns"
        lead = OutreachCapability()._lead(_ctx(tmp_path, idea), {})
        assert lead["fit_context"] == idea

    def test_args_win_over_derivation(self, tmp_path):
        args = {"name": "Rahul Sharma", "platform": "x", "handle": "@rahul_dev"}
        lead = OutreachCapability()._lead(_ctx(tmp_path, "draft outreach"), args)
        assert lead["name"] == "Rahul Sharma"
        assert lead["platform"] == "x"
        assert lead["handle"] == "@rahul_dev"

    def test_platform_defaults_to_email(self, tmp_path):
        lead = OutreachCapability()._lead(_ctx(tmp_path, "draft outreach"), {})
        assert lead["platform"] == "email"

    def test_declares_the_spec_metadata(self):
        assert OutreachCapability.name == "outreach_capability"
        assert OutreachCapability.phase == "mesh"
        assert OutreachCapability.budget_usd == 0.05


# ---------------------------------------------------------------------------
# MeshArtifact
# ---------------------------------------------------------------------------


class TestMeshArtifact:
    def _artifact(self, **kw) -> MeshArtifact:
        base = dict(
            agent="contract_capability",
            artifact_type=ArtifactType.CONTRACT,
            title="t",
            body="b" * 900,
            slug="contract",
        )
        base.update(kw)
        return MeshArtifact(**base)

    def test_defaults_to_pending(self):
        assert self._artifact().status is ArtifactStatus.PENDING

    def test_artifact_type_is_constrained(self):
        with pytest.raises(Exception):
            self._artifact(artifact_type="INVOICE")

    def test_status_is_constrained(self):
        with pytest.raises(Exception):
            self._artifact(status="shipped")

    def test_preview_truncates(self):
        preview = self._artifact().preview(limit=50)
        assert len(preview) <= 53
        assert preview.endswith("...")

    def test_preview_does_not_truncate_short_bodies(self):
        assert self._artifact(body="short").preview() == "short"

    def test_type_and_status_match_the_phase_7a_constraints(self):
        assert {t.value for t in ArtifactType} == {"CONTRACT", "SPEC", "EMAIL", "PROPOSAL"}
        assert {s.value for s in ArtifactStatus} == {
            "pending",
            "approved",
            "revision_requested",
            "rejected",
        }


# ---------------------------------------------------------------------------
# Registry — Phase 1 shipped it empty; Phase 2 binds two
# ---------------------------------------------------------------------------


class TestDefaultRegistry:
    def test_contract_and_outreach_are_bound(self):
        registry = default_registry()
        assert registry.get(Capability.CONTRACT) is ContractCapability
        assert registry.get(Capability.OUTREACH) is OutreachCapability

    def test_spec_and_build_are_not_bound_yet(self):
        registry = default_registry()
        assert registry.get(Capability.SPEC) is None
        assert registry.get(Capability.BUILD) is None
        assert registry.unregistered() == [Capability.SPEC, Capability.BUILD]

    def test_registers_classes_so_each_command_gets_its_own_instance(self):
        registry = default_registry()
        adapter_cls = registry.get(Capability.CONTRACT)
        assert isinstance(adapter_cls, type)
        assert adapter_cls() is not adapter_cls()

    def test_each_call_returns_a_fresh_registry(self):
        assert default_registry() is not default_registry()

    def test_empty_registry_still_available_for_callers_that_want_one(self):
        assert len(CapabilityRegistry()) == 0


# ---------------------------------------------------------------------------
# CLI — python3 -m mesh.run "<text>"
# ---------------------------------------------------------------------------


class TestMeshRunCLI:
    @pytest.fixture(autouse=True)
    def stub_transport(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
        monkeypatch.setattr(ClaudeClient, "complete", _fake_complete)

    def _run(self, tmp_path, *argv) -> int:
        from mesh.run import main

        return main([*argv, "--workdir", str(tmp_path)])

    def test_contract_command_runs_end_to_end_and_writes_a_file(self, tmp_path, capsys):
        code = self._run(tmp_path, "/contract", "for", "Acme", "Legal")
        out = capsys.readouterr().out
        assert code == 0
        assert (tmp_path / "artifacts" / "contract.md").exists()
        assert "Artifact:" in out
        assert "pending" in out

    def test_prints_the_routing_line(self, tmp_path, capsys):
        self._run(tmp_path, "/contract", "for", "Acme")
        out = capsys.readouterr().out
        assert "Routing to ContractForge." in out

    def test_dry_run_routes_without_dispatching(self, tmp_path, capsys):
        code = self._run(tmp_path, "--dry-run", "/contract", "for", "Acme")
        out = capsys.readouterr().out
        assert code == 0
        assert "dry run" in out
        assert not (tmp_path / "artifacts").exists()

    def test_unsupported_says_so_and_runs_nothing(self, tmp_path, capsys):
        code = self._run(tmp_path, "RUN MORNING METRICS")
        out = capsys.readouterr().out
        assert code == 0
        assert "Nothing ran." in out
        assert not (tmp_path / "artifacts").exists()

    def test_empty_command_asks_a_question(self, tmp_path, capsys):
        code = self._run(tmp_path, "")
        out = capsys.readouterr().out
        assert code == 0
        assert "?" in out

    def test_unwired_capability_exits_2(self, tmp_path, capsys):
        code = self._run(tmp_path, "/build", "a", "waitlist", "page")
        out = capsys.readouterr().out
        assert code == 2
        assert "no adapter wired yet" in out

    def test_capability_failure_exits_1(self, tmp_path, capsys):
        with patch.object(LegalAgent, "run", side_effect=RuntimeError("kaboom")):
            code = self._run(tmp_path, "/contract", "for", "Acme")
        assert code == 1
        assert "FAILED" in capsys.readouterr().out

    def test_route_args_reach_the_capability(self, tmp_path):
        from mesh.run import main

        with patch.object(ContractCapability, "run", return_value=MagicMock(status="success", output={})) as run:
            main(["/contract", "for", "Acme", "--workdir", str(tmp_path)])
        ctx = run.call_args.args[0]
        assert ctx.metadata[MESH_ARGS_KEY] == {"idea": "for Acme"}


# ---------------------------------------------------------------------------
# Live generation — real Anthropic calls. Skipped without a working key.
# ---------------------------------------------------------------------------


@skip_no_claude
class TestLiveContractGeneration:
    def test_real_contract_generation_writes_a_real_file(self, tmp_path):
        result = ContractCapability().run(
            _ctx(tmp_path, "Generate the legal pack for ContractForge")
        )
        assert result.status == "success", result.error

        artifact_file = tmp_path / "artifacts" / "contract.md"
        assert artifact_file.exists()
        body = artifact_file.read_text(encoding="utf-8")
        assert len(body) > 4500

        lowered = body.lower()
        assert "dpdp" in lowered or "digital personal data protection" in lowered
        assert "[INSERT" not in body
        assert "PLACEHOLDER" not in body.upper()
