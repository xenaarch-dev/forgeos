"""Pydantic output model for MissionValidator structured outputs."""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ValidatorOutput(BaseModel):
    """Validated output from MissionValidator (mission/validator.py).

    MissionValidator is the final gate before ship. The `verdict` field
    provides an explicit PASS/FAIL string for EvalAgent score computation.
    `acceptance_rate` is the fraction of assertions verified (0.0–1.0).
    """

    model_config = ConfigDict(extra="ignore")

    assertions_total: int = Field(..., ge=0, description="Total assertions in the validation contract")
    assertions_verified: int = Field(..., ge=0, description="Assertions that passed verification")
    acceptance_rate: float = Field(..., ge=0.0, le=1.0, description="assertions_verified / assertions_total")
    threshold: float = Field(..., ge=0.0, le=1.0, description="Minimum acceptance_rate to pass")
    passed: bool = Field(..., description="True if acceptance_rate >= threshold")
    self_heals_used: int = Field(..., ge=0, description="Number of self-heal iterations performed")
    verdict: Literal["PASS", "FAIL"] = Field(..., description="Explicit gate verdict string for EvalAgent")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Per-assertion result records")

    @model_validator(mode="after")
    def validate_verdict_matches_passed(self) -> "ValidatorOutput":
        expected_verdict = "PASS" if self.passed else "FAIL"
        if self.verdict != expected_verdict:
            raise ValueError(
                f"verdict '{self.verdict}' inconsistent with passed={self.passed}"
            )
        return self

    @model_validator(mode="after")
    def validate_acceptance_consistency(self) -> "ValidatorOutput":
        if self.assertions_total > 0:
            expected = round(self.assertions_verified / self.assertions_total, 4)
            actual = round(self.acceptance_rate, 4)
            if abs(expected - actual) > 0.01:
                raise ValueError(
                    f"acceptance_rate {self.acceptance_rate} inconsistent with "
                    f"{self.assertions_verified}/{self.assertions_total}"
                )
        return self
