"""Tests for LaunchAgent and FalClient stub.

Unit tests only — no LLM calls, no API calls, no network.
LLM is patched via monkeypatch on _llm to return a minimal LLMResponse.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from models import LLMResponse, ProjectContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(tmp_path: Path, idea: str = "Build ContractForge") -> ProjectContext:
    ctx = ProjectContext.new(idea=idea, workdir=str(tmp_path))
    ctx.frontend_url = "https://contractforge.vercel.app"
    ctx.backend_url  = "https://contractforge.onrender.com"
    ctx.repo_url     = "https://github.com/xenaarch-dev/contractforge"
    return ctx


_FAKE_SECTIONS = """\
## Product Hunt Draft

Name: ContractForge
Tagline: AI contract generator for indie founders

### Gallery captions
1. Generate a contract in 60 seconds
2. Plain-language terms, lawyer-reviewed structure
3. Export PDF, share link instantly

### First comment
built this because i kept paying $300 for NDAs. now it's $0.

## Outreach Seed

| Handle | Platform | Context |
|--------|----------|---------|
| @indiehackers | x | indie founders who need contracts |

Run for each entry you want to queue:
    python3 agents/distribution/outreach_queue.py add --handle "@indiehackers" --platform "x"

## Launch Thread

[1/3] built contractforge — ai contract generator. nda in 60s, $29/mo.
[2/3] forgeos scaffolded next.js + fastapi + supabase. 0 manual code.
[3/3] live: https://contractforge.vercel.app — try it free.
"""


def _fake_llm_response() -> LLMResponse:
    return LLMResponse(
        text=_FAKE_SECTIONS,
        model="test-model",
        prompt_tokens=100,
        completion_tokens=200,
        cost_usd=0.001,
    )


# ---------------------------------------------------------------------------
# LaunchAgent class-level attributes
# ---------------------------------------------------------------------------

class TestLaunchAgentAttrs:
    def test_name(self):
        from agents.launch import LaunchAgent
        assert LaunchAgent.name == "launch"

    def test_phase(self):
        from agents.launch import LaunchAgent
        assert LaunchAgent.phase == "launch"

    def test_capabilities(self):
        from agents.launch import LaunchAgent
        assert LaunchAgent.capabilities == ["LAUNCH.md"]

    def test_requires_contains_all_fields(self):
        from agents.launch import LaunchAgent
        required = set(LaunchAgent.requires)
        assert required >= {"idea", "project_id", "spec", "frontend_url", "backend_url", "repo_url"}

    def test_budget_usd_unlimited(self):
        from agents.launch import LaunchAgent
        assert LaunchAgent.budget_usd == 0.0

    def test_tools_empty(self):
        from agents.launch import LaunchAgent
        assert LaunchAgent.tools == []


# ---------------------------------------------------------------------------
# _render_launch_md (pure function, no agent needed)
# ---------------------------------------------------------------------------

class TestRenderLaunchMd:
    def test_draft_header_present(self):
        from agents.launch import _render_launch_md
        md = _render_launch_md(_FAKE_SECTIONS, "proj_abc", "https://example.com")
        assert "> DRAFT" in md

    def test_project_id_in_header(self):
        from agents.launch import _render_launch_md
        md = _render_launch_md(_FAKE_SECTIONS, "proj_abc123", "https://example.com")
        assert "proj_abc123" in md

    def test_checklist_present(self):
        from agents.launch import _render_launch_md
        md = _render_launch_md(_FAKE_SECTIONS, "proj_abc", "https://example.com")
        assert "## Checklist" in md
        assert "- [ ]" in md

    def test_campaign_videos_section_present(self):
        from agents.launch import _render_launch_md
        md = _render_launch_md(_FAKE_SECTIONS, "proj_abc", "")
        assert "## Campaign Videos" in md
        assert "build_a_brand" in md
        assert "app_screens" in md
        assert "product_sizzle" in md


# ---------------------------------------------------------------------------
# LaunchAgent._execute integration (LLM mocked)
# ---------------------------------------------------------------------------

class TestLaunchAgentRun:
    def test_writes_launch_md_to_workdir(self, tmp_path, monkeypatch):
        from agents.launch import LaunchAgent
        ctx = _ctx(tmp_path)
        monkeypatch.setattr(LaunchAgent, "_llm", lambda self, ctx, prompt, **kw: _fake_llm_response())
        result = LaunchAgent().run(ctx)
        assert result.status == "success"
        assert (tmp_path / "LAUNCH.md").exists()

    def test_writes_launch_md_to_project_dir(self, tmp_path, monkeypatch):
        from agents.launch import LaunchAgent
        ctx = _ctx(tmp_path)
        (tmp_path / "project").mkdir()
        monkeypatch.setattr(LaunchAgent, "_llm", lambda self, ctx, prompt, **kw: _fake_llm_response())
        LaunchAgent().run(ctx)
        assert (tmp_path / "project" / "LAUNCH.md").exists()

    def test_skips_project_write_if_dir_absent(self, tmp_path, monkeypatch):
        from agents.launch import LaunchAgent
        ctx = _ctx(tmp_path)
        monkeypatch.setattr(LaunchAgent, "_llm", lambda self, ctx, prompt, **kw: _fake_llm_response())
        LaunchAgent().run(ctx)
        assert not (tmp_path / "project" / "LAUNCH.md").exists()

    def test_sets_metadata_flags(self, tmp_path, monkeypatch):
        from agents.launch import LaunchAgent
        ctx = _ctx(tmp_path)
        monkeypatch.setattr(LaunchAgent, "_llm", lambda self, ctx, prompt, **kw: _fake_llm_response())
        LaunchAgent().run(ctx)
        assert ctx.metadata.get("launch_draft_ready") is True
        assert ctx.metadata.get("launch_needs_review") is True

    def test_graceful_with_empty_urls(self, tmp_path, monkeypatch):
        from agents.launch import LaunchAgent
        ctx = ProjectContext.new("Minimal idea", str(tmp_path))
        monkeypatch.setattr(LaunchAgent, "_llm", lambda self, ctx, prompt, **kw: _fake_llm_response())
        result = LaunchAgent().run(ctx)
        assert result.status == "success"
        assert (tmp_path / "LAUNCH.md").exists()

    def test_icp_note_from_pm_output_in_prompt(self, tmp_path, monkeypatch):
        from agents.launch import LaunchAgent
        ctx = _ctx(tmp_path)
        ctx.metadata["pm_output"] = {"icp": "indie founders building SaaS in India"}
        captured_prompts: list[str] = []

        def fake_llm(self, ctx, prompt, **kw):
            captured_prompts.append(prompt)
            return _fake_llm_response()

        monkeypatch.setattr(LaunchAgent, "_llm", fake_llm)
        LaunchAgent().run(ctx)
        assert captured_prompts, "LLM was not called"
        assert "indie founders building SaaS in India" in captured_prompts[0]

    def test_launch_md_contains_draft_marker(self, tmp_path, monkeypatch):
        from agents.launch import LaunchAgent
        ctx = _ctx(tmp_path)
        monkeypatch.setattr(LaunchAgent, "_llm", lambda self, ctx, prompt, **kw: _fake_llm_response())
        LaunchAgent().run(ctx)
        content = (tmp_path / "LAUNCH.md").read_text(encoding="utf-8")
        assert "> DRAFT" in content


# ---------------------------------------------------------------------------
# FalClient stub
# ---------------------------------------------------------------------------

class TestFalClientStub:
    def test_not_ready_without_api_key(self, monkeypatch):
        from tools.fal_client import FalClient
        monkeypatch.delenv("FAL_API_KEY", raising=False)
        assert FalClient().is_ready() is False

    def test_ready_with_api_key(self, monkeypatch):
        from tools.fal_client import FalClient
        monkeypatch.setenv("FAL_API_KEY", "fal-test-key-abc")
        assert FalClient().is_ready() is True

    def test_generate_raises_not_implemented_without_key(self, monkeypatch):
        from tools.fal_client import FalClient
        monkeypatch.delenv("FAL_API_KEY", raising=False)
        with pytest.raises(NotImplementedError):
            FalClient().generate("build_a_brand", "test prompt")

    def test_generate_raises_value_error_for_unknown_type(self, monkeypatch):
        from tools.fal_client import FalClient
        monkeypatch.delenv("FAL_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Unknown asset_type"):
            FalClient().generate("founder_video", "test prompt")  # type: ignore[arg-type]

    def test_provider_defaults_to_pika(self, monkeypatch):
        from tools.fal_client import FalClient
        monkeypatch.delenv("FAL_VIDEO_PROVIDER", raising=False)
        assert FalClient()._provider == "pika"

    def test_provider_overridden_by_env(self, monkeypatch):
        from tools.fal_client import FalClient
        monkeypatch.setenv("FAL_VIDEO_PROVIDER", "higgsfield")
        assert FalClient()._provider == "higgsfield"
