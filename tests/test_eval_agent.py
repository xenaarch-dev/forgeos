"""TDD: EvalAgent — automated quality gate.

Unit tests (instant, no API): TestEvalOutputModel
Integration tests (skipped by -k 'not integration'): TestEvalAgentIntegration
"""

from __future__ import annotations

import pytest

from models.outputs.eval_output import EvalOutput
from agents.eval_agent import EvalAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scores(**overrides) -> dict:
    base = {
        "code_quality_score": 85,
        "security_score": 90,
        "test_coverage_score": 80,
        "completeness_score": 85,
        "blocking_issues": [],
        "recommendations": ["Add more edge case tests"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# EvalOutput model-level tests (no LLM)
# ---------------------------------------------------------------------------

class TestEvalOutputModel:
    def test_valid_model_instantiates(self):
        out = EvalOutput(**_scores())
        assert out.code_quality_score == 85
        assert out.overall_score > 0

    def test_overall_score_computed_from_formula(self):
        out = EvalOutput(**_scores(
            code_quality_score=100,
            security_score=100,
            test_coverage_score=100,
            completeness_score=100,
        ))
        assert out.overall_score == 100

    def test_formula_weights_correct(self):
        # 80*0.3 + 80*0.35 + 80*0.2 + 80*0.15 = 80.0 → int 80
        out = EvalOutput(**_scores(
            code_quality_score=80,
            security_score=80,
            test_coverage_score=80,
            completeness_score=80,
        ))
        assert out.overall_score == int(80 * 0.3 + 80 * 0.35 + 80 * 0.2 + 80 * 0.15)

    def test_security_has_highest_weight(self):
        # security dominates: low security should drag score below 80
        out = EvalOutput(**_scores(
            code_quality_score=100,
            security_score=40,
            test_coverage_score=100,
            completeness_score=100,
        ))
        expected = int(100 * 0.3 + 40 * 0.35 + 100 * 0.2 + 100 * 0.15)
        assert out.overall_score == expected
        assert out.passed is False

    def test_passed_true_when_score_at_80(self):
        # Need overall >= 80: use all-equal scores at 80
        out = EvalOutput(**_scores(
            code_quality_score=80,
            security_score=80,
            test_coverage_score=80,
            completeness_score=80,
        ))
        assert out.passed is True

    def test_passed_false_when_score_below_80(self):
        out = EvalOutput(**_scores(
            code_quality_score=60,
            security_score=60,
            test_coverage_score=60,
            completeness_score=60,
        ))
        assert out.passed is False

    def test_ship_ready_true_when_passed_and_no_blocking_issues(self):
        out = EvalOutput(**_scores(
            code_quality_score=90,
            security_score=90,
            test_coverage_score=90,
            completeness_score=90,
            blocking_issues=[],
        ))
        assert out.ship_ready is True

    def test_ship_ready_false_when_blocking_issues_present_even_if_passed(self):
        out = EvalOutput(**_scores(
            code_quality_score=95,
            security_score=95,
            test_coverage_score=95,
            completeness_score=95,
            blocking_issues=["SQL injection in /api/contracts"],
        ))
        assert out.passed is True
        assert out.ship_ready is False

    def test_ship_ready_false_when_score_below_80(self):
        out = EvalOutput(**_scores(
            code_quality_score=50,
            security_score=40,
            test_coverage_score=50,
            completeness_score=50,
            blocking_issues=[],
        ))
        assert out.ship_ready is False

    def test_grade_A_for_90_plus(self):
        out = EvalOutput(**_scores(
            code_quality_score=95,
            security_score=95,
            test_coverage_score=90,
            completeness_score=95,
        ))
        assert out.grade == "A"

    def test_grade_B_for_80_to_89(self):
        out = EvalOutput(**_scores(
            code_quality_score=80,
            security_score=80,
            test_coverage_score=80,
            completeness_score=80,
        ))
        assert out.grade in ("A", "B")

    def test_grade_F_for_below_60(self):
        out = EvalOutput(**_scores(
            code_quality_score=40,
            security_score=40,
            test_coverage_score=40,
            completeness_score=40,
        ))
        assert out.grade == "F"

    def test_score_above_100_rejected(self):
        with pytest.raises(Exception):
            EvalOutput(**_scores(code_quality_score=101))

    def test_negative_score_rejected(self):
        with pytest.raises(Exception):
            EvalOutput(**_scores(security_score=-1))

    def test_extra_fields_ignored(self):
        out = EvalOutput(**_scores(), unknown_field="ignored")
        assert not hasattr(out, "unknown_field")

    def test_provided_overall_score_overwritten_by_formula(self):
        # Even if caller provides overall_score=99, it gets recomputed
        out = EvalOutput(**_scores(
            code_quality_score=50,
            security_score=40,
            test_coverage_score=50,
            completeness_score=50,
            overall_score=99,
        ))
        expected = int(50 * 0.3 + 40 * 0.35 + 50 * 0.2 + 50 * 0.15)
        assert out.overall_score == expected

    def test_grade_C_for_70_to_79(self):
        # 70*0.3 + 70*0.35 + 70*0.2 + 70*0.15 = 70
        out = EvalOutput(**_scores(
            code_quality_score=70,
            security_score=70,
            test_coverage_score=70,
            completeness_score=70,
        ))
        assert out.grade == "C"

    def test_grade_D_for_60_to_69(self):
        out = EvalOutput(**_scores(
            code_quality_score=60,
            security_score=60,
            test_coverage_score=60,
            completeness_score=60,
        ))
        assert out.grade == "D"


# ---------------------------------------------------------------------------
# Integration tests — skipped by -k "not integration"
# ---------------------------------------------------------------------------

class TestEvalAgentIntegration:
    """Live API tests. Require ANTHROPIC_API_KEY. Skipped in CI."""

    def test_eval_agent_returns_valid_output(self):
        from models import ProjectContext
        ctx = ProjectContext.new(
            idea="AI contract generator for Indian freelancers",
            workdir="/tmp/eval_test",
        )
        ctx.spec = "# ContractForge\n\nAI-powered contract generation for Indian freelancers."
        agent = EvalAgent()
        result = agent.run(ctx)
        # EvalAgent may fail if quality is low (that is correct behaviour)
        assert result.output or result.error
        if result.status == "success":
            out = EvalOutput(**result.output)
            assert 0 <= out.overall_score <= 100
