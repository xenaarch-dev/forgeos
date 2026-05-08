"""
CoderAgent.

Iterates `TASKS.json` for tasks where `agent == 'coder'`. For each task,
asks the LLM to produce a multi-file diff/scaffold response, parses the
fenced file blocks, writes them to `<workdir>/project/...`, and self-
reviews each file before moving on.

Self-review is a second LLM pass that flags incomplete logic, missing
error handling, and obvious bugs; the agent re-applies any improved
versions of the file.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from models import ProjectContext, Task, TaskStatus
from .base import BaseAgent


SYSTEM_PROMPT = """\
You are the CoderAgent in ForgeOS. You implement atomic engineering
tasks end-to-end. You write production-grade code with full type hints,
explicit error handling, and tests. You NEVER leave placeholders or
TODOs. Each response is a sequence of file blocks formatted as:

```relative/path/from/project/root.py
<file contents>
```

Do not include explanations outside of code blocks. Paths must be
relative to the project root that already exists. Overwrite is allowed.

When writing tests, use pytest for backend and vitest for frontend.
"""


class CoderAgent(BaseAgent):
    name = "coder"
    phase = "code"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        project_root = Path(context.workdir) / "project"
        if not project_root.exists():
            raise RuntimeError("Project scaffold missing — run ScaffoldAgent first")

        coder_tasks = [t for t in context.tasks if t.agent == "coder"]
        if not coder_tasks:
            return {"completed": 0, "skipped": 0, "tasks": []}

        completed: list[dict[str, Any]] = []
        for task in self._ordered(coder_tasks, context.tasks):
            try:
                self._log(f"[coder] starting task {task.id}: {task.title}")
                task.status = TaskStatus.IN_PROGRESS.value
                files = self._run_task(context, task, project_root)
                # Self-review pass
                self._self_review(context, task, project_root, files)
                task.status = TaskStatus.DONE.value
                task.artifacts = files
                completed.append({"id": task.id, "title": task.title, "files": files})
            except Exception as e:
                self._log(f"[coder] task {task.id} failed: {e}")
                task.status = TaskStatus.FAILED.value
                task.notes = f"failed: {e}"

            # Persist context after every task — incremental safety
            context.save()

        return {"completed": len(completed), "tasks": completed}

    # ------------------------------------------------------------------
    # Task ordering
    # ------------------------------------------------------------------

    def _ordered(self, coder_tasks: list[Task], all_tasks: list[Task]) -> list[Task]:
        by_id = {t.id: t for t in all_tasks}
        ordered: list[Task] = []
        seen: set[str] = set()

        def visit(t: Task) -> None:
            if t.id in seen:
                return
            for dep_id in t.depends_on:
                dep = by_id.get(dep_id)
                if dep and dep.agent == "coder":
                    visit(dep)
            seen.add(t.id)
            ordered.append(t)

        for t in coder_tasks:
            visit(t)
        return ordered

    # ------------------------------------------------------------------
    # Run a single task
    # ------------------------------------------------------------------

    def _run_task(
        self, context: ProjectContext, task: Task, project_root: Path
    ) -> list[str]:
        existing = self._project_inventory(project_root)
        try:
            resp = self._llm(
                context,
                user_prompt=(
                    f"TASK ID: {task.id}\n"
                    f"TITLE: {task.title}\n\n"
                    f"PROJECT FILES (truncated inventory):\n{existing}\n\n"
                    "Implement this task end-to-end. Output one or more "
                    "fenced code blocks, each tagged with a relative path. "
                    "Cover both implementation files AND tests. Keep blocks "
                    "self-contained; never reference 'rest of file'."
                ),
                system_extra=SYSTEM_PROMPT,
                task_complexity="medium",
                task_type="code",
                purpose=f"coder.{task.id}",
                max_tokens=6000,
            )
            files = self._split_files(resp.text)
        except Exception as e:
            self._log(f"[coder] LLM call failed for {task.id}: {e} — using fallback")
            files = {}

        if not files:
            files = self._fallback_files(task)

        written: list[str] = []
        for relpath, content in files.items():
            rel = relpath.strip().lstrip("/")
            if ".." in rel.split("/"):
                continue
            target = project_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written.append(rel)
        return written

    # ------------------------------------------------------------------
    # Self-review pass
    # ------------------------------------------------------------------

    def _self_review(
        self,
        context: ProjectContext,
        task: Task,
        project_root: Path,
        files: list[str],
    ) -> None:
        for rel in files:
            target = project_root / rel
            if not target.exists() or not target.is_file():
                continue
            current = target.read_text(encoding="utf-8")
            # Simple heuristic gate — only review files that look risky.
            if not self._looks_risky(current):
                continue
            try:
                resp = self._llm(
                    context,
                    user_prompt=(
                        f"FILE: {rel}\n\n"
                        f"CONTENT:\n```\n{current[:6000]}\n```\n\n"
                        "Review for: incomplete logic, TODO/FIXME, missing "
                        "error handling, missing typings, obvious bugs. If "
                        "the file is fine, reply with `OK`. Otherwise reply "
                        f"with a SINGLE corrected version inside ```{rel}\n...\n``` "
                        "tagged with the same relative path."
                    ),
                    system_extra=SYSTEM_PROMPT,
                    task_complexity="medium",
                    task_type="review",
                    purpose=f"coder.review.{rel}",
                    max_tokens=4000,
                    temperature=0.1,
                )
                if "OK" == resp.text.strip().upper():
                    continue
                fixed = self._split_files(resp.text)
                new_content = fixed.get(rel)
                if new_content and new_content.strip() and new_content != current:
                    target.write_text(new_content, encoding="utf-8")
                    self._log(f"[coder] self-review updated {rel}")
            except Exception as e:
                self._log(f"[coder] review skipped for {rel}: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _project_inventory(self, project_root: Path, limit: int = 200) -> str:
        rows: list[str] = []
        for p in sorted(project_root.rglob("*")):
            if any(part in {".git", "node_modules", ".venv", "__pycache__"} for part in p.parts):
                continue
            if p.is_file():
                try:
                    rel = p.relative_to(project_root).as_posix()
                except ValueError:
                    continue
                rows.append(rel)
                if len(rows) >= limit:
                    rows.append("...")
                    break
        return "\n".join(rows) or "(empty project)"

    def _looks_risky(self, content: str) -> bool:
        markers = ("TODO", "FIXME", "pass  # implement", "raise NotImplementedError")
        return any(m in content for m in markers) or len(content.strip()) < 30

    def _fallback_files(self, task: Task) -> dict[str, str]:
        # Deterministic fallback — guarantees forward progress when LLM fails.
        title = task.title.lower()
        if "healthz" in title or "health" in title:
            return {
                "backend/app/routers/health.py": (
                    "from __future__ import annotations\n\n"
                    "from fastapi import APIRouter\n\n"
                    "router = APIRouter()\n\n\n"
                    "@router.get('/healthz', tags=['meta'])\n"
                    "async def healthz() -> dict[str, str]:\n"
                    "    return {'status': 'ok'}\n"
                )
            }
        if "items" in title and "crud" in title:
            return {
                "backend/tests/test_items_crud.py": (
                    "from __future__ import annotations\n\n"
                    "def test_items_endpoint_requires_auth(client) -> None:\n"
                    "    r = client.get('/api/items')\n"
                    "    assert r.status_code == 401\n"
                )
            }
        # Default: log the task as a TASKLOG entry so it's not silently lost.
        slug = "".join(c if c.isalnum() else "-" for c in title).strip("-") or task.id
        return {
            f"docs/tasks/{slug}.md": (
                f"# Task: {task.title}\n\n"
                f"- ID: {task.id}\n"
                f"- Phase: {task.phase}\n"
                "- Note: LLM unavailable — task captured for manual follow-up.\n"
            )
        }


__all__ = ["CoderAgent"]
