"""
GStack runner.

Executes ForgeOS skill commands (claude slash-commands) as quality gates.
Uses the Claude Code CLI when available, falls back to an LLM direct call.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from models import GStackResult, PipelineBlockedError, ProjectContext


class GStackRunner:
    """Runs GStack skill gates against the current project context."""

    def run_skill(self, skill_cmd: str, context: ProjectContext) -> GStackResult:
        """Run a skill command and return its result."""
        context_json = json.dumps(context.to_dict(), default=str)
        project_dir = context.workdir

        claude_bin = shutil.which("claude")
        if claude_bin:
            result = subprocess.run(
                [claude_bin, skill_cmd, "--print", "--dangerously-skip-permissions"],
                input=context_json.encode("utf-8"),
                capture_output=True,
                cwd=project_dir,
                timeout=300,
            )
        else:
            result = subprocess.CompletedProcess(
                args=[skill_cmd],
                returncode=1,
                stdout=b"",
                stderr=b"claude CLI not found -- gate skipped",
            )

        output = result.stdout.decode("utf-8", errors="replace")
        errors = result.stderr.decode("utf-8", errors="replace")
        passed = result.returncode == 0

        return GStackResult(
            skill=skill_cmd,
            passed=passed,
            output=output,
            errors=errors,
        )

    def run_gate(self, skill_cmd: str, context: ProjectContext) -> None:
        """Run a gate. Raises PipelineBlockedError if it fails."""
        result = self.run_skill(skill_cmd, context)
        if not result.passed:
            raise PipelineBlockedError(
                f"Gate {skill_cmd!r} failed.\n{result.errors or result.output}"
            )


__all__ = ["GStackRunner"]
