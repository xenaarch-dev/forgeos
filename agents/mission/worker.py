"""
MissionWorker and MissionWorkerLoop -- feature-by-feature code generation.
Each worker handles ONE feature in a fresh context.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from models import MissionHandoff, ProjectContext, TaskStatus
from agents.base import BaseAgent
from agents.sandbox import ForgeOSSandbox


class MissionWorker:
    """
    Implements ONE feature. Called by MissionWorkerLoop.
    Strategy: Claude Code CLI first, direct LLM fallback.
    """

    def __init__(
        self, feature_title: str, feature_index: int, total_features: int
    ) -> None:
        self.feature_title = feature_title
        self.feature_index = feature_index
        self.total_features = total_features

    def run(self, context: ProjectContext) -> MissionHandoff:
        project_dir = Path(context.workdir) / "project"
        project_dir.mkdir(parents=True, exist_ok=True)

        sys.stderr.write(
            f"[worker] feature {self.feature_index + 1}/{self.total_features}: "
            f"{self.feature_title}\n"
        )
        sys.stderr.flush()

        files_before = _list_files(project_dir)
        files_written = (
            self._try_claude_code(context, project_dir)
            or self._llm_fallback(context, project_dir)
        )
        files_after = _list_files(project_dir)
        new_files = [f for f in files_after if f not in set(files_before)]

        self._git_commit(project_dir, self.feature_title)

        # Write handoff JSON
        handoff_dir = Path(context.workdir) / ".forgeos" / "handoffs"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        import time
        handoff = MissionHandoff(
            agent="worker",
            feature=self.feature_title,
            completed=files_written or new_files,
            skipped=[],
            issues=[],
            commands_run=[f"git commit -m 'feat: {self.feature_title[:60]}'"],
            next_feature=(
                f"feature {self.feature_index + 2}"
                if self.feature_index + 1 < self.total_features
                else "validation"
            ),
        )
        (handoff_dir / f"worker_{self.feature_index}.json").write_text(
            json.dumps(asdict(handoff), indent=2, default=str), encoding="utf-8"
        )

        return handoff

    def _try_claude_code(
        self, context: ProjectContext, project_dir: Path
    ) -> list[str] | None:
        claude_bin = shutil.which("claude")
        if not claude_bin:
            return None
        try:
            result = subprocess.run(
                [
                    claude_bin,
                    "--print",
                    "--dangerously-skip-permissions",
                    (
                        f"Implement this feature for the project in {project_dir}:\n"
                        f"FEATURE: {self.feature_title}\n"
                        f"IDEA: {context.idea}\n\n"
                        "Write all necessary files. No placeholders. Full implementations only."
                    ),
                ],
                capture_output=True,
                timeout=300,
                cwd=str(project_dir),
            )
            if result.returncode != 0:
                return None
            output = result.stdout.decode("utf-8", errors="replace")
            return _extract_written_files(output, project_dir)
        except Exception:
            return None

    def _llm_fallback(
        self, context: ProjectContext, project_dir: Path
    ) -> list[str]:
        from llm.router import complete as llm_complete
        from agents.base import BaseAgent

        inventory = _inventory(project_dir)
        try:
            resp = llm_complete(
                context=context,
                user=(
                    f"FEATURE: {self.feature_title}\n"
                    f"IDEA: {context.idea}\n\n"
                    f"EXISTING FILES:\n{inventory}\n\n"
                    "Implement this feature. Return fenced file blocks tagged with relative paths. "
                    "No placeholders. Full implementations only."
                ),
                system_extra=_WORKER_SYSTEM,
                task_complexity="medium",
                task_type="code",
                purpose=f"worker.{self.feature_index}",
                max_tokens=6000,
            )
            files = _split_files(resp.text)
        except Exception:
            files = {}

        written: list[str] = []
        for relpath, file_content in files.items():
            rel = relpath.strip().lstrip("/")
            if not rel:
                continue
            target = (project_dir / rel).resolve()
            if not target.is_relative_to(project_dir.resolve()):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file_content, encoding="utf-8")
            written.append(rel)
        return written

    def _git_commit(self, project_dir: Path, title: str) -> None:
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(project_dir),
                capture_output=True,
                timeout=30,
            )
            subprocess.run(
                ["git", "commit", "-m", f"feat: {title[:60]}"],
                cwd=str(project_dir),
                capture_output=True,
                timeout=30,
            )
        except Exception:
            pass


_WORKER_SYSTEM = """\
You are a MissionWorker in ForgeOS. Implement exactly ONE feature.
Write production-grade code -- no placeholders, no TODOs, no stubs.
Each response is a sequence of fenced file blocks tagged with relative paths.
"""


class MissionWorkerLoop(BaseAgent):
    """BaseAgent that drives all MissionWorkers serially, each in a fresh sandbox."""

    name = "mission_worker_loop"
    phase = "code"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        project_root = Path(context.workdir) / "project"
        if not project_root.exists():
            raise RuntimeError("Project scaffold missing -- run ScaffoldAgent first")

        coder_tasks = [t for t in context.tasks if t.agent == "coder"]
        if not coder_tasks:
            self._log("[worker_loop] no coder tasks -- skipping")
            return {"features_completed": 0, "features_total": 0}

        handoffs: list[dict[str, Any]] = []
        completed = 0

        for i, task in enumerate(coder_tasks):
            task.status = TaskStatus.IN_PROGRESS.value
            context.save()

            # Each task gets its own sandbox instance
            sandbox = ForgeOSSandbox()
            worker = MissionWorker(task.title, i, len(coder_tasks))

            try:
                handoff = worker.run(context)
                task.status = TaskStatus.DONE.value
                task.artifacts = handoff.completed
                handoffs.append(asdict(handoff))
                completed += 1
                self._log(
                    f"[worker_loop] {i + 1}/{len(coder_tasks)} done: {task.title}"
                )
            except Exception as e:
                task.status = TaskStatus.FAILED.value
                task.notes = str(e)
                self._log(f"[worker_loop] feature {i + 1} failed: {e}")
                # Record failure
                from models import PipelineBlockedError
                self._write_failure(context, task.title, str(e))

            context.save()

        context.metadata["mission_handoffs"] = handoffs
        return {
            "features_completed": completed,
            "features_total": len(coder_tasks),
            "handoffs": handoffs,
        }

    def _write_failure(self, context: ProjectContext, feature: str, error: str) -> None:
        import json
        from datetime import datetime, timezone
        failure = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": "mission_worker",
            "agent": self.name,
            "error": error,
            "context_idea": context.idea,
            "fix_attempted": "retry once",
            "resolved": False,
            "processed": False,
        }
        failure_path = Path(context.workdir) / "FAILURE.md"
        existing = ""
        if failure_path.exists():
            existing = failure_path.read_text(encoding="utf-8")
        failure_path.write_text(
            existing + "\n" + json.dumps(failure, indent=2) + "\n",
            encoding="utf-8",
        )


def _inventory(project_root: Path, max_files: int = 60) -> str:
    if not project_root.exists():
        return "(empty)"
    rows: list[str] = []
    for p in sorted(project_root.rglob("*")):
        if any(d in {".git", "node_modules", ".venv", "__pycache__", ".next"} for d in p.parts):
            continue
        if p.is_file():
            try:
                rows.append(p.relative_to(project_root).as_posix())
                if len(rows) >= max_files:
                    rows.append("...")
                    break
            except ValueError:
                continue
    return "\n".join(rows) or "(empty)"


def _list_files(project_root: Path) -> list[str]:
    if not project_root.exists():
        return []
    rows: list[str] = []
    for p in sorted(project_root.rglob("*")):
        if any(d in {".git", "node_modules", ".venv", "__pycache__", ".next"} for d in p.parts):
            continue
        if p.is_file():
            try:
                rows.append(p.relative_to(project_root).as_posix())
            except ValueError:
                pass
    return rows


def _split_files(text: str) -> dict[str, str]:
    files: dict[str, str] = {}
    pattern = re.compile(r"```([^\n`]+)\n(.*?)```", re.S)
    for m in pattern.finditer(text):
        header = m.group(1).strip()
        file_content = m.group(2)
        if not header or " " in header.split(":", 1)[0]:
            continue
        if "/" not in header and "." not in header:
            continue
        files[header] = file_content
    return files


def _extract_written_files(output: str, project_dir: Path) -> list[str]:
    written: list[str] = []
    pattern = re.compile(r"```([^\n`]+)\n(.*?)```", re.S)
    for m in pattern.finditer(output):
        header = m.group(1).strip()
        if "/" in header or "." in header:
            written.append(header)
    return written


__all__ = ["MissionWorker", "MissionWorkerLoop"]
