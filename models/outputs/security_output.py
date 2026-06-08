"""Pydantic output model for SecurityAgent structured outputs."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class SecurityOutput(BaseModel):
    """Validated security audit output from SecurityAgent.

    The owasp_score field is the key addition over the legacy dict — EvalAgent
    uses it as a numeric gate when computing the pipeline ship score.
    Score formula: 10.0 - (critical × 3.0) - min(warnings × 0.5, 2.0), clamped [0, 10].
    """

    model_config = ConfigDict(extra="ignore")

    owasp_score: float = Field(..., ge=0.0, le=10.0, description="OWASP audit score 0.0–10.0 (10 = no findings)")
    critical_count: int = Field(..., ge=0, description="Number of critical findings (0 = pipeline can proceed)")
    warnings_count: int = Field(..., ge=0, description="Number of warning-level findings")
    passed_count: int = Field(..., ge=0, description="Number of checks that passed cleanly")
    critical_findings: List[str] = Field(default_factory=list, description="Critical finding descriptions")
    warnings_list: List[str] = Field(default_factory=list, description="Warning finding descriptions")
    passed_checks: List[str] = Field(default_factory=list, description="Passed check names")
    security_md_written: bool = Field(..., description="SECURITY.md written to workdir")
    rls_policies_written: bool = Field(..., description="supabase/policies.sql written to project directory")
    ci_security_workflow_written: bool = Field(..., description=".github/workflows/security.yml written")


def compute_owasp_score(critical_count: int, warnings_count: int) -> float:
    """Compute deterministic OWASP score from audit findings."""
    score = 10.0 - (critical_count * 3.0) - min(warnings_count * 0.5, 2.0)
    return round(max(0.0, min(10.0, score)), 1)
