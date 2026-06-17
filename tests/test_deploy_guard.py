"""
Tests for FORGEOS_AUTO_DEPLOY guard in DeployAgent._execute.

The guard is the single mechanism governing whether external deploys
run unattended. It must satisfy:
  - Deploy is SKIPPED when the env var is absent or '0'.
  - DEPLOYMENT.md is always written (skipped notice OR full report).
  - All external step helpers (GitHub / Render / Vercel / Sentry / Uptime)
    are NEVER called when guard is off.
  - When FORGEOS_AUTO_DEPLOY=1 and project_root exists, the agent proceeds
    to real deploy logic (steps may raise, which is fine — tested separately).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models import ProjectContext


def _ctx(tmp_path: Path) -> ProjectContext:
    ctx = ProjectContext.new(idea="Build a test SaaS", workdir=str(tmp_path))
    ctx.project_id = "test_proj_001"
    return ctx


# ---------------------------------------------------------------------------
# Guard OFF (default) — no env var
# ---------------------------------------------------------------------------

class TestDeployGuardOff:
    def test_returns_skipped_list(self, tmp_path, monkeypatch):
        from agents.deploy import DeployAgent
        monkeypatch.delenv("FORGEOS_AUTO_DEPLOY", raising=False)
        ctx = _ctx(tmp_path)
        result = DeployAgent().run(ctx)
        assert result.status == "success"
        skipped = result.output.get("skipped", [])
        assert "github" in skipped
        assert "render" in skipped or "vercel" in skipped

    def test_deployment_md_written_on_skip(self, tmp_path, monkeypatch):
        from agents.deploy import DeployAgent
        monkeypatch.delenv("FORGEOS_AUTO_DEPLOY", raising=False)
        ctx = _ctx(tmp_path)
        DeployAgent().run(ctx)
        md = (tmp_path / "DEPLOYMENT.md").read_text(encoding="utf-8")
        assert "FORGEOS_AUTO_DEPLOY" in md
        assert "skipped" in md.lower()

    def test_urls_empty_on_skip(self, tmp_path, monkeypatch):
        from agents.deploy import DeployAgent
        monkeypatch.delenv("FORGEOS_AUTO_DEPLOY", raising=False)
        ctx = _ctx(tmp_path)
        result = DeployAgent().run(ctx)
        assert result.output.get("repo_url") == ""
        assert result.output.get("backend_url") == ""
        assert result.output.get("frontend_url") == ""

    def test_no_external_calls_on_skip(self, tmp_path, monkeypatch):
        from agents.deploy import DeployAgent
        monkeypatch.delenv("FORGEOS_AUTO_DEPLOY", raising=False)
        ctx = _ctx(tmp_path)

        with patch("agents.deploy.GitHubClient") as mock_gh, \
             patch("agents.deploy.VercelClient") as mock_vc, \
             patch("agents.deploy.RenderClient") as mock_rc:
            DeployAgent().run(ctx)
            mock_gh.assert_not_called()
            mock_vc.assert_not_called()
            mock_rc.assert_not_called()

    def test_guard_off_when_set_to_zero(self, tmp_path, monkeypatch):
        from agents.deploy import DeployAgent
        monkeypatch.setenv("FORGEOS_AUTO_DEPLOY", "0")
        ctx = _ctx(tmp_path)
        result = DeployAgent().run(ctx)
        assert "github" in result.output.get("skipped", [])

    def test_note_in_output(self, tmp_path, monkeypatch):
        from agents.deploy import DeployAgent
        monkeypatch.delenv("FORGEOS_AUTO_DEPLOY", raising=False)
        ctx = _ctx(tmp_path)
        result = DeployAgent().run(ctx)
        assert "FORGEOS_AUTO_DEPLOY=1" in result.output.get("note", "")


# ---------------------------------------------------------------------------
# Guard ON — FORGEOS_AUTO_DEPLOY=1
# ---------------------------------------------------------------------------

class TestDeployGuardOn:
    def test_proceeds_to_deploy_logic_when_set(self, tmp_path, monkeypatch):
        """When guard is on and project_root missing, agent raises RuntimeError."""
        from agents.deploy import DeployAgent
        monkeypatch.setenv("FORGEOS_AUTO_DEPLOY", "1")
        ctx = _ctx(tmp_path)
        # project/ directory does not exist — agent should raise
        result = DeployAgent().run(ctx)
        assert result.status == "failed"
        assert "Project missing" in (result.error or "")

    def test_project_root_checked_after_guard(self, tmp_path, monkeypatch):
        """Guard passes, but runtime error comes from missing project/ not guard."""
        from agents.deploy import DeployAgent
        monkeypatch.setenv("FORGEOS_AUTO_DEPLOY", "1")
        ctx = _ctx(tmp_path)
        result = DeployAgent().run(ctx)
        # The guard is NOT the reason for failure
        assert "FORGEOS_AUTO_DEPLOY" not in (result.error or "")
        assert "Project missing" in (result.error or "")

    def test_guard_on_does_not_write_skip_notice(self, tmp_path, monkeypatch):
        """When guard is on, DEPLOYMENT.md should NOT say 'deploy skipped'."""
        from agents.deploy import DeployAgent
        monkeypatch.setenv("FORGEOS_AUTO_DEPLOY", "1")
        # Create a project dir so we get past the root check, then let steps fail
        (tmp_path / "project").mkdir()
        ctx = _ctx(tmp_path)

        with patch.object(DeployAgent, "_step_github", side_effect=RuntimeError("no token")), \
             patch.object(DeployAgent, "_step_render", side_effect=RuntimeError("no token")), \
             patch.object(DeployAgent, "_step_vercel", side_effect=RuntimeError("no token")), \
             patch.object(DeployAgent, "_step_sentry", side_effect=RuntimeError("no token")), \
             patch.object(DeployAgent, "_step_uptime", side_effect=RuntimeError("no token")):
            result = DeployAgent().run(ctx)

        assert result.status == "success"
        if (tmp_path / "DEPLOYMENT.md").exists():
            md = (tmp_path / "DEPLOYMENT.md").read_text(encoding="utf-8")
            assert "Deploy skipped" not in md
