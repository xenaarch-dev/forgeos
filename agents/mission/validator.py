"""
MissionValidator -- adversarial validation of the ValidationContract.
Tests every assertion, self-heals up to 3 times if below threshold.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from models import PipelineBlockedError, ProjectContext
from agents.base import BaseAgent
from .orchestrator import MissionOrchestrator, _inventory


_VALIDATOR_SYSTEM = """\
You are an adversarial MissionValidator in ForgeOS.
You have NEVER seen this code before. You are testing it cold.
Verify each assertion in the ValidationContract independently.
Be strict. Do NOT give benefit of the doubt.
If you cannot confirm an assertion is implemented, mark it UNVERIFIED.
"""

_MAX_SELF_HEALS = 3
_ACCEPTANCE_THRESHOLD = 0.95


class MissionValidator(BaseAgent):
    """Adversarial validator -- tests every assertion in the ValidationContract."""

    name = "mission_validator"
    phase = "qa"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        contract = context.metadata.get("validation_contract", {})
        assertions = contract.get("assertions", [])
        threshold = max(
            float(contract.get("acceptance_threshold", _ACCEPTANCE_THRESHOLD)),
            _ACCEPTANCE_THRESHOLD,
        )

        if not assertions:
            self._log("[validator] no contract found -- generating one first")
            mo = MissionOrchestrator()
            mo._execute(context)
            contract = context.metadata.get("validation_contract", {})
            assertions = contract.get("assertions", [])

        heal_count = 0
        result_list: list[dict[str, Any]] = []
        acceptance = 0.0

        while heal_count <= _MAX_SELF_HEALS:
            result_list = self._validate(context, assertions)
            verified = sum(1 for r in result_list if r.get("status") == "VERIFIED")
            total = len(result_list) or len(assertions)
            acceptance = verified / total if total > 0 else 0.0
            passed = acceptance >= threshold

            self._log(
                f"[validator] attempt {heal_count + 1}: "
                f"{verified}/{total} verified ({acceptance:.0%}) "
                f"threshold={threshold:.0%} -> {'PASS' if passed else 'FAIL'}"
            )

            if passed:
                break

            if heal_count < _MAX_SELF_HEALS:
                self._self_heal(context, result_list)
                heal_count += 1
            else:
                break

        verified_final = sum(1 for r in result_list if r.get("status") == "VERIFIED")
        total_final = len(result_list) or len(assertions)
        acceptance_final = verified_final / total_final if total_final > 0 else 0.0
        passed_final = acceptance_final >= threshold

        context.metadata["validator_result"] = {
            "passed": passed_final,
            "acceptance_rate": round(acceptance_final, 4),
            "assertions_total": total_final,
            "assertions_verified": verified_final,
            "self_heals_used": heal_count,
        }

        if not passed_final:
            raise PipelineBlockedError(
                f"MissionValidator failed after {heal_count} self-heal(s): "
                f"{verified_final}/{total_final} assertions verified "
                f"({acceptance_final:.0%} < {threshold:.0%} required)"
            )

        return {
            "assertions_total": total_final,
            "assertions_verified": verified_final,
            "acceptance_rate": round(acceptance_final, 4),
            "threshold": threshold,
            "passed": True,
            "self_heals": heal_count,
            "results": result_list,
        }

    def _validate(
        self, context: ProjectContext, assertions: list[Any]
    ) -> list[dict[str, Any]]:
        inventory = _inventory(Path(context.workdir) / "project")
        assertions_text = "\n".join(
            f"  [{i + 1}] [{a.get('category', '?')}] {a.get('description', a)}"
            if isinstance(a, dict)
            else f"  [{i + 1}] {a}"
            for i, a in enumerate(assertions)
        )
        try:
            resp = self._llm(
                context,
                user_prompt=(
                    f"Adversarially validate this codebase against the ValidationContract.\n\n"
                    f"IDEA: {context.idea}\n\n"
                    f"ASSERTIONS:\n{assertions_text}\n\n"
                    f"GENERATED FILES:\n{inventory}\n\n"
                    "For each assertion output: [N] VERIFIED | UNVERIFIED | PARTIAL -- reason\n\n"
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
                max_tokens=4000,
                temperature=0.1,
            )
            data = self._extract_json_block(resp.text)
            if isinstance(data, dict) and "results" in data:
                return data["results"]
        except Exception as e:
            self._log(f"[validator] LLM failed: {e}")
        return []

    def _self_heal(
        self, context: ProjectContext, results: list[dict[str, Any]]
    ) -> None:
        unverified = [r for r in results if r.get("status") != "VERIFIED"]
        if not unverified:
            return

        unverified_text = "\n".join(
            f"- {r.get('assertion', '')}: {r.get('reason', '')}"
            for r in unverified
        )
        project_dir = Path(context.workdir) / "project"

        try:
            from llm.router import complete as llm_complete

            resp = llm_complete(
                context=context,
                user=(
                    f"Fix these failing assertions in the project at {project_dir}:\n\n"
                    f"{unverified_text}\n\n"
                    "For each issue: output the corrected file as a fenced block tagged with its path."
                ),
                system_extra=(
                    "You are fixing specific failing assertions. "
                    "Write complete corrected files. No placeholders."
                ),
                task_complexity="medium",
                task_type="code",
                purpose="validator.self_heal",
                max_tokens=6000,
            )
            from agents.mission.worker import _split_files
            files = _split_files(resp.text)
            for relpath, file_content in files.items():
                rel = relpath.strip().lstrip("/")
                if not rel:
                    continue
                target = (project_dir / rel).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(file_content, encoding="utf-8")
            self._log(f"[validator] self-heal wrote {len(files)} files")
        except Exception as e:
            self._log(f"[validator] self-heal failed: {e}")


__all__ = ["MissionValidator"]
