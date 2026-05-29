"""
TDD: SecurityAgent structured outputs.

Key addition: owasp_score as a numeric field for EvalAgent gate scoring.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from models.outputs.security_output import SecurityOutput, compute_owasp_score
from agents.architect import ArchitectAgent
from agents.scaffold import ScaffoldAgent
from agents.security import SecurityAgent
from models import ProjectContext


def _full_ctx(tmp_path: Path) -> ProjectContext:
    """Run architect + scaffold to produce a project directory security can audit."""
    import os
    old = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        ctx = ProjectContext.new(idea="Build a habit tracker SaaS", workdir=str(tmp_path))
        ArchitectAgent().run(ctx)
        ScaffoldAgent().run(ctx)
    finally:
        if old:
            os.environ["ANTHROPIC_API_KEY"] = old
    return ctx


# ---------------------------------------------------------------------------
# Score helper tests
# ---------------------------------------------------------------------------

class TestComputeOwaspScore:
    def test_no_findings_gives_ten(self):
        assert compute_owasp_score(0, 0) == 10.0

    def test_one_critical_reduces_score(self):
        score = compute_owasp_score(1, 0)
        assert score == 7.0

    def test_two_criticals_reduces_score(self):
        score = compute_owasp_score(2, 0)
        assert score == 4.0

    def test_warnings_reduce_score_capped(self):
        # 10 warnings still only deducts max 2.0
        score = compute_owasp_score(0, 10)
        assert score == 8.0

    def test_score_never_below_zero(self):
        score = compute_owasp_score(10, 10)
        assert score == 0.0

    def test_score_never_above_ten(self):
        score = compute_owasp_score(0, 0)
        assert score == 10.0


# ---------------------------------------------------------------------------
# Model-level tests
# ---------------------------------------------------------------------------

class TestSecurityOutputModel:
    def test_valid_model_instantiates(self):
        out = SecurityOutput(
            owasp_score=10.0,
            critical_count=0,
            warnings_count=0,
            passed_count=5,
            critical_findings=[],
            warnings_list=[],
            passed_checks=["no hardcoded secrets", "auth on all routes"],
            security_md_written=True,
            rls_policies_written=True,
            ci_security_workflow_written=True,
        )
        assert out.owasp_score == 10.0
        assert out.critical_count == 0

    def test_owasp_score_lower_bound(self):
        with pytest.raises(Exception):
            SecurityOutput(
                owasp_score=-0.1,  # < 0
                critical_count=0,
                warnings_count=0,
                passed_count=5,
                security_md_written=True,
                rls_policies_written=True,
                ci_security_workflow_written=True,
            )

    def test_owasp_score_upper_bound(self):
        with pytest.raises(Exception):
            SecurityOutput(
                owasp_score=10.1,  # > 10
                critical_count=0,
                warnings_count=0,
                passed_count=5,
                security_md_written=True,
                rls_policies_written=True,
                ci_security_workflow_written=True,
            )

    def test_negative_critical_count_rejected(self):
        with pytest.raises(Exception):
            SecurityOutput(
                owasp_score=10.0,
                critical_count=-1,
                warnings_count=0,
                passed_count=5,
                security_md_written=True,
                rls_policies_written=True,
                ci_security_workflow_written=True,
            )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestSecurityOutputFromAgent:
    def test_agent_output_validates_as_pydantic_model(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _full_ctx(tmp_path)
        result = SecurityAgent().run(ctx)
        assert result.status == "success", f"security failed: {result.error}"
        output = SecurityOutput(**result.output)
        assert 0.0 <= output.owasp_score <= 10.0

    def test_clean_project_gets_high_score(self, tmp_path, monkeypatch):
        """A freshly scaffolded project should have 0 critical findings and high score."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _full_ctx(tmp_path)
        result = SecurityAgent().run(ctx)
        assert result.status == "success"
        output = SecurityOutput(**result.output)
        assert output.critical_count == 0, f"unexpected criticals: {output.critical_findings}"
        assert output.owasp_score >= 8.0, f"score too low: {output.owasp_score}"

    def test_security_files_written(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _full_ctx(tmp_path)
        result = SecurityAgent().run(ctx)
        assert result.status == "success"
        output = SecurityOutput(**result.output)
        assert output.security_md_written is True
        assert output.rls_policies_written is True
        assert output.ci_security_workflow_written is True
        assert (tmp_path / "SECURITY.md").exists()
        assert (tmp_path / "project/supabase/policies.sql").exists()
        assert (tmp_path / "project/.github/workflows/security.yml").exists()

    def test_passed_count_positive(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _full_ctx(tmp_path)
        result = SecurityAgent().run(ctx)
        assert result.status == "success"
        output = SecurityOutput(**result.output)
        assert output.passed_count >= 1

    def test_types_correct(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _full_ctx(tmp_path)
        result = SecurityAgent().run(ctx)
        assert result.status == "success"
        output = SecurityOutput(**result.output)
        assert isinstance(output.critical_findings, list)
        assert isinstance(output.warnings_list, list)
        assert isinstance(output.passed_checks, list)
        assert isinstance(output.owasp_score, float)
