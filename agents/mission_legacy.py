"""
Mission architecture for ForgeOS V2.

Replaces the monolithic CoderAgent with serial, feature-by-feature
execution. Three roles:

  MissionOrchestrator  — plans features + writes ValidationContract
  MissionWorker        — implements ONE feature (serial, clean context)
  MissionWorkerLoop    — BaseAgent that drives all workers in order
  MissionValidator     — adversarial, tests ValidationContract assertions
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

from models import MissionHandoff, ProjectContext, Task, TaskStatus
from .base import BaseAgent


_MISSION_SYSTEM = """\
You are a MissionWorker in ForgeOS. You implement exactly ONE feature at a time.
You write production-grade code — no placeholders, no TODOs, no stubs.
Each response is a sequence of fenced file blocks tagged with relative paths.

```path/to/file.py
# contents
```

Rules:
- Only write files relevant to THIS feature.
- Never truncate file contents — complete implementations only.
- Always include a test file for backend code.
"""

_VALIDATOR_SYSTEM = """\
You are an adversarial MissionValidator in ForgeOS.
You have NEVER seen this code before. You are testing it cold.
Verify each assertion in the ValidationContract independently.
Be strict. Do NOT give benefit of the doubt.
If you cannot confirm an assertion is implemented, mark it UNVERIFIED.
"""


class MissionOrchestrator(BaseAgent):
    """Plans the mission: breaks idea into features, writes ValidationContract."""

    name = "mission_orchestrator"
    phase = "planning"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        features = self._extract_features(context)
        contract = self._build_contract(context, features)
        context.metadata["validation_contract"] = contract
        contract_path = self._write(
            context,
            "VALIDATION_CONTRACT.json",
            json.dumps(contract, indent=2),
        )
        self._log(
            f"[mission_orchestrator] {len(contract['assertions'])} assertions, "
            f"{len(features)} features, threshold={contract['acceptance_threshold']}"
        )
        return {
            "features": features,
            "assertion_count": len(contract["assertions"]),
            "contract_path": str(contract_path),
        }

    def _extract_features(self, context: ProjectContext) -> list[str]:
        coder_tasks = [t for t in context.tasks if t.agent == "coder"]
        return [t.title for t in coder_tasks] or ["core application features"]

    def _build_contract(
        self, context: ProjectContext, features: list[str]
    ) -> dict[str, Any]:
        features_text = "\n".join(f"- {f}" for f in features)
        try:
            resp = self._llm(
                context,
                user_prompt=(
                    f"Generate a ValidationContract for this product.\n\n"
                    f"IDEA: {context.idea}\n\n"
                    f"FEATURES TO BUILD:\n{features_text}\n\n"
                    "Write 8-12 concrete, testable assertions. Each assertion must be\n"
                    "independently verifiable (HTTP response, file exists, UI element, etc.).\n\n"
                    "Return ONLY a JSON object:\n"
                    "{\n"
                    '  "assertions": [\n'
                    '    {"description": "GET / returns 200 with app name", "category": "api"},\n'
                    '    {"description": "POST /auth/signup creates user in database", "category": "auth"}\n'
                    "  ],\n"
                    '  "acceptance_threshold": 0.90\n'
                    "}"
                ),
                system_extra=(
                    "You are writing a quality contract. Be specific and measurable. "
                    "Categories: api, auth, ui, data, infra, security, perf."
                ),
                task_complexity="hard",
                task_type="architecture",
                purpose="mission.contract",
                max_tokens=1500,
                temperature=0.1,
            )
            data = self._extract_json_block(resp.text)
            if isinstance(data, dict) and "assertions" in data:
                return {
                    "project_id": context.project_id,
                    "assertions": data["assertions"],
                    "acceptance_threshold": float(
                        data.get("acceptance_threshold", 0.90)
                    ),
                }
        except Exception as e:
            self._log(f"[mission_orchestrator] LLM contract failed, using baseline: {e}")

        return {
            "project_id": context.project_id,
            "assertions": [
                {"description": "GET /healthz returns 200 with status ok", "category": "api"},
                {"description": "POST /api/auth/signup creates user and returns JWT", "category": "auth"},
                {"description": "GET /api/items requires authentication (401 if missing)", "category": "auth"},
                {"description": "Frontend root page loads without console errors", "category": "ui"},
                {"description": "Frontend auth page has signup and login forms", "category": "ui"},
                {"description": "All pages mobile responsive at 375px viewport", "category": "ui"},
            ],
            "acceptance_threshold": 0.85,
        }


class MissionWorker:
    """
    Implements ONE feature. Not a BaseAgent — called by MissionWorkerLoop.

    Strategy (in order):
      1. Claude Code CLI (--print --dangerously-skip-permissions) if available
      2. Direct LLM call (same quality bar, no CLI dependency)
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

        next_feat = (
            f"feature {self.feature_index + 2}"
            if self.feature_index + 1 < self.total_features
            else "validation"
        )
        return MissionHandoff(
            agent="worker",
            feature=self.feature_title,
            completed=files_written or new_files,
            skipped=[],
            issues=[],
            commands_run=[f"git commit -m 'feat: {self.feature_title[:60]}'"],
            next_feature=next_feat,
        )

    # ------------------------------------------------------------------
    # Implementation strategies
    # ------------------------------------------------------------------

    def _try_claude_code(
        self, context: ProjectContext, project_dir: Path
    ) -> list[str] | None:
        claude_bin = shutil.which("claude")
        if not claude_bin:
            return None

        inventory = _inventory(project_dir)
        prompt = (
            f"Implement this feature for the project: {context.idea}\n\n"
            f"FEATURE: {self.feature_title}\n\n"
            f"EXISTING FILES:\n{inventory}\n\n"
            f"SPEC EXCERPT:\n{(context.spec or '')[:1000]}\n\n"
            "Write complete, production-ready code. Include tests. "
            "No TODOs. No placeholders. No ellipsis."
        )
        try:
            result = subprocess.run(
                [claude_bin, "--print", "--dangerously-skip-permissions", prompt],
                capture_output=True,
                text=True,
                cwd=str(project_dir),
                timeout=480,
            )
            if result.returncode == 0:
                after = _list_files(project_dir)
                sys.stderr.write(
                    f"[worker] claude code completed for: {self.feature_title}\n"
                )
                return after
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            sys.stderr.write(f"[worker] claude CLI unavailable: {e}\n")

        return None

    def _llm_fallback(
        self, context: ProjectContext, project_dir: Path
    ) -> list[str]:
        from llm.router import complete as llm_complete

        inventory = _inventory(project_dir)
        resp = llm_complete(
            context=context,
            user=(
                f"FEATURE: {self.feature_title}\n\n"
                f"IDEA: {context.idea}\n\n"
                f"EXISTING FILES:\n{inventory}\n\n"
                "Implement this feature end-to-end. Output fenced code blocks "
                "tagged with relative paths. Cover implementation AND tests. "
                "No truncation, no TODOs."
            ),
            system_extra=_MISSION_SYSTEM,
            task_complexity="medium",
            task_type="code",
            purpose=f"worker.{self.feature_index}",
            max_tokens=6000,
            temperature=0.15,
            stream=True,
        )

        files = _split_files(resp.text)
        written: list[str] = []
        root = project_dir.resolve()

        for relpath, content in files.items():
            rel = relpath.strip().lstrip("/")
            if not rel:
                continue
            target = (project_dir / rel).resolve()
            if not target.is_relative_to(root):
                sys.stderr.write(f"[worker] blocked path: {rel}\n")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written.append(rel)

        return written

    # ------------------------------------------------------------------
    # Git checkpoint
    # ------------------------------------------------------------------

    def _git_commit(self, project_dir: Path, feature: str) -> None:
        try:
            subprocess.run(
                ["git", "init"], cwd=str(project_dir), capture_output=True
            )
            subprocess.run(
                ["git", "add", "-A"], cwd=str(project_dir), capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"feat: {feature[:70]}", "--allow-empty"],
                cwd=str(project_dir),
                capture_output=True,
            )
        except Exception as e:
            sys.stderr.write(f"[worker] git commit failed (non-fatal): {e}\n")


class MissionWorkerLoop(BaseAgent):
    """BaseAgent that drives all MissionWorkers serially."""

    name = "mission_worker_loop"
    phase = "code"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        project_root = Path(context.workdir) / "project"
        if not project_root.exists():
            raise RuntimeError("Project scaffold missing — run ScaffoldAgent first")

        coder_tasks = [t for t in context.tasks if t.agent == "coder"]
        if not coder_tasks:
            self._log("[worker_loop] no coder tasks — skipping")
            return {"features_completed": 0, "features_total": 0}

        handoffs: list[dict[str, Any]] = []
        completed = 0

        for i, task in enumerate(coder_tasks):
            task.status = TaskStatus.IN_PROGRESS.value
            context.save()

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

            context.save()

        context.metadata["mission_handoffs"] = handoffs
        return {
            "features_completed": completed,
            "features_total": len(coder_tasks),
            "handoffs": handoffs,
        }


class MissionValidator(BaseAgent):
    """Adversarial validator — tests every assertion in the ValidationContract."""

    name = "mission_validator"
    phase = "qa"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        contract = context.metadata.get("validation_contract", {})
        assertions = contract.get("assertions", [])
        threshold = float(contract.get("acceptance_threshold", 0.90))

        if not assertions:
            self._log("[validator] no contract found — writing one first")
            mo = MissionOrchestrator()
            mo._execute(context)
            contract = context.metadata.get("validation_contract", {})
            assertions = contract.get("assertions", [])

        inventory = _inventory(Path(context.workdir) / "project")
        assertions_text = "\n".join(
            f"  [{i + 1}] [{a.get('category', '?')}] {a.get('description', a)}"
            if isinstance(a, dict)
            else f"  [{i + 1}] {a}"
            for i, a in enumerate(assertions)
        )

        result_list: list[dict[str, Any]] = []
        try:
            resp = self._llm(
                context,
                user_prompt=(
                    f"Validate this codebase against the ValidationContract.\n\n"
                    f"IDEA: {context.idea}\n\n"
                    f"ASSERTIONS:\n{assertions_text}\n\n"
                    f"GENERATED FILES:\n{inventory}\n\n"
                    "For each assertion output: [N] VERIFIED | UNVERIFIED | PARTIAL — reason\n\n"
                    "Then output ONLY this JSON:\n"
                    "```json\n"
                    '{"results": [{"assertion": "...", "status": "VERIFIED|UNVERIFIED|PARTIAL"'
                    ', "reason": "..."}]}\n'
                    "```"
                ),
                system_extra=_VALIDATOR_SYSTEM,
                task_complexity="hard",
                task_type="review",
                purpose="validator.check",
                max_tokens=3000,
                temperature=0.1,
            )
            data = self._extract_json_block(resp.text)
            if isinstance(data, dict) and "results" in data:
                result_list = data["results"]
        except Exception as e:
            self._log(f"[validator] LLM failed: {e}")

        verified = sum(
            1 for r in result_list if r.get("status") == "VERIFIED"
        )
        total = len(result_list) or len(assertions)
        acceptance = verified / total if total > 0 else 0.0
        passed = acceptance >= threshold

        self._log(
            f"[validator] {verified}/{total} verified ({acceptance:.0%}) "
            f"threshold={threshold:.0%} -> {'PASS' if passed else 'FAIL'}"
        )

        if not passed:
            context.metadata["validator_needs_correction"] = True
            context.metadata["validator_unverified"] = [
                r for r in result_list if r.get("status") != "VERIFIED"
            ]

        return {
            "assertions_total": total,
            "assertions_verified": verified,
            "acceptance_rate": round(acceptance, 4),
            "threshold": threshold,
            "passed": passed,
            "results": result_list,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inventory(project_root: Path, max_files: int = 60) -> str:
    if not project_root.exists():
        return "(empty)"
    rows: list[str] = []
    for p in sorted(project_root.rglob("*")):
        if any(
            part in {".git", "node_modules", ".venv", "__pycache__", ".next"}
            for part in p.parts
        ):
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
        if any(
            part in {".git", "node_modules", ".venv", "__pycache__", ".next"}
            for part in p.parts
        ):
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
        content = m.group(2)
        if not header or " " in header.split(":", 1)[0]:
            continue
        if "/" not in header and "." not in header:
            continue
        files[header] = content
    return files


__all__ = [
    "MissionOrchestrator",
    "MissionValidator",
    "MissionWorker",
    "MissionWorkerLoop",
]
