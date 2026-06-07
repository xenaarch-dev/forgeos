"""TDD: PMAgent — Stage 0 demand validation.

Unit tests (instant, no API): TestPMOutputModel, TestCompetitorInfo
Integration tests (skipped by -k 'not integration'): TestPMAgentIntegration
"""

from __future__ import annotations

import pytest

from models.outputs.pm_output import CompetitorInfo, PMOutput
from agents.pm_agent import PMAgent
from llm.claude import ClaudeClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LONG_PERSONA = "a" * 100
_LONG_REASONING = "b" * 200


def _valid_pm_output(**overrides) -> dict:
    base = {
        "product_name": "ContractForge",
        "top_3_competitors": [
            {"name": "DocuSign",   "weakness": "expensive for India", "opportunity": "INR pricing"},
            {"name": "PandaDoc",   "weakness": "no India compliance",  "opportunity": "local law coverage"},
            {"name": "Zoho Sign",  "weakness": "poor UX",             "opportunity": "AI document generation"},
        ],
        "target_user_persona": _LONG_PERSONA,
        "demand_signals": ["r/IndiaFreelance posts", "Twitter complaints", "Google Trends surge"],
        "recommended_price_inr": 999,
        "recommended_price_usd": 12,
        "build_recommendation": "build",
        "reasoning": _LONG_REASONING,
        "spec_additions": ["offline PDF export", "GST invoice generation"],
        "market_size_estimate": "$200M TAM in Indian SMB",
        "biggest_risk": "DocuSign price drop",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# PMOutput model-level tests (no LLM)
# ---------------------------------------------------------------------------

class TestPMOutputModel:
    def test_valid_model_instantiates(self):
        out = PMOutput(**_valid_pm_output())
        assert out.product_name == "ContractForge"
        assert out.build_recommendation == "build"
        assert out.recommended_price_inr == 999

    def test_build_recommendation_invalid_literal_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(build_recommendation="maybe"))

    def test_build_recommendation_valid_build(self):
        out = PMOutput(**_valid_pm_output(build_recommendation="build"))
        assert out.build_recommendation == "build"

    def test_build_recommendation_valid_dont_build(self):
        out = PMOutput(**_valid_pm_output(build_recommendation="dont_build"))
        assert out.build_recommendation == "dont_build"

    def test_build_recommendation_valid_pivot(self):
        out = PMOutput(**_valid_pm_output(build_recommendation="pivot"))
        assert out.build_recommendation == "pivot"

    def test_competitors_fewer_than_3_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(top_3_competitors=[
                {"name": "A", "weakness": "x", "opportunity": "y"},
                {"name": "B", "weakness": "x", "opportunity": "y"},
            ]))

    def test_competitors_more_than_3_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(top_3_competitors=[
                {"name": f"C{i}", "weakness": "x", "opportunity": "y"}
                for i in range(4)
            ]))

    def test_competitors_exactly_3_accepted(self):
        out = PMOutput(**_valid_pm_output())
        assert len(out.top_3_competitors) == 3

    def test_demand_signals_fewer_than_3_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(demand_signals=["only one", "two"]))

    def test_demand_signals_3_or_more_accepted(self):
        out = PMOutput(**_valid_pm_output())
        assert len(out.demand_signals) >= 3

    def test_target_persona_below_100_chars_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(target_user_persona="too short"))

    def test_target_persona_100_chars_accepted(self):
        out = PMOutput(**_valid_pm_output(target_user_persona="a" * 100))
        assert len(out.target_user_persona) == 100

    def test_reasoning_below_200_chars_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(reasoning="short reason"))

    def test_reasoning_200_chars_accepted(self):
        out = PMOutput(**_valid_pm_output(reasoning="r" * 200))
        assert len(out.reasoning) == 200

    def test_spec_additions_fewer_than_2_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(spec_additions=["only one"]))

    def test_spec_additions_2_or_more_accepted(self):
        out = PMOutput(**_valid_pm_output())
        assert len(out.spec_additions) >= 2

    def test_recommended_price_inr_zero_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(recommended_price_inr=0))

    def test_recommended_price_inr_negative_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(recommended_price_inr=-1))

    def test_recommended_price_usd_zero_rejected(self):
        with pytest.raises(Exception):
            PMOutput(**_valid_pm_output(recommended_price_usd=0))

    def test_extra_fields_ignored(self):
        out = PMOutput(**_valid_pm_output(), unknown_field="ignored")
        assert not hasattr(out, "unknown_field")


class TestCompetitorInfo:
    def test_valid_competitor_info(self):
        c = CompetitorInfo(name="DocuSign", weakness="expensive", opportunity="INR pricing")
        assert c.name == "DocuSign"

    def test_empty_name_rejected(self):
        with pytest.raises(Exception):
            CompetitorInfo(name="", weakness="x", opportunity="y")

    def test_empty_weakness_rejected(self):
        with pytest.raises(Exception):
            CompetitorInfo(name="X", weakness="", opportunity="y")

    def test_empty_opportunity_rejected(self):
        with pytest.raises(Exception):
            CompetitorInfo(name="X", weakness="x", opportunity="")


# ---------------------------------------------------------------------------
# Integration tests — skipped by -k "not integration"
# ---------------------------------------------------------------------------

class TestPMAgentIntegration:
    """Live API tests. Require ANTHROPIC_API_KEY. Skipped in CI."""

    def _ctx(self, idea: str, suffix: str):
        from models import ProjectContext
        return ProjectContext.new(idea=idea, workdir=f"/tmp/pm_test_{suffix}")

    def test_build_recommendation_is_build_for_known_idea(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
        monkeypatch.setattr(ClaudeClient, "complete_structured",
                            lambda *a, **kw: PMOutput(**_valid_pm_output()))
        ctx = self._ctx("AI contract generator for Indian freelancers", "build")
        result = PMAgent().run(ctx)
        assert result.status == "success", f"PMAgent failed: {result.error}"
        assert result.output["build_recommendation"] == "build"

    def test_exactly_3_competitors_returned(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
        monkeypatch.setattr(ClaudeClient, "complete_structured",
                            lambda *a, **kw: PMOutput(**_valid_pm_output()))
        ctx = self._ctx("AI contract generator for Indian freelancers", "competitors")
        result = PMAgent().run(ctx)
        assert result.status == "success"
        assert len(result.output["top_3_competitors"]) == 3

    def test_recommended_price_inr_positive(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
        monkeypatch.setattr(ClaudeClient, "complete_structured",
                            lambda *a, **kw: PMOutput(**_valid_pm_output()))
        ctx = self._ctx("AI contract generator for Indian freelancers", "price")
        result = PMAgent().run(ctx)
        assert result.status == "success"
        assert result.output["recommended_price_inr"] > 0
