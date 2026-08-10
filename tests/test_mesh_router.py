"""
TDD: MeshRouter — Phase 1 of SPEC_AgentMesh.md (router as a pure library).

Unit tests (instant, no API): everything except TestLiveClassify.
Integration tests (skipped without a live Anthropic key): TestLiveClassify.

The load-bearing assertions, in the spec's own words:
  - the prefilter exact-matches all three quick actions with ZERO LLM calls
  - every confidence band (>=0.75, 0.45-0.75, <0.45) and UNSUPPORTED is asserted
  - "Build a simple waitlist landing page for a productivity app" — the input
    that exposed the bug — routes to BUILD, not silence
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mesh.models import (
    CLARIFY_THRESHOLD,
    DISPATCHABLE,
    DISPATCH_THRESHOLD,
    Capability,
    RouteDecision,
)
from mesh.registry import CapabilityRegistry
from mesh.router import ROUTER_STAGE, MeshRouter
from models import LLMError, ProjectContext
from tests.conftest import skip_no_claude


# The exact input from tonight's investigation. It contains no contract or
# outreach keyword, which is why a pure keyword table would go silent on it.
WAITLIST = "Build a simple waitlist landing page for a productivity app"

# web/app/app/command/page.tsx:20 — verbatim.
QUICK_ACTIONS = ["GENERATE NDA", "DRAFT OUTREACH FOR CA FIRMS", "RUN MORNING METRICS"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(tmp_path: Path, idea: str = WAITLIST) -> ProjectContext:
    return ProjectContext.new(idea=idea, workdir=str(tmp_path))


def _decision(capability: Capability, confidence: float, **kw) -> RouteDecision:
    kw.setdefault("rationale", "test rationale")
    return RouteDecision(capability=capability, confidence=confidence, **kw)


@contextmanager
def _no_llm():
    """Seal every LLM entry point the router could reach and record the calls.

    Patches all three seams, not just _structured_llm, so "zero LLM calls" is a
    claim about the process rather than about one mock.
    """
    with patch.object(MeshRouter, "_structured_llm") as structured, patch(
        "llm.claude.ClaudeClient.complete_structured"
    ) as claude_structured, patch("agents.base.llm_complete") as plain_complete:
        yield SimpleNamespace(
            structured=structured,
            claude_structured=claude_structured,
            plain_complete=plain_complete,
        )


def _assert_no_llm(calls: SimpleNamespace) -> None:
    assert calls.structured.call_count == 0, "_structured_llm was called"
    assert calls.claude_structured.call_count == 0, "ClaudeClient.complete_structured was called"
    assert calls.plain_complete.call_count == 0, "llm.router.complete was called"


@contextmanager
def _classifier(decision: RouteDecision):
    """Mock stage 2 so confidence-band policy can be tested deterministically."""
    with patch.object(MeshRouter, "_structured_llm", return_value=decision) as m:
        yield m


# ---------------------------------------------------------------------------
# Capability — the enum is closed
# ---------------------------------------------------------------------------


class TestCapabilityEnum:
    def test_exactly_six_members(self):
        assert len(Capability) == 6

    def test_member_values(self):
        assert {c.value for c in Capability} == {
            "contract",
            "outreach",
            "spec",
            "build",
            "clarify",
            "unsupported",
        }

    def test_no_capability_for_unbuilt_forges(self):
        """MeetingForge / ReputationForge / ClientForge have no backing code.
        The enum must make routing to them structurally impossible."""
        values = {c.value for c in Capability}
        for absent in ("meeting", "reputation", "client", "gbrain", "metrics"):
            assert absent not in values

    def test_dispatchable_excludes_terminal_outcomes(self):
        assert Capability.CLARIFY not in DISPATCHABLE
        assert Capability.UNSUPPORTED not in DISPATCHABLE
        assert list(DISPATCHABLE) == [
            Capability.CONTRACT,
            Capability.OUTREACH,
            Capability.SPEC,
            Capability.BUILD,
        ]


# ---------------------------------------------------------------------------
# RouteDecision — model invariants
# ---------------------------------------------------------------------------


class TestRouteDecisionModel:
    def test_valid_model_instantiates(self):
        d = _decision(Capability.CONTRACT, 0.9, args={"idea": "NDA"})
        assert d.capability is Capability.CONTRACT
        assert d.args == {"idea": "NDA"}

    def test_confidence_above_one_rejected(self):
        with pytest.raises(Exception):
            _decision(Capability.BUILD, 1.5)

    def test_confidence_below_zero_rejected(self):
        with pytest.raises(Exception):
            _decision(Capability.BUILD, -0.1)

    def test_invalid_capability_rejected(self):
        with pytest.raises(Exception):
            RouteDecision(capability="meetingforge", confidence=0.9, rationale="x")

    def test_unsupported_always_carries_a_reason(self):
        """§3d — the system must say what it cannot do, never go quiet."""
        d = _decision(Capability.UNSUPPORTED, 0.9)
        assert d.unsupported_reason
        assert d.unsupported_reason.strip()

    def test_rationale_is_never_blank(self):
        d = RouteDecision(capability=Capability.BUILD, confidence=0.9, rationale="   ")
        assert d.rationale.strip()

    def test_derived_properties_are_not_llm_fields(self):
        """should_dispatch / transcript_prefix must stay out of the tool schema."""
        props = set(RouteDecision.model_json_schema()["properties"])
        assert props == {
            "capability",
            "args",
            "confidence",
            "rationale",
            "unsupported_reason",
        }


# ---------------------------------------------------------------------------
# Stage 1 — prefilter. Zero LLM calls is the whole point.
# ---------------------------------------------------------------------------


class TestPrefilterQuickActions:
    @pytest.mark.parametrize("label", QUICK_ACTIONS)
    def test_quick_action_costs_zero_llm_calls(self, tmp_path: Path, label: str):
        with _no_llm() as calls:
            decision = MeshRouter().route(_ctx(tmp_path), label)
        _assert_no_llm(calls)
        assert isinstance(decision, RouteDecision)

    @pytest.mark.parametrize("label", QUICK_ACTIONS)
    def test_quick_action_is_a_deterministic_exact_match(self, tmp_path: Path, label: str):
        with _no_llm():
            decision = MeshRouter().route(_ctx(tmp_path), label)
        assert decision.confidence == 1.0

    def test_generate_nda_routes_to_contract(self, tmp_path: Path):
        with _no_llm():
            d = MeshRouter().route(_ctx(tmp_path), "GENERATE NDA")
        assert d.capability is Capability.CONTRACT
        assert d.should_dispatch is True

    def test_draft_outreach_routes_to_outreach(self, tmp_path: Path):
        with _no_llm():
            d = MeshRouter().route(_ctx(tmp_path), "DRAFT OUTREACH FOR CA FIRMS")
        assert d.capability is Capability.OUTREACH
        assert d.should_dispatch is True

    def test_run_morning_metrics_is_honestly_unsupported(self, tmp_path: Path):
        """No mesh capability produces metrics. Saying so beats silence."""
        with _no_llm():
            d = MeshRouter().route(_ctx(tmp_path), "RUN MORNING METRICS")
        assert d.capability is Capability.UNSUPPORTED
        assert d.should_dispatch is False
        assert "Nothing ran." in d.unsupported_reason

    def test_quick_action_matched_case_insensitively(self, tmp_path: Path):
        with _no_llm() as calls:
            d = MeshRouter().route(_ctx(tmp_path), "  generate nda  ")
        _assert_no_llm(calls)
        assert d.capability is Capability.CONTRACT

    def test_quick_action_passes_the_text_through_as_args(self, tmp_path: Path):
        with _no_llm():
            d = MeshRouter().route(_ctx(tmp_path), "GENERATE NDA")
        assert d.args == {"idea": "GENERATE NDA"}


class TestPrefilterSlashCommands:
    @pytest.mark.parametrize(
        "command,expected",
        [
            ("/contract", Capability.CONTRACT),
            ("/outreach", Capability.OUTREACH),
            ("/spec", Capability.SPEC),
            ("/build", Capability.BUILD),
        ],
    )
    def test_slash_command_routes_directly_with_no_llm(
        self, tmp_path: Path, command: str, expected: Capability
    ):
        with _no_llm() as calls:
            d = MeshRouter().route(_ctx(tmp_path), command)
        _assert_no_llm(calls)
        assert d.capability is expected
        assert d.confidence == 1.0
        assert d.should_dispatch is True

    def test_slash_command_remainder_becomes_args(self, tmp_path: Path):
        with _no_llm():
            d = MeshRouter().route(_ctx(tmp_path), "/build a habit tracker SaaS")
        assert d.capability is Capability.BUILD
        assert d.args == {"idea": "a habit tracker SaaS"}

    def test_bare_slash_command_has_empty_args(self, tmp_path: Path):
        with _no_llm():
            d = MeshRouter().route(_ctx(tmp_path), "/contract")
        assert d.args == {}

    def test_slash_command_is_case_insensitive(self, tmp_path: Path):
        with _no_llm():
            d = MeshRouter().route(_ctx(tmp_path), "/BUILD something")
        assert d.capability is Capability.BUILD

    def test_unknown_slash_command_is_unsupported_not_silent(self, tmp_path: Path):
        with _no_llm() as calls:
            d = MeshRouter().route(_ctx(tmp_path), "/meeting tomorrow 3pm")
        _assert_no_llm(calls)
        assert d.capability is Capability.UNSUPPORTED
        assert "/meeting" in d.unsupported_reason
        assert d.should_dispatch is False


class TestPrefilterEmptyInput:
    @pytest.mark.parametrize("text", ["", "   ", "\n\t "])
    def test_empty_input_short_circuits_to_clarify(self, tmp_path: Path, text: str):
        with _no_llm() as calls:
            d = MeshRouter().route(_ctx(tmp_path), text)
        _assert_no_llm(calls)
        assert d.capability is Capability.CLARIFY
        assert d.should_dispatch is False
        assert d.rationale.count("?") == 1


class TestPrefilterFallthrough:
    def test_natural_language_is_not_prefiltered(self):
        """Anything not on the small exact-match table must reach stage 2."""
        assert MeshRouter()._prefilter(WAITLIST) is None
        assert MeshRouter()._prefilter("draft an NDA for a fintech client") is None


# ---------------------------------------------------------------------------
# Stage 2 + §3c confidence bands. Classifier mocked throughout.
# ---------------------------------------------------------------------------


class TestConfidenceBandHigh:
    """>= 0.75 — dispatch directly."""

    def test_high_confidence_dispatches_unhedged(self, tmp_path: Path):
        with _classifier(_decision(Capability.CONTRACT, 0.92)):
            d = MeshRouter().route(_ctx(tmp_path), "draft an NDA for a fintech client")
        assert d.capability is Capability.CONTRACT
        assert d.should_dispatch is True
        assert d.is_hedged is False
        assert d.transcript_prefix == ""

    def test_threshold_boundary_is_inclusive(self, tmp_path: Path):
        with _classifier(_decision(Capability.SPEC, DISPATCH_THRESHOLD)):
            d = MeshRouter().route(_ctx(tmp_path), "write me a spec")
        assert d.is_hedged is False
        assert d.should_dispatch is True

    def test_route_event_carries_the_rationale(self, tmp_path: Path):
        """§3c — emit a `route` event with the rationale."""
        seen: list[tuple[str, dict]] = []
        router = MeshRouter(event_callback=lambda e, p: seen.append((e, p)))
        with _classifier(_decision(Capability.CONTRACT, 0.9, rationale="NDA requested.")):
            router.route(_ctx(tmp_path), "draft an NDA")
        assert [e for e, _ in seen] == ["route"]
        assert seen[0][1]["rationale"] == "NDA requested."
        assert seen[0][1]["capability"] == "contract"
        assert seen[0][1]["dispatch"] is True


class TestConfidenceBandHedged:
    """0.45 - 0.75 — dispatch, but tell the founder it is a guess."""

    def test_mid_confidence_dispatches_with_a_hedge_prefix(self, tmp_path: Path):
        with _classifier(_decision(Capability.CONTRACT, 0.60)):
            d = MeshRouter().route(_ctx(tmp_path), "sort out the paperwork")
        assert d.capability is Capability.CONTRACT
        assert d.should_dispatch is True
        assert d.is_hedged is True
        assert d.transcript_prefix == (
            'Routing to ContractForge — say "no, I meant …" to redirect.'
        )

    def test_lower_boundary_is_inclusive(self, tmp_path: Path):
        with _classifier(_decision(Capability.OUTREACH, CLARIFY_THRESHOLD)):
            d = MeshRouter().route(_ctx(tmp_path), "reach out to some firms")
        assert d.capability is Capability.OUTREACH
        assert d.should_dispatch is True
        assert d.is_hedged is True

    def test_upper_boundary_is_exclusive(self, tmp_path: Path):
        with _classifier(_decision(Capability.BUILD, DISPATCH_THRESHOLD - 0.01)):
            d = MeshRouter().route(_ctx(tmp_path), "make me a thing")
        assert d.is_hedged is True


class TestConfidenceBandLow:
    """< 0.45 — never dispatch. Ask exactly one question."""

    def test_low_confidence_becomes_clarify(self, tmp_path: Path):
        with _classifier(_decision(Capability.CONTRACT, 0.30)):
            d = MeshRouter().route(_ctx(tmp_path), "handle the thing from yesterday")
        assert d.capability is Capability.CLARIFY
        assert d.should_dispatch is False

    def test_clarify_asks_exactly_one_question(self, tmp_path: Path):
        with _classifier(_decision(Capability.CONTRACT, 0.30)):
            d = MeshRouter().route(_ctx(tmp_path), "handle the thing from yesterday")
        assert d.rationale.count("?") == 1

    def test_clarify_names_the_best_guess(self, tmp_path: Path):
        with _classifier(_decision(Capability.OUTREACH, 0.20)):
            d = MeshRouter().route(_ctx(tmp_path), "the firms thing")
        assert "OutreachForge" in d.rationale

    def test_boundary_just_below_threshold_does_not_dispatch(self, tmp_path: Path):
        with _classifier(_decision(Capability.BUILD, CLARIFY_THRESHOLD - 0.01)):
            d = MeshRouter().route(_ctx(tmp_path), "something vague")
        assert d.capability is Capability.CLARIFY
        assert d.should_dispatch is False

    def test_low_confidence_unsupported_also_becomes_clarify(self, tmp_path: Path):
        """Never dispatch below 0.45 — and never assert 'not built' while guessing."""
        with _classifier(_decision(Capability.UNSUPPORTED, 0.10)):
            d = MeshRouter().route(_ctx(tmp_path), "do the thing")
        assert d.capability is Capability.CLARIFY
        assert d.rationale.count("?") == 1

    def test_classifier_clarify_is_passed_through(self, tmp_path: Path):
        with _classifier(_decision(Capability.CLARIFY, 0.9, rationale="Which client?")):
            d = MeshRouter().route(_ctx(tmp_path), "draft it")
        assert d.capability is Capability.CLARIFY
        assert d.rationale == "Which client?"


class TestUnsupported:
    """§3d — UNSUPPORTED is a first-class outcome."""

    def test_confident_unsupported_is_preserved(self, tmp_path: Path):
        reason = "MeetingForge isn't built yet — it activates at 10 active clients."
        with _classifier(
            _decision(Capability.UNSUPPORTED, 0.95, unsupported_reason=reason)
        ):
            d = MeshRouter().route(_ctx(tmp_path), "schedule a meeting with the CA firm")
        assert d.capability is Capability.UNSUPPORTED
        assert d.unsupported_reason == reason

    def test_unsupported_never_dispatches(self, tmp_path: Path):
        with _classifier(_decision(Capability.UNSUPPORTED, 0.99)):
            d = MeshRouter().route(_ctx(tmp_path), "what did GBrain learn last night?")
        assert d.should_dispatch is False
        assert d.transcript_prefix == ""

    def test_unsupported_emits_a_route_event_rather_than_silence(self, tmp_path: Path):
        seen: list[tuple[str, dict]] = []
        router = MeshRouter(event_callback=lambda e, p: seen.append((e, p)))
        with _classifier(_decision(Capability.UNSUPPORTED, 0.95)):
            router.route(_ctx(tmp_path), "post a review response")
        assert [e for e, _ in seen] == ["route"]
        assert seen[0][1]["dispatch"] is False


# ---------------------------------------------------------------------------
# The regression that started all of this
# ---------------------------------------------------------------------------


class TestWaitlistLandingPageRegression:
    """The exact prompt that produced a user bubble, a routing line, then silence."""

    def test_reaches_the_classifier_instead_of_dying_in_the_prefilter(self):
        assert MeshRouter()._prefilter(WAITLIST) is None

    def test_routes_to_build(self, tmp_path: Path):
        with _classifier(
            _decision(Capability.BUILD, 0.93, args={"idea": WAITLIST})
        ) as classify:
            d = MeshRouter().route(_ctx(tmp_path), WAITLIST)
        assert classify.call_count == 1
        assert d.capability is Capability.BUILD
        assert d.should_dispatch is True

    def test_the_command_text_reaches_the_classifier(self, tmp_path: Path):
        with _classifier(_decision(Capability.BUILD, 0.93)) as classify:
            MeshRouter().route(_ctx(tmp_path), WAITLIST)
        prompt = classify.call_args.kwargs["user_prompt"]
        assert WAITLIST in prompt

    def test_is_not_silence(self, tmp_path: Path):
        """Whatever happens, the founder gets a decision with something to render."""
        with _classifier(_decision(Capability.BUILD, 0.93)):
            d = MeshRouter().route(_ctx(tmp_path), WAITLIST)
        assert d is not None
        assert d.rationale.strip()

    def test_no_keyword_rule_could_have_caught_it(self):
        """Documents why the prefilter alone is insufficient (§3b)."""
        lowered = WAITLIST.lower()
        for keyword in ("contract", "nda", "outreach", "lead", "spec", "architecture"):
            assert keyword not in lowered


# ---------------------------------------------------------------------------
# §3e — which model routes
# ---------------------------------------------------------------------------


class TestRouterModelSelection:
    def test_classify_requests_the_router_stage(self, tmp_path: Path):
        with _classifier(_decision(Capability.BUILD, 0.9)) as classify:
            MeshRouter().route(_ctx(tmp_path), WAITLIST)
        assert classify.call_args.kwargs["stage"] == ROUTER_STAGE

    def test_router_stage_resolves_to_sonnet(self):
        from llm.router import ModelRouter

        assert ModelRouter().get_model(ROUTER_STAGE) == "claude-sonnet-4-6"

    def test_router_stage_is_not_the_glm_default(self):
        from llm.router import ModelRouter

        model = ModelRouter().get_model(ROUTER_STAGE)
        assert "glm" not in model.lower()
        assert "qwen" not in model.lower()

    def test_frontier_tier_does_not_upgrade_the_router(self):
        """Routing is a cheap classify; it must not silently become a Fable-5 call."""
        import importlib

        import config
        import llm.router as router_module

        with patch.dict("os.environ", {"FORGEOS_FRONTIER_TIER": "true"}, clear=False):
            importlib.reload(config)
            importlib.reload(router_module)
            assert router_module.ModelRouter().get_model(ROUTER_STAGE) == "claude-sonnet-4-6"

        importlib.reload(config)
        importlib.reload(router_module)

    def test_default_stage_derivation_still_works_for_other_agents(self, tmp_path: Path):
        """The new stage kwarg must not change any existing caller."""
        from agents.architect import ArchitectAgent

        with patch("llm.claude.ClaudeClient.complete_structured") as cs, patch.dict(
            "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
        ):
            cs.return_value = object()
            ArchitectAgent()._structured_llm(
                _ctx(tmp_path), user_prompt="x", output_model=RouteDecision
            )
        assert cs.call_args.kwargs["stage"] == "architect"


# ---------------------------------------------------------------------------
# §3e — budget
# ---------------------------------------------------------------------------


class TestRouterBudget:
    def test_budget_is_two_cents(self):
        assert MeshRouter.budget_usd == 0.02

    def test_exhausted_budget_aborts_the_classify(self, tmp_path: Path):
        ctx = _ctx(tmp_path)
        ctx.record_tokens(
            model="claude-sonnet-4-6",
            purpose="test",
            prompt_tokens=1,
            completion_tokens=1,
            cost_usd=0.05,
        )
        with _classifier(_decision(Capability.BUILD, 0.9)):
            with pytest.raises(LLMError):
                MeshRouter().route(ctx, WAITLIST)

    def test_exhausted_budget_still_serves_prefilter_hits(self, tmp_path: Path):
        """A quick action spends nothing, so the budget is irrelevant to it."""
        ctx = _ctx(tmp_path)
        ctx.record_tokens(
            model="claude-sonnet-4-6",
            purpose="test",
            prompt_tokens=1,
            completion_tokens=1,
            cost_usd=0.05,
        )
        with _no_llm() as calls:
            d = MeshRouter().route(ctx, "GENERATE NDA")
        _assert_no_llm(calls)
        assert d.capability is Capability.CONTRACT


# ---------------------------------------------------------------------------
# ForgeAgent integration (§4a — the router is a ForgeAgent)
# ---------------------------------------------------------------------------


class TestMeshRouterIsAForgeAgent:
    def test_declares_forgeagent_metadata(self):
        from forge_sdk.agent import ForgeAgent

        assert issubclass(MeshRouter, ForgeAgent)
        assert MeshRouter.name == "mesh_router"
        assert MeshRouter.phase == "mesh"

    def test_writes_no_artifacts(self):
        assert MeshRouter.capabilities == []

    def test_execute_routes_the_context_idea(self, tmp_path: Path):
        with _classifier(_decision(Capability.BUILD, 0.93)):
            result = MeshRouter().run(_ctx(tmp_path, WAITLIST))
        assert result.status == "success"
        assert result.output["route"]["capability"] == "build"

    def test_run_serialises_the_decision_as_json(self, tmp_path: Path):
        with _classifier(_decision(Capability.CONTRACT, 0.9, args={"idea": "NDA"})):
            result = MeshRouter().run(_ctx(tmp_path, "draft an NDA"))
        route = result.output["route"]
        assert route["capability"] == "contract"
        assert route["args"] == {"idea": "NDA"}
        assert isinstance(route["confidence"], float)


# ---------------------------------------------------------------------------
# CapabilityRegistry (§3f) — present, empty, and honest about it
# ---------------------------------------------------------------------------


class TestCapabilityRegistry:
    def test_starts_empty_in_phase_1(self):
        r = CapabilityRegistry()
        assert len(r) == 0
        assert r.registered() == []
        assert r.unregistered() == list(DISPATCHABLE)

    def test_get_returns_none_when_nothing_is_wired(self):
        assert CapabilityRegistry().get(Capability.CONTRACT) is None

    def test_register_and_retrieve(self):
        r = CapabilityRegistry()
        adapter = object()
        r.register(Capability.CONTRACT, adapter)
        assert r.get(Capability.CONTRACT) is adapter
        assert r.is_registered(Capability.CONTRACT) is True
        assert Capability.CONTRACT in r
        assert len(r) == 1

    def test_registered_follows_dispatch_order(self):
        r = CapabilityRegistry()
        r.register(Capability.BUILD, object())
        r.register(Capability.CONTRACT, object())
        assert r.registered() == [Capability.CONTRACT, Capability.BUILD]

    @pytest.mark.parametrize(
        "terminal", [Capability.CLARIFY, Capability.UNSUPPORTED]
    )
    def test_terminal_outcomes_cannot_be_registered(self, terminal: Capability):
        with pytest.raises(ValueError):
            CapabilityRegistry().register(terminal, object())

    def test_double_registration_rejected(self):
        r = CapabilityRegistry()
        r.register(Capability.SPEC, object())
        with pytest.raises(ValueError):
            r.register(Capability.SPEC, object())

    def test_repr_says_empty_when_empty(self):
        assert "empty" in repr(CapabilityRegistry())


# ---------------------------------------------------------------------------
# Integration — a real classify call. Skipped without a live Anthropic key.
# ---------------------------------------------------------------------------


@skip_no_claude
class TestLiveClassify:
    """Mocks cannot prove the classifier's judgment. These calls can."""

    def test_waitlist_landing_page_really_routes_to_build(self, tmp_path: Path):
        d = MeshRouter().route(_ctx(tmp_path), WAITLIST)
        assert d.capability is Capability.BUILD
        assert d.should_dispatch is True

    def test_nda_request_really_routes_to_contract(self, tmp_path: Path):
        d = MeshRouter().route(
            _ctx(tmp_path),
            "Generate an NDA and service agreement for a new fintech client.",
        )
        assert d.capability is Capability.CONTRACT

    def test_meeting_request_really_reports_unsupported(self, tmp_path: Path):
        d = MeshRouter().route(
            _ctx(tmp_path), "Book me a call with the CA firm on Thursday morning"
        )
        assert d.capability is Capability.UNSUPPORTED
        assert d.unsupported_reason
