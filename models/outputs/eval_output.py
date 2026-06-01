"""Pydantic output model for EvalAgent — automated quality gate."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvalOutput(BaseModel):
    """Quality scores and ship-readiness verdict.

    overall_score, grade, passed, and ship_ready are computed by
    model_validator — the LLM only needs to supply the four raw scores,
    blocking_issues, and recommendations.
    """

    model_config = ConfigDict(extra="ignore")

    code_quality_score: int = Field(..., ge=0, le=100)
    security_score: int = Field(..., ge=0, le=100)
    test_coverage_score: int = Field(..., ge=0, le=100)
    completeness_score: int = Field(..., ge=0, le=100)
    blocking_issues: List[str]
    recommendations: List[str]

    # Computed by validator — do not require from LLM
    overall_score: int = Field(default=0, ge=0, le=100)
    passed: bool = False
    grade: Literal["A", "B", "C", "D", "F"] = "F"
    ship_ready: bool = False

    @model_validator(mode="after")
    def compute_derived_fields(self) -> "EvalOutput":
        """Recompute overall_score, grade, passed, ship_ready from raw scores."""
        overall = int(
            self.code_quality_score * 0.3
            + self.security_score * 0.35
            + self.test_coverage_score * 0.2
            + self.completeness_score * 0.15
        )
        self.overall_score = overall
        self.passed = overall >= 80
        self.ship_ready = self.passed and not self.blocking_issues
        if overall >= 90:
            self.grade = "A"
        elif overall >= 80:
            self.grade = "B"
        elif overall >= 70:
            self.grade = "C"
        elif overall >= 60:
            self.grade = "D"
        else:
            self.grade = "F"
        return self


__all__ = ["EvalOutput"]
