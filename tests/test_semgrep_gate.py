"""
SecurityAgent semgrep gate tests.

These tests cover:
  - _run_semgrep() finds ERROR-severity findings in a SQL-injection fixture.
  - _run_semgrep() returns [] for a clean fixture.
  - _run_semgrep() returns [] gracefully when semgrep is not installed.
  - CSOGate._evaluate() blocks immediately when semgrep blocking=True in metadata.
  - CSOGate._evaluate() proceeds to LLM evaluation when semgrep is clean.

The semgrep integration tests are marked @pytest.mark.integration and skip
when semgrep is not available on PATH or user-scripts dir.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agents.security import SecurityAgent
from agents.gstack import CSOGate
from models import GateResult, ProjectContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(tmp_path: Path, semgrep_meta: dict | None = None) -> ProjectContext:
    ctx = MagicMock(spec=ProjectContext)
    ctx.project_id = "test-proj"
    ctx.workdir = str(tmp_path)
    ctx.idea = "test idea"
    ctx.metadata = {}
    if semgrep_meta is not None:
        ctx.metadata["security"] = {"semgrep": semgrep_meta}
    return ctx


_SQLI_FIXTURE = textwrap.dedent("""\
    import sqlite3

    def get_user(username):
        conn = sqlite3.connect("app.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE name = '" + username + "'")
        return cur.fetchone()
""")

_CLEAN_FIXTURE = textwrap.dedent("""\
    def add(a: int, b: int) -> int:
        return a + b
""")


def _semgrep_available() -> bool:
    from agents.security import SecurityAgent
    agent = SecurityAgent()
    import shutil
    return bool(shutil.which("semgrep") or agent._find_semgrep_binary())


# ---------------------------------------------------------------------------
# Semgrep integration tests (real tool invocation)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSemgrepIntegration:
    def setup_method(self):
        if not _semgrep_available():
            pytest.skip("semgrep not installed — skipping integration tests")

    def test_sqli_fixture_produces_error_findings(self, tmp_path: Path):
        vuln_file = tmp_path / "sqli.py"
        vuln_file.write_text(_SQLI_FIXTURE, encoding="utf-8")

        agent = SecurityAgent()
        findings = agent._run_semgrep(tmp_path)

        error_findings = [
            f for f in findings
            if f.get("extra", {}).get("severity", "").upper() == "ERROR"
        ]
        assert len(error_findings) > 0, (
            f"Expected at least one ERROR finding for SQLi fixture, got: {findings}"
        )

    def test_clean_fixture_produces_no_error_findings(self, tmp_path: Path):
        clean_file = tmp_path / "clean.py"
        clean_file.write_text(_CLEAN_FIXTURE, encoding="utf-8")

        agent = SecurityAgent()
        findings = agent._run_semgrep(tmp_path)

        error_findings = [
            f for f in findings
            if f.get("extra", {}).get("severity", "").upper() == "ERROR"
        ]
        assert len(error_findings) == 0, (
            f"Expected no ERROR findings for clean fixture, got: {error_findings}"
        )

    def test_empty_directory_produces_no_findings(self, tmp_path: Path):
        agent = SecurityAgent()
        findings = agent._run_semgrep(tmp_path)
        assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# _run_semgrep unit tests (mocked subprocess)
# ---------------------------------------------------------------------------


class TestRunSemgrepUnit:
    def _agent(self) -> SecurityAgent:
        return SecurityAgent()

    def test_returns_empty_list_when_semgrep_not_found(self, tmp_path: Path):
        agent = self._agent()
        with patch("shutil.which", return_value=None), \
             patch.object(SecurityAgent, "_find_semgrep_binary", return_value=None):
            result = agent._run_semgrep(tmp_path)
        assert result == []

    def test_returns_findings_from_valid_json_output(self, tmp_path: Path):
        fake_output = json.dumps({
            "results": [
                {
                    "check_id": "python.lang.sqli",
                    "path": str(tmp_path / "app.py"),
                    "extra": {"severity": "ERROR", "message": "SQL injection"},
                }
            ],
            "errors": [],
        })
        agent = self._agent()
        with patch("shutil.which", return_value="/usr/bin/semgrep"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=fake_output, stderr="", returncode=1
            )
            result = agent._run_semgrep(tmp_path)

        assert len(result) == 1
        assert result[0]["check_id"] == "python.lang.sqli"
        assert result[0]["extra"]["severity"] == "ERROR"

    def test_returns_empty_on_json_parse_error(self, tmp_path: Path):
        agent = self._agent()
        with patch("shutil.which", return_value="/usr/bin/semgrep"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="not json", stderr="", returncode=0)
            result = agent._run_semgrep(tmp_path)
        assert result == []

    def test_returns_empty_on_timeout(self, tmp_path: Path):
        agent = self._agent()
        with patch("shutil.which", return_value="/usr/bin/semgrep"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("semgrep", 180)):
            result = agent._run_semgrep(tmp_path)
        assert result == []

    def test_returns_empty_on_subprocess_error(self, tmp_path: Path):
        agent = self._agent()
        with patch("shutil.which", return_value="/usr/bin/semgrep"), \
             patch("subprocess.run", side_effect=OSError("permission denied")):
            result = agent._run_semgrep(tmp_path)
        assert result == []

    def test_returns_empty_when_stdout_is_empty(self, tmp_path: Path):
        agent = self._agent()
        with patch("shutil.which", return_value="/usr/bin/semgrep"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            result = agent._run_semgrep(tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# CSOGate semgrep blocking tests
# ---------------------------------------------------------------------------


class TestCSOGateSemgrepBlock:
    def test_blocks_immediately_when_semgrep_has_critical_findings(self, tmp_path: Path):
        ctx = _make_context(
            tmp_path,
            semgrep_meta={
                "blocking": True,
                "critical_count": 2,
                "critical_findings": [
                    {"check_id": "python.lang.sqli", "path": "app.py",
                     "message": "SQL injection", "severity": "ERROR"},
                    {"check_id": "secrets.hardcoded-key", "path": "config.py",
                     "message": "Hardcoded secret", "severity": "ERROR"},
                ],
            },
        )
        gate = CSOGate()
        result = gate._evaluate(ctx)

        assert isinstance(result, GateResult)
        assert result.passed is False
        assert result.score == 0.0
        assert "2" in result.feedback
        assert "semgrep" in result.feedback.lower() or "Semgrep" in result.feedback

    def test_proceeds_to_llm_when_semgrep_clean(self, tmp_path: Path):
        ctx = _make_context(
            tmp_path,
            semgrep_meta={
                "blocking": False,
                "critical_count": 0,
                "critical_findings": [],
            },
        )
        # Mock the LLM call so we don't need real API keys.
        with patch("agents.gstack.llm_complete") as mock_llm, \
             patch("agents.gstack._read_artifact", return_value="# Security Report"), \
             patch("agents.gstack._get_code_inventory", return_value="app.py"):
            mock_llm.return_value = MagicMock(
                text="The code looks secure. SCORE: 8/10 PASS", model="test"
            )
            gate = CSOGate()
            result = gate._evaluate(ctx)

        assert mock_llm.called, "LLM should be called when semgrep is clean"
        assert result.passed is True

    def test_proceeds_to_llm_when_no_semgrep_metadata(self, tmp_path: Path):
        ctx = _make_context(tmp_path, semgrep_meta=None)

        with patch("agents.gstack.llm_complete") as mock_llm, \
             patch("agents.gstack._read_artifact", return_value=""), \
             patch("agents.gstack._get_code_inventory", return_value=""):
            mock_llm.return_value = MagicMock(
                text="Looks fine. SCORE: 7/10 PASS", model="test"
            )
            gate = CSOGate()
            result = gate._evaluate(ctx)

        assert mock_llm.called

    def test_check_id_appears_in_blocking_feedback(self, tmp_path: Path):
        ctx = _make_context(
            tmp_path,
            semgrep_meta={
                "blocking": True,
                "critical_count": 1,
                "critical_findings": [
                    {"check_id": "python.django.sqli", "path": "views.py",
                     "message": "Direct SQL", "severity": "ERROR"},
                ],
            },
        )
        gate = CSOGate()
        result = gate._evaluate(ctx)
        assert "python.django.sqli" in result.feedback
