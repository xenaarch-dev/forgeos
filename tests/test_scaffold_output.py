"""
TDD: ScaffoldAgent structured outputs.

ScaffoldAgent is mostly deterministic (file templates). The structured output
captures validated metadata about what was generated — ensuring downstream
agents can trust that required files exist before they run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from models.outputs.scaffold_output import ScaffoldOutput
from agents.architect import ArchitectAgent
from agents.scaffold import ScaffoldAgent
from models import ProjectContext


def _ctx(tmp_path: Path, idea: str = "Build a habit tracker SaaS") -> ProjectContext:
    ctx = ProjectContext.new(idea=idea, workdir=str(tmp_path))
    # Run architect first — scaffold depends on context.stack and context.tasks
    import os
    old = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        ArchitectAgent().run(ctx)
    finally:
        if old:
            os.environ["ANTHROPIC_API_KEY"] = old
    return ctx


# ---------------------------------------------------------------------------
# Model-level tests
# ---------------------------------------------------------------------------

class TestScaffoldOutputModel:
    def test_valid_model_instantiates(self):
        out = ScaffoldOutput(
            project_root="project",
            files_created=["project/backend/app/main.py", "project/frontend/package.json",
                           "project/supabase/schema.sql", "project/docker-compose.yml",
                           "project/.github/workflows/ci.yml"],
            has_backend=True,
            has_frontend=True,
            has_supabase=True,
            has_docker=True,
            has_github_actions=True,
            backend_framework="FastAPI",
            frontend_framework="Next.js 14",
            file_count=5,
        )
        assert out.has_backend is True
        assert out.file_count == 5

    def test_files_created_minimum_count(self):
        with pytest.raises(Exception):
            ScaffoldOutput(
                project_root="project",
                files_created=["a", "b", "c", "d"],  # < 5
                has_backend=True,
                has_frontend=True,
                has_supabase=True,
                has_docker=True,
                has_github_actions=True,
                backend_framework="FastAPI",
                frontend_framework="Next.js 14",
                file_count=4,
            )

    def test_file_count_minimum(self):
        with pytest.raises(Exception):
            ScaffoldOutput(
                project_root="project",
                files_created=["a"] * 5,
                has_backend=True,
                has_frontend=True,
                has_supabase=True,
                has_docker=True,
                has_github_actions=True,
                backend_framework="FastAPI",
                frontend_framework="Next.js 14",
                file_count=3,  # < 5
            )

    def test_project_root_cannot_be_empty(self):
        with pytest.raises(Exception):
            ScaffoldOutput(
                project_root="",
                files_created=["a"] * 5,
                has_backend=True,
                has_frontend=True,
                has_supabase=True,
                has_docker=True,
                has_github_actions=True,
                backend_framework="FastAPI",
                frontend_framework="Next.js 14",
                file_count=5,
            )


# ---------------------------------------------------------------------------
# Integration tests — ScaffoldAgent.run() must return ScaffoldOutput-valid dict
# ---------------------------------------------------------------------------

class TestScaffoldOutputFromAgent:
    def test_agent_output_validates_as_pydantic_model(self, tmp_path, monkeypatch):
        """Core contract: scaffold output must parse as ScaffoldOutput."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ScaffoldAgent().run(ctx)
        assert result.status == "success", f"scaffold failed: {result.error}"
        output = ScaffoldOutput(**result.output)
        assert output.project_root
        assert output.file_count >= 5

    def test_has_backend_true_when_backend_exists(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ScaffoldAgent().run(ctx)
        assert result.status == "success"
        output = ScaffoldOutput(**result.output)
        assert output.has_backend is True
        assert (tmp_path / "project/backend/app/main.py").exists()

    def test_has_frontend_true_when_frontend_exists(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ScaffoldAgent().run(ctx)
        assert result.status == "success"
        output = ScaffoldOutput(**result.output)
        assert output.has_frontend is True
        assert (tmp_path / "project/frontend/package.json").exists()

    def test_has_supabase_true(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ScaffoldAgent().run(ctx)
        assert result.status == "success"
        output = ScaffoldOutput(**result.output)
        assert output.has_supabase is True
        assert (tmp_path / "project/supabase/schema.sql").exists()

    def test_has_github_actions_true(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ScaffoldAgent().run(ctx)
        assert result.status == "success"
        output = ScaffoldOutput(**result.output)
        assert output.has_github_actions is True
        assert (tmp_path / "project/.github/workflows/ci.yml").exists()

    def test_files_list_non_empty_strings(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ScaffoldAgent().run(ctx)
        assert result.status == "success"
        output = ScaffoldOutput(**result.output)
        assert all(f and f.strip() for f in output.files_created)

    def test_framework_fields_non_empty(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ScaffoldAgent().run(ctx)
        assert result.status == "success"
        output = ScaffoldOutput(**result.output)
        assert output.backend_framework
        assert output.frontend_framework

    def test_file_count_matches_files_list(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ScaffoldAgent().run(ctx)
        assert result.status == "success"
        output = ScaffoldOutput(**result.output)
        assert output.file_count == len(output.files_created)
