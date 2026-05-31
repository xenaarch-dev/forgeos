"""End-to-end orchestrator tests using stubbed agents (no network)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from forgeos.agents.base import BaseAgent
from forgeos.models import AgentResult, AgentStatus, ProjectContext
from forgeos.orchestrator import Orchestrator


class _OkAgent(BaseAgent):
    name = "stub"
    phase = "code"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        return {"ok": True}


class _FailingAgent(BaseAgent):
    name = "boom"
    phase = "code"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        raise RuntimeError("boom")


def test_orchestrator_runs_stub_agents(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGEOS_ENABLE_OBSIDIAN", "0")
    monkeypatch.setenv("FORGEOS_MAX_AGENT_RETRIES", "1")
    orch = Orchestrator(idea="Build a tiny todo app", workdir=str(tmp_path))
    Orchestrator.AGENTS = [_OkAgent]
    ctx = orch.run()
    assert (tmp_path / "context.json").exists()
    assert (tmp_path / "SUMMARY.md").exists()
    assert any(r.status == AgentStatus.SUCCESS.value for r in ctx.agent_results)


def test_orchestrator_degrades_on_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGEOS_ENABLE_OBSIDIAN", "0")
    monkeypatch.setenv("FORGEOS_MAX_AGENT_RETRIES", "1")
    orch = Orchestrator(idea="Build a todo app", workdir=str(tmp_path))
    Orchestrator.AGENTS = [_FailingAgent, _OkAgent]
    ctx = orch.run()
    statuses = [r.status for r in ctx.agent_results]
    assert AgentStatus.FAILED.value in statuses
    assert (tmp_path / "STATUS.md").exists()


def test_project_context_round_trip(tmp_path: Path) -> None:
    ctx = ProjectContext.new(idea="Hello", workdir=str(tmp_path))
    ctx.spec = "spec"
    ctx.architecture = "arch"
    ctx.save()
    again = ProjectContext.load(ctx.context_path())
    assert again.idea == "Hello"
    assert again.spec == "spec"
    assert again.architecture == "arch"


def test_summary_after_token_record(tmp_path: Path) -> None:
    ctx = ProjectContext.new(idea="Hello", workdir=str(tmp_path))
    ctx.record_tokens("claude-sonnet-4-20250514", "test", 100, 200, 0.05)
    summary = ctx.summary()
    assert summary["tokens"] == 300
    assert summary["cost_usd"] == 0.05
