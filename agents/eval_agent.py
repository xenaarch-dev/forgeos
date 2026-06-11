"""EvalAgent — automated quality gate (Stage 13).

Evaluates code quality, security, test coverage, and completeness after
SecurityAgent completes. If ship_ready == False, blocks the pipeline and
surfaces the score breakdown to the human.
"""

from __future__ import annotations

from typing import Any

from forge_sdk.agent import ForgeAgent
from models import LLMError, ProjectContext
from models.outputs.eval_output import EvalOutput


_SYSTEM_PROMPT = """\
You are the quality gate evaluator for ForgeOS.
Inspect the generated codebase, security audit, and test results honestly.
Score objectively — a passing score (≥80) means this code is ready for
real users. Flag security vulnerabilities, missing tests, or unimplemented
spec features as blocking issues (these prevent shipping regardless of score).
"""

_PROMPT = """\
Evaluate this ForgeOS build:

IDEA: {idea}

SPEC (excerpt):
{spec}

ARCHITECTURE (excerpt):
{arch}

TASKS: {tasks_summary}

SECURITY REPORT: {security_report}

Score each dimension 0-100:
- code_quality_score  (weight 30%): correctness, maintainability, no TODOs/stubs
- security_score      (weight 35%): no hardcoded secrets, RLS in place, auth correct
- test_coverage_score (weight 20%): meaningful tests cover core paths
- completeness_score  (weight 15%): all spec features implemented

List blocking_issues (empty list if none) — these stop the deploy regardless of score.
List recommendations for the next build cycle.
"""


class EvalAgent(ForgeAgent):
    """Automated quality gate — blocks deploy if score < 80 or blocking issues exist."""

    name         = "eval_agent"
    phase        = "eval"
    capabilities = ["eval_output"]
    requires     = ["idea", "spec", "architecture", "security_output"]
    budget_usd   = 0.0

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        import os
        from llm.claude import ClaudeClient
        from llm.router import _build_system_prompt

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY not set — EvalAgent requires Claude structured output")

        security = context.metadata.get("security_output", {})
        tasks_done = sum(1 for t in context.tasks if getattr(t, "status", None) == "done")
        tasks_summary = f"{len(context.tasks)} tasks, {tasks_done} completed"

        client = ClaudeClient()
        system = _build_system_prompt(None, _SYSTEM_PROMPT)
        prompt = _PROMPT.format(
            idea=context.idea,
            spec=(context.spec or "")[:1000],
            arch=(context.architecture or "")[:500],
            tasks_summary=tasks_summary,
            security_report=security,
        )

        result: EvalOutput = client.complete_structured(
            messages=[{"role": "user", "content": prompt}],
            output_model=EvalOutput,
            system=system,
            max_tokens=4096,
            stage="eval_agent",
        )

        context.metadata["eval_output"] = result.model_dump()
        self._log(
            f"[eval_agent] score={result.overall_score} grade={result.grade} "
            f"ship_ready={result.ship_ready}"
        )

        if not result.ship_ready:
            issues = "; ".join(result.blocking_issues) if result.blocking_issues else "score below 80"
            raise RuntimeError(
                f"Quality gate FAILED — score={result.overall_score}/100 "
                f"grade={result.grade} | {issues}"
            )

        return result.model_dump()


__all__ = ["EvalAgent"]
