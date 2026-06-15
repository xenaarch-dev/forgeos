"""GStackGate migration smoke tests — no LLM calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.gstack import GStackGate
from models import GateResult, ProjectContext


def _ctx(tmp_path: Path) -> ProjectContext:
    return ProjectContext.new(idea="Build a task manager SaaS", workdir=str(tmp_path))


class _FailingGate(GStackGate):
    """Minimal concrete gate that always returns a failing GateResult."""

    name = "test_failing_gate"
    gate_name = "test_fail"
    blocking = True

    def _evaluate(self, context: ProjectContext) -> GateResult:
        return GateResult(
            gate=self.gate_name,
            passed=False,
            score=2.0,
            feedback="deliberate test failure",
        )


class _PassingGate(GStackGate):
    """Minimal concrete gate that always returns a passing GateResult."""

    name = "test_passing_gate"
    gate_name = "test_pass"
    blocking = True

    def _evaluate(self, context: ProjectContext) -> GateResult:
        return GateResult(
            gate=self.gate_name,
            passed=True,
            score=8.0,
            feedback="looks good",
        )


def test_blocking_gate_failure_produces_failed_result(tmp_path: Path) -> None:
    """A blocking gate that fails must return status='failed' — the signal hermes
    uses to raise RuntimeError and halt the pipeline."""
    ctx = _ctx(tmp_path)
    result = _FailingGate().run(ctx)
    assert result.status == "failed"
    assert result.error is not None
    assert "RuntimeError" in result.error
    assert "test_fail" in result.error


def test_passing_gate_produces_success_result(tmp_path: Path) -> None:
    """A gate that passes must return status='success' so hermes continues."""
    ctx = _ctx(tmp_path)
    result = _PassingGate().run(ctx)
    assert result.status == "success"
    assert result.output["passed"] is True
    assert result.output["score"] == 8.0


def test_gstack_gate_is_forgeagent_subclass() -> None:
    """Confirm GStackGate now inherits from ForgeAgent (migration check)."""
    from forge_sdk.agent import ForgeAgent
    assert issubclass(GStackGate, ForgeAgent)


def test_gstack_gate_base_attrs() -> None:
    """GStackGate must declare the three ForgeAgent base attrs."""
    assert GStackGate.capabilities == []
    assert "idea" in GStackGate.requires
    assert GStackGate.budget_usd == 0.0
