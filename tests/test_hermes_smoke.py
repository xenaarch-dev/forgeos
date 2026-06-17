"""Smoke test: HermesOrchestrator imports cleanly and run() completes.

Specifically guards against import-time failures (missing model classes)
that crash the pipeline before any agent runs. The real _build_pipeline()
is called so all lazy agent imports -- including the agents.sandbox chain
that triggered the original SandboxResult ImportError -- are exercised.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_hermes_run_completes_on_trivial_idea(tmp_path: Path) -> None:
    from agents.hermes import HermesOrchestrator
    from models import AgentResult, AgentStatus

    orch = HermesOrchestrator(idea="Build a todo list", workdir=str(tmp_path))

    # Call the real _build_pipeline() — this is where all lazy agent imports
    # happen. If any model class is missing (e.g. SandboxResult), the
    # ImportError surfaces here, not during the drainer dry run.
    real_stages = orch._build_pipeline()
    assert len(real_stages) > 0, "_build_pipeline() returned empty list"

    # Stub every agent so no LLM calls happen.
    ok_result = AgentResult.started("stub")
    ok_result.finalize(AgentStatus.SUCCESS, output={"ok": True})
    stub_cls = MagicMock()
    stub_cls.return_value.run.return_value = ok_result
    stubbed = [{**s, "cls": stub_cls} for s in real_stages]

    with (
        patch.object(orch, "_build_pipeline", return_value=stubbed),
        patch.object(orch, "_write_obsidian"),
        patch.object(orch, "_append_dataset"),
    ):
        ctx = orch.run()

    assert ctx.idea == "Build a todo list"
    assert (tmp_path / "context.json").exists()
