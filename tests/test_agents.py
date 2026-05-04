"""Agent unit tests — exercise deterministic fallbacks (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forgeos.agents.architect import ArchitectAgent
from forgeos.agents.scaffold import ScaffoldAgent
from forgeos.agents.security import SecurityAgent
from forgeos.models import ProjectContext, StackChoice, Task, TaskStatus


def _ctx(tmp_path: Path, idea: str = "Build a CRUD SaaS") -> ProjectContext:
    return ProjectContext.new(idea=idea, workdir=str(tmp_path))


def test_architect_falls_back_without_llm(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    ctx = _ctx(tmp_path)
    out = ArchitectAgent().run(ctx)
    assert out.status == "success"
    assert (tmp_path / "STACK.json").exists()
    assert (tmp_path / "SPEC.md").exists()
    assert (tmp_path / "ARCH.md").exists()
    assert (tmp_path / "TASKS.json").exists()
    tasks = json.loads((tmp_path / "TASKS.json").read_text())
    assert len(tasks) >= 5
    stack = json.loads((tmp_path / "STACK.json").read_text())
    assert stack["frontend"]
    assert stack["backend"]


def test_scaffold_emits_full_tree(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    ctx = _ctx(tmp_path)
    ArchitectAgent().run(ctx)
    out = ScaffoldAgent().run(ctx)
    assert out.status == "success"
    project = tmp_path / "project"
    assert (project / "backend/app/main.py").exists()
    assert (project / "frontend/package.json").exists()
    assert (project / "supabase/schema.sql").exists()
    assert (project / "docker-compose.yml").exists()
    assert (project / ".github/workflows/ci.yml").exists()


def test_security_writes_report_and_policies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    ctx = _ctx(tmp_path)
    ArchitectAgent().run(ctx)
    ScaffoldAgent().run(ctx)
    out = SecurityAgent().run(ctx)
    assert out.status == "success"
    assert (tmp_path / "SECURITY.md").exists()
    project = tmp_path / "project"
    assert (project / "supabase/policies.sql").exists()
    assert (project / "trivy.yaml").exists()
    assert (project / ".github/workflows/security.yml").exists()


def test_task_dependencies_round_trip(tmp_path: Path) -> None:
    a = Task.new("a", "coder", "code")
    b = Task.new("b", "coder", "code", [a.id])
    assert b.depends_on == [a.id]
    assert a.status == TaskStatus.PENDING.value
