"""
GStack quality gates for ForgeOS.

Each gate is a BaseAgent subclass that performs an LLM-powered quality
check at a specific pipeline stage. Gates with blocking=True halt the
pipeline when they fail.

Gate ladder (pipeline order):
  planning:  OfficeHoursGate -> CEOReviewGate
  design:    EngReviewGate -> DesignShotgunGate
  review:    ReviewGate -> AdversarialGate -> ScoreGate
  security:  CSOGate
  qa:        QAGate
  ship:      ShipGate
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from llm.router import complete as llm_complete
from models import GateResult, ProjectContext
from forge_sdk.agent import ForgeAgent


_GATE_SYSTEM = (
    "You are a rigorous quality gate in ForgeOS, an autonomous AI product factory. "
    "Evaluate what is given and return a clear verdict. "
    "Always end with exactly one of: PASS or FAIL. "
    "Always include SCORE: N/10 where N is your 1-10 rating. "
    "Be specific about what is wrong when you FAIL something."
)


class GStackGate(ForgeAgent):
    """Abstract base for all GStack quality gates."""

    gate_name: str = "gate"
    phase: str = "gate"
    min_score: float = 6.0
    blocking: bool = True
    capabilities: list[str] = []
    requires: list[str] = ["idea"]
    budget_usd: float = 0.0

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        result = self._evaluate(context)
        gates = context.metadata.setdefault("gates", [])
        gates.append(asdict(result))

        self._log(
            f"[{self.gate_name}] {'PASS' if result.passed else 'FAIL'} "
            f"score={result.score:.1f} — {result.feedback[:120]}"
        )

        if not result.passed and self.blocking:
            raise RuntimeError(
                f"Gate '{self.gate_name}' blocked pipeline "
                f"(score={result.score:.1f} < {self.min_score:.1f}): "
                f"{result.feedback[:300]}"
            )

        return {
            "gate": self.gate_name,
            "passed": result.passed,
            "score": result.score,
            "feedback": result.feedback,
        }

    def _evaluate(self, context: ProjectContext) -> GateResult:
        raise NotImplementedError

    def _gate_call(
        self,
        context: ProjectContext,
        prompt: str,
        max_tokens: int = 1200,
        task_type: str = "review",
    ) -> GateResult:
        resp = llm_complete(
            context=context,
            user=prompt,
            system_extra=_GATE_SYSTEM,
            task_complexity="hard",
            task_type=task_type,
            purpose=f"gate.{self.gate_name}",
            max_tokens=max_tokens,
            temperature=0.1,
            stream=True,
        )
        passed, score, feedback = _parse_verdict(resp.text, self.min_score)
        return GateResult(
            gate=self.gate_name,
            passed=passed,
            score=score,
            feedback=feedback,
        )


# ---------------------------------------------------------------------------
# Planning tier
# ---------------------------------------------------------------------------


class OfficeHoursGate(GStackGate):
    """Is this idea worth building at all?"""

    name = "office_hours_gate"
    gate_name = "office_hours"
    phase = "planning"
    min_score = 6.0
    requires = ["idea"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        return self._gate_call(
            context,
            f"""Evaluate this product idea for viability.

IDEA: {context.idea}

Assess:
1. Market demand — is there a real problem being solved?
2. Monetization — can this charge money and to whom?
3. Complexity — is this buildable by a 6-agent AI system in one session?
4. Risk — what is the biggest reason this fails?
5. Moat — why would someone pay vs use a free alternative?

Score the idea 1-10. Score >= 7 = PASS. Score < 7 = FAIL.
End with SCORE: N/10 and PASS or FAIL.""",
        )


class CEOReviewGate(GStackGate):
    """Business plan review — is the SPEC commercially sound?"""

    name = "ceo_review_gate"
    gate_name = "ceo_review"
    phase = "planning"
    min_score = 6.0
    requires = ["idea", "spec"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        spec = context.spec or "(no spec yet — evaluating idea only)"
        return self._gate_call(
            context,
            f"""Review this product from a CEO/investor perspective.

IDEA: {context.idea}

SPEC:
{spec[:3000]}

Assess:
1. Revenue model — is there a clear path to $1k MRR?
2. Target user — is the ICP specific enough to market to?
3. Core features — do they match the revenue goal?
4. Scope — is it too big to ship in one sprint?
5. Missing — what critical feature is absent?

Score 1-10. Score >= 6 = PASS. Score < 6 = FAIL.
End with SCORE: N/10 and PASS or FAIL.""",
        )


# ---------------------------------------------------------------------------
# Design tier
# ---------------------------------------------------------------------------


class EngReviewGate(GStackGate):
    """Engineering plan review — is the ARCH technically sound?"""

    name = "eng_review_gate"
    gate_name = "eng_review"
    phase = "design"
    min_score = 6.0
    requires = ["idea", "architecture"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        arch = context.architecture or "(no architecture yet)"
        return self._gate_call(
            context,
            f"""Review this architecture from a senior engineer perspective.

IDEA: {context.idea}

ARCHITECTURE:
{arch[:3000]}

Assess:
1. Stack — appropriate and not over-engineered?
2. Data model — does the ERD support all core features?
3. API design — endpoints complete and RESTful?
4. Gaps — what critical system component is missing?
5. Risk — highest technical risk?

Score 1-10. Score >= 6 = PASS. Score < 6 = FAIL.
End with SCORE: N/10 and PASS or FAIL.""",
        )


class DesignShotgunGate(GStackGate):
    """Rapid-fire design review — quick calls on each design decision."""

    name = "design_shotgun_gate"
    gate_name = "design_shotgun"
    phase = "design"
    min_score = 5.0
    blocking = False  # Advisory only
    requires = ["idea", "stack"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        stack_json = (
            json.dumps(asdict(context.stack), indent=2)
            if context.stack
            else "{}"
        )
        return self._gate_call(
            context,
            f"""Rapid shotgun design review (fast, direct, no softening).

IDEA: {context.idea}

STACK:
{stack_json}

Fire one-line verdicts:
- Auth strategy: correct choice?
- Database: over/under engineered?
- Frontend: right framework?
- Payments: works in target market?
- Deploy: right infra for this scale?
- Biggest design mistake (one sentence):
- What to cut from scope (one sentence):

Score 1-10. Score >= 5 = PASS. Score < 5 = FAIL.
End with SCORE: N/10 and PASS or FAIL.""",
        )


# ---------------------------------------------------------------------------
# Review tier
# ---------------------------------------------------------------------------


class ReviewGate(GStackGate):
    """Staff-level code review."""

    name = "review_gate"
    gate_name = "review"
    phase = "review"
    min_score = 6.0
    requires = ["idea", "workdir"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        inventory = _get_code_inventory(context)
        return self._gate_call(
            context,
            f"""Staff-level code review for this generated project.

IDEA: {context.idea}

GENERATED FILES:
{inventory}

Review for:
1. Completeness — all core features implemented?
2. Quality — any TODO/FIXME/placeholder remaining?
3. Tests — meaningful test coverage present?
4. Security — obvious vulnerabilities?
5. Production readiness — will this actually run without modification?

Score 1-10. Score >= 6 = PASS. Score < 6 = FAIL.
End with SCORE: N/10 and PASS or FAIL.""",
            max_tokens=1500,
        )


class AdversarialGate(GStackGate):
    """Adversarial review — try to break the code."""

    name = "adversarial_gate"
    gate_name = "adversarial"
    phase = "review"
    min_score = 5.0
    requires = ["idea", "workdir"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        inventory = _get_code_inventory(context)
        return self._gate_call(
            context,
            f"""Adversarial review — pretend you are a malicious user.

IDEA: {context.idea}

GENERATED FILES:
{inventory}

Attack vectors to evaluate (rate each: BLOCKED / VULNERABLE):
1. SQL injection via user input fields
2. Auth bypass — unauthenticated access to protected routes?
3. IDOR — access another user's data by ID manipulation?
4. Missing rate limiting on expensive endpoints?
5. Secrets hardcoded in source?
6. Logic errors in payment/billing flow?

Any VULNERABLE = FAIL. All BLOCKED = PASS.
Score 1-10 where 10 = completely secure.
End with SCORE: N/10 and PASS or FAIL.""",
            max_tokens=1500,
        )


class ScoreGate(GStackGate):
    """Score the code 1-10. Block if below min_score."""

    name = "score_gate"
    gate_name = "score"
    phase = "review"
    min_score = 7.0
    requires = ["idea", "workdir"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        inventory = _get_code_inventory(context)
        return self._gate_call(
            context,
            f"""Produce a final quality score for this generated codebase.

IDEA: {context.idea}

GENERATED FILES:
{inventory}

Scoring rubric:
- 10: Production-ready. Ships today. No changes needed.
- 8-9: Near production. Minor polish required.
- 7: Acceptable. Missing a few things but core works.
- 5-6: Incomplete. Key features broken or missing.
- 1-4: Fundamentally broken. Major rework needed.

Be strict. Most AI-generated code scores 5-7.
Score >= 7 = PASS. Score < 7 = FAIL.
End with SCORE: N/10 and PASS or FAIL.""",
            max_tokens=1000,
        )


# ---------------------------------------------------------------------------
# Security tier
# ---------------------------------------------------------------------------


class CSOGate(GStackGate):
    """Chief Security Officer review."""

    name = "cso_gate"
    gate_name = "cso"
    phase = "security"
    min_score = 6.0
    requires = ["idea", "workdir"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        # Semgrep hard-block: any ERROR-severity finding fails immediately,
        # independent of LLM judgment. This gate is blocking (gate=True).
        semgrep = context.metadata.get("security", {}).get("semgrep", {})
        if semgrep.get("blocking"):
            count = semgrep.get("critical_count", 0)
            details = "; ".join(
                f.get("check_id", "") for f in semgrep.get("critical_findings", [])[:3]
            )
            summary = (
                f"Semgrep static analysis found {count} ERROR-severity finding(s): "
                f"{details}. "
                "Gate blocked by execution-verified static analysis — fix findings "
                "before re-running. See SECURITY.md for the full report."
            )
            self._log(f"[cso_gate] BLOCKED by semgrep: {count} ERROR finding(s)")
            return GateResult(gate=self.gate_name, passed=False, score=0.0, feedback=summary)

        security_md = _read_artifact(context, "SECURITY.md")
        inventory = _get_code_inventory(context)
        return self._gate_call(
            context,
            f"""Security review from a Chief Security Officer perspective.

IDEA: {context.idea}

SECURITY.md:
{security_md[:2000] if security_md else "(not found)"}

FILES:
{inventory}

Evaluate:
1. Authentication — JWT properly validated? Session management secure?
2. Authorization — RLS policies correct? No privilege escalation paths?
3. Input validation — all user inputs sanitized?
4. Secrets management — no secrets in source?
5. Dependencies — any known vulnerable packages?
6. Data compliance — GDPR/data handling concerns?

Score >= 6 = PASS (ship with risks documented).
Score < 6 = FAIL (must not ship).
End with SCORE: N/10 and PASS or FAIL.""",
            max_tokens=1500,
            task_type="security",  # routes to Fable-5 when FORGEOS_FRONTIER_TIER=true
        )


# ---------------------------------------------------------------------------
# QA tier
# ---------------------------------------------------------------------------


class QAGate(GStackGate):
    """QA validation against the ValidationContract."""

    name = "qa_gate"
    gate_name = "qa"
    phase = "qa"
    min_score = 7.0
    requires = ["idea", "workdir"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        contract = context.metadata.get("validation_contract", {})
        assertions = contract.get("assertions", [])
        if not assertions:
            return GateResult(
                gate=self.gate_name,
                passed=True,
                score=7.0,
                feedback="No ValidationContract found — QA gate skipped.",
            )

        inventory = _get_code_inventory(context)
        assertions_text = "\n".join(
            f"- [{a.get('category', 'functional')}] {a.get('description', a)}"
            if isinstance(a, dict)
            else f"- {a}"
            for a in assertions
        )
        threshold = float(contract.get("acceptance_threshold", 0.90))

        return self._gate_call(
            context,
            f"""QA validation against the project's ValidationContract.

IDEA: {context.idea}

ASSERTIONS TO VERIFY:
{assertions_text}

FILES:
{inventory}

For each assertion, check if the generated code supports it (YES/NO/PARTIAL).
Acceptance threshold: {threshold:.0%} must pass.
If threshold met: PASS. Otherwise: FAIL.

Score = (passing_assertions / total_assertions) * 10.
End with SCORE: N/10 and PASS or FAIL.""",
            max_tokens=2000,
        )


# ---------------------------------------------------------------------------
# Ship tier
# ---------------------------------------------------------------------------


class ShipGate(GStackGate):
    """Final gate before deployment. Aggregates all prior gate results."""

    name = "ship_gate"
    gate_name = "ship"
    phase = "ship"
    min_score = 7.0
    requires = ["metadata.gates"]

    def _evaluate(self, context: ProjectContext) -> GateResult:
        gates = context.metadata.get("gates", [])
        failed = [g for g in gates if not g.get("passed", True)]
        passing_scores = [g.get("score", 0.0) for g in gates if g.get("passed", True)]
        avg = sum(passing_scores) / len(passing_scores) if passing_scores else 0.0

        if failed:
            names = ", ".join(g["gate"] for g in failed)
            return GateResult(
                gate=self.gate_name,
                passed=False,
                score=max(0.0, avg - 2.0),
                feedback=f"Cannot ship: these gates failed = [{names}].",
            )

        return GateResult(
            gate=self.gate_name,
            passed=avg >= self.min_score,
            score=avg,
            feedback=(
                f"All {len(gates)} gates passed. Average score: {avg:.1f}/10. "
                "Ready to deploy."
            ),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_verdict(text: str, min_score: float) -> tuple[bool, float, str]:
    upper = text.upper()

    score = 0.0
    m = re.search(r"SCORE\s*[:\-]\s*(\d+(?:\.\d+)?)\s*/\s*10", upper)
    if m:
        score = float(m.group(1))

    tail = upper[-400:]
    if "PASS" in tail and "FAIL" not in tail[tail.rfind("PASS"):]:
        passed = True
    elif "FAIL" in tail:
        passed = False
    else:
        passed = score >= min_score

    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    feedback_lines = [
        ln for ln in lines
        if not re.match(r"^(PASS|FAIL|SCORE)", ln.upper())
    ]
    feedback = " ".join(feedback_lines)[:500] or text[:300]

    return passed, score, feedback


def _get_code_inventory(context: ProjectContext, max_files: int = 60) -> str:
    project_root = Path(context.workdir) / "project"
    if not project_root.exists():
        return "(no code generated yet)"
    rows: list[str] = []
    for p in sorted(project_root.rglob("*")):
        if any(
            part in {".git", "node_modules", ".venv", "__pycache__", ".next"}
            for part in p.parts
        ):
            continue
        if p.is_file():
            try:
                rel = p.relative_to(project_root).as_posix()
                size = p.stat().st_size
                rows.append(f"{rel} ({size}B)")
                if len(rows) >= max_files:
                    rows.append("... (truncated)")
                    break
            except (ValueError, OSError):
                continue
    return "\n".join(rows) or "(empty project)"


def _read_artifact(context: ProjectContext, name: str) -> str:
    path = Path(context.workdir) / name
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


__all__ = [
    "AdversarialGate",
    "CEOReviewGate",
    "CSOGate",
    "DesignShotgunGate",
    "EngReviewGate",
    "GStackGate",
    "OfficeHoursGate",
    "QAGate",
    "ReviewGate",
    "ScoreGate",
    "ShipGate",
]
