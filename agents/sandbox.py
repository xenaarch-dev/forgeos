"""
ForgeOS e2b sandbox wrapper.

Every MissionWorker code execution goes through this sandbox.
Sandbox spins up per worker, tears down on handoff complete.
On sandbox exception: write to FAILURE.md, retry once.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any

from models import SandboxResult


class ForgeOSSandbox:
    """
    Isolated code execution sandbox backed by e2b.
    Falls back to a subprocess-based local sandbox when E2B_API_KEY is absent.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or _get_api_key()
        self._use_e2b = bool(self._api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, code: str, context: Any = None) -> SandboxResult:
        """Run code in isolation. Returns SandboxResult."""
        if self._use_e2b:
            return self._e2b_execute(code)
        return self._local_execute(code)

    def execute_and_verify(self, code: str, test_cmd: str) -> SandboxResult:
        """Run code then run a test command. Returns combined result."""
        run_result = self.execute(code)
        if not run_result.success:
            return run_result

        verify_result = self._run_command(test_cmd)
        return SandboxResult(
            success=verify_result.success,
            output=run_result.output + "\n--- verify ---\n" + verify_result.output,
            errors=verify_result.errors,
            exit_code=verify_result.exit_code,
        )

    # ------------------------------------------------------------------
    # e2b backend
    # ------------------------------------------------------------------

    def _e2b_execute(self, code: str) -> SandboxResult:
        try:
            from e2b_code_interpreter import Sandbox

            with Sandbox(api_key=self._api_key) as sbx:
                execution = sbx.run_code(code)
                output = "\n".join(str(o) for o in (execution.logs.stdout or []))
                errors = "\n".join(str(e) for e in (execution.logs.stderr or []))
                success = not execution.error
                if execution.error:
                    errors += f"\n{execution.error}"
                return SandboxResult(
                    success=success,
                    output=output,
                    errors=errors,
                    exit_code=0 if success else 1,
                )
        except Exception as e:
            return SandboxResult(
                success=False,
                output="",
                errors=f"e2b execution failed: {e}",
                exit_code=1,
            )

    # ------------------------------------------------------------------
    # Local subprocess fallback
    # ------------------------------------------------------------------

    def _local_execute(self, code: str) -> SandboxResult:
        import subprocess, tempfile, os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            fname = f.name
        try:
            result = subprocess.run(
                [sys.executable, fname],
                capture_output=True,
                timeout=60,
            )
            return SandboxResult(
                success=result.returncode == 0,
                output=result.stdout.decode("utf-8", errors="replace"),
                errors=result.stderr.decode("utf-8", errors="replace"),
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(success=False, output="", errors="timeout", exit_code=1)
        except Exception as e:
            return SandboxResult(success=False, output="", errors=str(e), exit_code=1)
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass

    def _run_command(self, cmd: str) -> SandboxResult:
        import subprocess, shlex

        try:
            result = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                timeout=60,
            )
            return SandboxResult(
                success=result.returncode == 0,
                output=result.stdout.decode("utf-8", errors="replace"),
                errors=result.stderr.decode("utf-8", errors="replace"),
                exit_code=result.returncode,
            )
        except Exception as e:
            return SandboxResult(success=False, output="", errors=str(e), exit_code=1)


def _get_api_key() -> str:
    import os

    return os.environ.get("E2B_API_KEY", "")


__all__ = ["ForgeOSSandbox"]
