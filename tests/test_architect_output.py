"""
TDD: ArchitectAgent structured outputs.

These tests define the contract for ArchitectOutput — the Pydantic model
that replaces freeform text parsing in ArchitectAgent._execute().

Run before implementation to confirm RED. After implementation must be GREEN.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# NOTE: This import fails until models/outputs/architect_output.py is created.
from models.outputs.architect_output import ArchitectOutput
from agents.architect import ArchitectAgent, SYSTEM_PROMPT
from models import ProjectContext


def _ctx(tmp_path: Path, idea: str = "Build a habit tracker SaaS for busy professionals") -> ProjectContext:
    return ProjectContext.new(idea=idea, workdir=str(tmp_path))


# ---------------------------------------------------------------------------
# Model-level tests — pure Pydantic validation, no LLM needed
# ---------------------------------------------------------------------------

class TestArchitectOutputModel:
    def test_valid_model_instantiates(self):
        out = ArchitectOutput(
            product_name="HabitPro",
            tech_stack={"frontend": "Next.js 14", "backend": "FastAPI", "database": "Supabase"},
            spec_md="# Product Specification\n\n" + "content " * 50,
            arch_md="# Architecture\n\n" + "content " * 50,
            api_routes=["GET /healthz", "POST /api/habits", "GET /api/habits"],
            task_titles=["scaffold project", "implement habits CRUD", "deploy to Railway"],
            estimated_phases=5,
            stack_frontend="Next.js 14 (App Router) + Tailwind",
            stack_backend="FastAPI",
            stack_database="Supabase (Postgres)",
        )
        assert out.product_name == "HabitPro"
        assert out.estimated_phases == 5

    def test_product_name_cannot_be_empty(self):
        with pytest.raises(Exception):
            ArchitectOutput(
                product_name="",
                tech_stack={},
                spec_md="x" * 200,
                arch_md="x" * 200,
                api_routes=["GET /healthz"],
                task_titles=["a", "b", "c"],
                estimated_phases=5,
                stack_frontend="Next.js",
                stack_backend="FastAPI",
                stack_database="Supabase",
            )

    def test_spec_md_minimum_length(self):
        with pytest.raises(Exception):
            ArchitectOutput(
                product_name="App",
                tech_stack={},
                spec_md="too short",
                arch_md="x" * 200,
                api_routes=["GET /healthz"],
                task_titles=["a", "b", "c"],
                estimated_phases=5,
                stack_frontend="Next.js",
                stack_backend="FastAPI",
                stack_database="Supabase",
            )

    def test_arch_md_minimum_length(self):
        with pytest.raises(Exception):
            ArchitectOutput(
                product_name="App",
                tech_stack={},
                spec_md="x" * 200,
                arch_md="too short",
                api_routes=["GET /healthz"],
                task_titles=["a", "b", "c"],
                estimated_phases=5,
                stack_frontend="Next.js",
                stack_backend="FastAPI",
                stack_database="Supabase",
            )

    def test_estimated_phases_lower_bound(self):
        with pytest.raises(Exception):
            ArchitectOutput(
                product_name="App",
                tech_stack={},
                spec_md="x" * 200,
                arch_md="x" * 200,
                api_routes=["GET /healthz"],
                task_titles=["a", "b", "c"],
                estimated_phases=2,  # < 3
                stack_frontend="Next.js",
                stack_backend="FastAPI",
                stack_database="Supabase",
            )

    def test_estimated_phases_upper_bound(self):
        with pytest.raises(Exception):
            ArchitectOutput(
                product_name="App",
                tech_stack={},
                spec_md="x" * 200,
                arch_md="x" * 200,
                api_routes=["GET /healthz"],
                task_titles=["a", "b", "c"],
                estimated_phases=21,  # > 20
                stack_frontend="Next.js",
                stack_backend="FastAPI",
                stack_database="Supabase",
            )

    def test_task_titles_minimum_count(self):
        with pytest.raises(Exception):
            ArchitectOutput(
                product_name="App",
                tech_stack={},
                spec_md="x" * 200,
                arch_md="x" * 200,
                api_routes=["GET /healthz"],
                task_titles=["only one task", "only two tasks"],  # < 3
                estimated_phases=5,
                stack_frontend="Next.js",
                stack_backend="FastAPI",
                stack_database="Supabase",
            )


# ---------------------------------------------------------------------------
# Integration tests — ArchitectAgent.run() must return ArchitectOutput-valid dict
# ---------------------------------------------------------------------------

class TestArchitectOutputFromAgent:
    def test_agent_output_validates_as_pydantic_model(self, tmp_path, monkeypatch):
        """Core contract: agent output must be parseable as ArchitectOutput."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ArchitectAgent().run(ctx)
        assert result.status == "success", f"agent failed: {result.error}"
        output = ArchitectOutput(**result.output)
        assert output.product_name

    def test_required_fields_are_non_empty(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ArchitectAgent().run(ctx)
        assert result.status == "success"
        output = ArchitectOutput(**result.output)
        for field_name in ["product_name", "spec_md", "arch_md", "stack_frontend", "stack_backend", "stack_database"]:
            val = getattr(output, field_name)
            assert val and str(val).strip(), f"Field '{field_name}' must not be empty"

    def test_spec_md_has_minimum_content(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ArchitectAgent().run(ctx)
        assert result.status == "success"
        output = ArchitectOutput(**result.output)
        assert len(output.spec_md) >= 200, f"spec_md too short: {len(output.spec_md)} chars"

    def test_arch_md_has_minimum_content(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ArchitectAgent().run(ctx)
        assert result.status == "success"
        output = ArchitectOutput(**result.output)
        assert len(output.arch_md) >= 200, f"arch_md too short: {len(output.arch_md)} chars"

    def test_api_routes_is_list_with_content(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ArchitectAgent().run(ctx)
        assert result.status == "success"
        output = ArchitectOutput(**result.output)
        assert isinstance(output.api_routes, list)
        assert len(output.api_routes) >= 1, "must have at least one API route"

    def test_task_titles_has_minimum_count(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ArchitectAgent().run(ctx)
        assert result.status == "success"
        output = ArchitectOutput(**result.output)
        assert len(output.task_titles) >= 3

    def test_types_are_correct(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        result = ArchitectAgent().run(ctx)
        assert result.status == "success"
        output = ArchitectOutput(**result.output)
        assert isinstance(output.tech_stack, dict)
        assert isinstance(output.api_routes, list)
        assert isinstance(output.task_titles, list)
        assert isinstance(output.estimated_phases, int)
        assert 3 <= output.estimated_phases <= 20

    def test_files_still_written_to_disk(self, tmp_path, monkeypatch):
        """Structured output migration must not break file output."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ctx = _ctx(tmp_path)
        ArchitectAgent().run(ctx)
        assert (tmp_path / "SPEC.md").exists()
        assert (tmp_path / "ARCH.md").exists()
        assert (tmp_path / "TASKS.json").exists()
        assert (tmp_path / "STACK.json").exists()


# ---------------------------------------------------------------------------
# GBrain integration — technical.json injection into system prompt
# ---------------------------------------------------------------------------

class TestGBrainIntegration:
    def test_system_prompt_includes_patterns_when_file_present(self, tmp_path):
        """GBrain patterns are prepended to SYSTEM_PROMPT before the LLM sees the idea."""
        patterns_file = tmp_path / "technical.json"
        patterns_file.write_text(json.dumps({
            "version": "0.1.0",
            "patterns": [{
                "id": "test-caching",
                "title": "Redis write-through caching pattern",
                "tags": ["redis", "cache", "performance"],
                "pattern": "Always use write-through caching for user session data.",
                "when_to_use": "Any endpoint that reads user session state.",
            }]
        }), encoding="utf-8")

        agent = ArchitectAgent(_gbrain_path=patterns_file)
        prompt = agent._system_prompt

        assert "Learned patterns from previous builds" in prompt
        assert "Redis write-through caching pattern" in prompt
        assert "Always use write-through caching" in prompt
        # Patterns must appear BEFORE the core system prompt
        assert prompt.index("Learned patterns") < prompt.index("You are the ArchitectAgent")

    def test_agent_runs_cleanly_when_gbrain_missing(self, tmp_path, monkeypatch):
        """Missing technical.json must not crash — graceful fallback to base prompt."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        missing = tmp_path / "does_not_exist.json"

        agent = ArchitectAgent(_gbrain_path=missing)
        assert agent._gbrain_context == ""
        assert agent._system_prompt == SYSTEM_PROMPT

        # Full pipeline run also completes without error
        ctx = _ctx(tmp_path / "build")
        result = agent.run(ctx)
        assert result.status == "success"
