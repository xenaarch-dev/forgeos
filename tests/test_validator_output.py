"""TDD: MissionValidator structured outputs."""

from __future__ import annotations

import pytest

from models.outputs.validator_output import ValidatorOutput


class TestValidatorOutputModel:
    def test_valid_pass_model(self):
        out = ValidatorOutput(
            assertions_total=10,
            assertions_verified=9,
            acceptance_rate=0.9,
            threshold=0.8,
            passed=True,
            self_heals_used=0,
            verdict="PASS",
            results=[],
        )
        assert out.verdict == "PASS"
        assert out.passed is True

    def test_valid_fail_model(self):
        out = ValidatorOutput(
            assertions_total=10,
            assertions_verified=5,
            acceptance_rate=0.5,
            threshold=0.8,
            passed=False,
            self_heals_used=2,
            verdict="FAIL",
            results=[],
        )
        assert out.verdict == "FAIL"
        assert out.passed is False

    def test_verdict_inconsistent_with_passed_rejected(self):
        with pytest.raises(Exception):
            ValidatorOutput(
                assertions_total=10,
                assertions_verified=9,
                acceptance_rate=0.9,
                threshold=0.8,
                passed=True,
                self_heals_used=0,
                verdict="FAIL",  # inconsistent: passed=True but verdict=FAIL
                results=[],
            )

    def test_acceptance_rate_inconsistency_rejected(self):
        with pytest.raises(Exception):
            ValidatorOutput(
                assertions_total=10,
                assertions_verified=5,
                acceptance_rate=0.8,  # should be 0.5
                threshold=0.7,
                passed=True,
                self_heals_used=0,
                verdict="PASS",
                results=[],
            )

    def test_acceptance_rate_bounds(self):
        with pytest.raises(Exception):
            ValidatorOutput(
                assertions_total=10,
                assertions_verified=10,
                acceptance_rate=1.1,  # > 1.0
                threshold=0.8,
                passed=True,
                self_heals_used=0,
                verdict="PASS",
                results=[],
            )

    def test_negative_self_heals_rejected(self):
        with pytest.raises(Exception):
            ValidatorOutput(
                assertions_total=10,
                assertions_verified=9,
                acceptance_rate=0.9,
                threshold=0.8,
                passed=True,
                self_heals_used=-1,
                verdict="PASS",
                results=[],
            )

    def test_zero_assertions_edge_case(self):
        out = ValidatorOutput(
            assertions_total=0,
            assertions_verified=0,
            acceptance_rate=0.0,
            threshold=0.8,
            passed=False,
            self_heals_used=0,
            verdict="FAIL",
            results=[],
        )
        assert out.assertions_total == 0
