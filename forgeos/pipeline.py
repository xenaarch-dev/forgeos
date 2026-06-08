"""
Adapter: routes forgeos.cli commands to the root-level orchestrator.

Handles both editable installs (repo root already on sys.path) and
non-editable installs (resolves path relative to this file's location).
"""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_on_path() -> None:
    """Make root orchestrator.py importable regardless of install mode."""
    try:
        import orchestrator  # noqa: F401
        return
    except ImportError:
        pass
    repo_root = Path(__file__).resolve().parent.parent
    if (repo_root / "orchestrator.py").exists() and str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


_ensure_repo_on_path()


def run_build(idea: str, workdir: str | None = None, legacy: bool = False) -> int:
    """Run a ForgeOS build. Returns exit code (0 = success)."""
    from orchestrator import main as _main  # type: ignore[import]

    args = ["--idea", idea]
    if workdir:
        args += ["--workdir", workdir]
    if legacy:
        args += ["--legacy"]
    return _main(args) or 0
