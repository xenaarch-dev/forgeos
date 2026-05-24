"""
MissionOrchestrator — plans features and writes ValidationContract.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from models import MissionHandoff, ProjectContext, Task, TaskStatus
from agents.base import BaseAgent


_MISSION_SYSTEM = """\
You are a MissionWorker in ForgeOS. You implement exactly ONE feature at a time.
You write production-grade code -- no placeholders, no TODOs, no stubs.
Each response is a sequence of fenced file blocks tagged with relative paths.

```path/to/file.py
# contents
```

Rules:
- Only write files relevant to THIS feature.
- Never truncate file contents -- complete implementations only.
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
        # Also write to .forgeos/ subdir
        forgeos_dir = Path(context.workdir) / ".forgeos"
        forgeos_dir.mkdir(parents=True, exist_ok=True)
        (forgeos_dir / "ValidationContract.json").write_text(
            json.dumps(contract, indent=2), encoding="utf-8"
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
                    "Write 20+ concrete, testable assertions. Each assertion must be\n"
                    "independently verifiable (HTTP response, file exists, UI element, etc.).\n\n"
                    "Return ONLY a JSON object:\n"
                    "{\n"
                    '  "assertions": [\n'
                    '    {"description": "GET / returns 200 with app name", "category": "api"},\n'
                    '    {"description": "POST /auth/signup creates user", "category": "auth"}\n'
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
                max_tokens=2000,
                temperature=0.1,
            )
            data = self._extract_json_block(resp.text)
            if isinstance(data, dict) and "assertions" in data:
                assertions = data["assertions"]
                # Ensure 20+ assertions by adding baseline ones if needed
                baseline = _baseline_assertions()
                existing_descs = {a.get("description", "") for a in assertions if isinstance(a, dict)}
                for b in baseline:
                    if b["description"] not in existing_descs:
                        assertions.append(b)
                return {
                    "project_id": context.project_id,
                    "assertions": assertions[:30],
                    "acceptance_threshold": float(
                        data.get("acceptance_threshold", 0.90)
                    ),
                    "created_before_code": True,
                }
        except Exception as e:
            self._log(f"[mission_orchestrator] LLM contract failed, using baseline: {e}")

        return {
            "project_id": context.project_id,
            "assertions": _baseline_assertions(),
            "acceptance_threshold": 0.90,
            "created_before_code": True,
        }


def _baseline_assertions() -> list[dict[str, str]]:
    return [
        {"description": "GET / returns 200 with app name and version", "category": "api"},
        {"description": "GET /healthz returns 200 with status healthy", "category": "api"},
        {"description": "POST /api/auth/signup creates user and returns token", "category": "auth"},
        {"description": "POST /api/auth/login with valid creds returns JWT", "category": "auth"},
        {"description": "GET /api/items without auth returns 401", "category": "auth"},
        {"description": "POST /api/items with auth creates item", "category": "api"},
        {"description": "GET /api/items returns list of user items", "category": "api"},
        {"description": "PATCH /api/items/{id} updates item data", "category": "api"},
        {"description": "DELETE /api/items/{id} removes item", "category": "api"},
        {"description": "Frontend root page loads without JS errors", "category": "ui"},
        {"description": "Frontend auth page has signup and login forms", "category": "ui"},
        {"description": "Frontend dashboard shows items list", "category": "ui"},
        {"description": "All pages mobile responsive at 375px viewport", "category": "ui"},
        {"description": "Supabase RLS policies exist for all tables", "category": "security"},
        {"description": ".env file not committed to git", "category": "security"},
        {"description": "All mutating routes require authentication", "category": "security"},
        {"description": "Backend dockerfile builds without errors", "category": "infra"},
        {"description": "Frontend Next.js build completes without errors", "category": "infra"},
        {"description": "GitHub Actions CI workflow exists", "category": "infra"},
        {"description": "vercel.json exists in frontend directory", "category": "infra"},
        {"description": "Backend pytest suite has at least 5 tests", "category": "api"},
        {"description": "LemonSqueezy checkout link is present on pricing page", "category": "ui"},
    ]




def _inventory(project_dir: "Path") -> str:
    """Return a formatted file listing of the project directory."""
    from pathlib import Path as _Path
    project_dir = _Path(project_dir)
    if not project_dir.exists():
        return "(project directory not found)"
    _SKIP = {"__pycache__", "node_modules", ".next", "dist", ".git"}
    lines: list[str] = []
    for p in sorted(project_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(project_dir)
            parts = rel.parts
            if any(part.startswith(".") or part in _SKIP for part in parts):
                continue
            lines.append(str(rel))
    return "\n".join(lines) or "(no files)"

__all__ = ["MissionOrchestrator", "_inventory"]

