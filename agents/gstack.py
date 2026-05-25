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
from .base import BaseAgent


_GATE_SYSTEM = (
    "You are a rigorous quality gate in ForgeOS, an autonomous AI product factory. "
    "Evaluate what is given and return a clear verdict. "
    "Always end with exactly one of: PASS or FAIL. "
    "Always include SCORE: N/10 where N is your 1-10 rating. "
    "Be specific about what is wrong when you FAIL something."
)


class GStackGate(BaseAgent):
    """Abstract base for all GStack quality gates."""

    gate_name: str = "gate"
    phase: str = "gate"
    min_score: float = 6.0
    blocking: bool = True

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
    ) -> GateResult:
        resp = llm_complete(
            context=context,
            user=prompt,
            system_extra=_GATE_SYSTEM,
            task_complexity="hard",
            task_type="review",
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

Score the idea 1-10. Score >= 6 = PASS. Score < 6 = FAIL.
End with SCORE: N/10 on its own line, then PASS or FAIL on its own line.""",
        )


class CEOReviewGate(GStackGate):
    """Business plan review — is the SPEC commercially sound?"""

    name = "ceo_review_gate"
    gate_name = "ceo_review"
    phase = "planning"
    min_score = 5.0

    def _evaluate(self, context: ProjectContext) -> GateResult:
        # Evaluate idea alone — spec may not exist yet at planning stage.
        spec_section = ""
        if context.spec:
            spec_section = f"\n\nSPEC (summary):\n{context.spec[:2000]}"
        return self._gate_call(
            context,
            f"""Review this product idea from a CEO/investor perspective.

IDEA: {context.idea}{spec_section}

Assess ONLY the idea as stated (spec may not exist yet):
1. Revenue model — is Rs2499/month or equivalent a realistic starting price?
2. Target user — is the ICP (Indian freelancers / B2B SaaS / etc.) specific?
3. Core features described — do they justify the price?
4. Scope — can a 5-agent AI system ship an MVP in one session?
5. Fatal flaw — is there one deal-breaker?

Score 1-10 based on the IDEA alone. Score >= 5 = PASS.
End with SCORE: N/10 on its own line, then PASS or FAIL on its own line.""",
        )


# ---------------------------------------------------------------------------
# Design tier
# ---------------------------------------------------------------------------


class EngReviewGate(GStackGate):
    """Engineering plan review — is the ARCH technically sound?"""

    name = "eng_review_gate"
    gate_name = "eng_review"
    phase = "design"
    min_score = 5.0  # matches gate prompt: "Score >= 5 = PASS"

    def _evaluate(self, context: ProjectContext) -> GateResult:
        # Read from disk first (more complete than context.architecture which may be truncated)
        arch = _read_artifact(context, "ARCH.md") or context.architecture or "(no architecture yet)"
        return self._gate_call(
            context,
            f"""Review this architecture from a senior engineer perspective.
This is an MVP plan — evaluate it as an MVP, not an enterprise system.

IDEA: {context.idea}

ARCHITECTURE:
{arch[:4000]}

Assess (grade leniently for MVP scope):
1. Stack — appropriate and not over-engineered for an MVP?
2. Data model — adequate for the core features described?
3. API design — are the key endpoints implied/described?
4. Security — any obvious missing concern (auth, RLS, secrets)?
5. Risk — highest technical risk for this specific idea?

NOTE: ERD diagrams and full endpoint lists may not be in this draft.
Grade the thinking and decisions, not the documentation completeness.
Score 1-10. Score >= 5 = PASS. Score < 5 = FAIL.
End with SCORE: N/10 on its own line, then PASS or FAIL on its own line.""",
        )


class DesignShotgunGate(GStackGate):
    """Rapid-fire design review — quick calls on each design decision."""

    name = "design_shotgun_gate"
    gate_name = "design_shotgun"
    phase = "design"
    min_score = 5.0
    blocking = False  # Advisory only

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
    min_score = 5.0

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

Score 1-10. Score >= 5 = PASS. Score < 5 = FAIL.
End with SCORE: N/10 and PASS or FAIL.""",
            max_tokens=1500,
        )


class AdversarialGate(GStackGate):
    """Adversarial review — try to break the code."""

    name = "adversarial_gate"
    gate_name = "adversarial"
    phase = "review"
    min_score = 4.0

    def _evaluate(self, context: ProjectContext) -> GateResult:
        inventory = _get_code_inventory(context)
        return self._gate_call(
            context,
            f"""Adversarial security review for an MVP codebase.

IDEA: {context.idea}

GENERATED FILES:
{inventory}

Rate the overall security posture 1-10:
- 10: Production-hardened, no obvious vulnerabilities
- 7-9: Minor issues, acceptable for launch
- 5-6: Some gaps, fixable in next sprint
- 4: Critical issues present but codebase is not completely broken
- 1-3: Fundamental security failures

Scoring rubric — evaluate but DO NOT hard-fail on individual vectors.
Note any concerns about: SQL injection, auth bypass, IDOR, missing rate limits,
hardcoded secrets, payment logic errors.

This is MVP code. Score >= 4 = PASS (security sprint follows).
End with SCORE: N/10 and PASS or FAIL.""",
            max_tokens=1500,
        )


class ScoreGate(GStackGate):
    """Score the code 1-10. Block if below min_score."""

    name = "score_gate"
    gate_name = "score"
    phase = "review"
    min_score = 3.0

    def _evaluate(self, context: ProjectContext) -> GateResult:
        inventory = _get_code_inventory(context)
        return self._gate_call(
            context,
            f"""Score this MVP codebase 1-10 on its own merits as an early-stage product.

IDEA: {context.idea}

GENERATED FILES:
{inventory}

MVP scoring rubric (this is NOT production code — it is a first-pass AI-generated MVP):
- 8-10: Exceptional MVP. Core features fully present, no obvious stubs.
- 6-7: Good MVP. Core features present, minor gaps.
- 4-5: Acceptable MVP. Main happy path works, some features incomplete.
- 3: Minimum viable. Scaffolding and structure correct; implementation has gaps.
- 1-2: Fundamentally broken. Missing core feature code entirely.

Do NOT penalise for: missing tests, no production hardening, missing CI/CD,
no performance tuning — those are Sprint 2+ concerns.
DO penalise for: missing files for advertised features, empty function bodies, no route handlers.

Score >= 3 = PASS (MVP threshold). End with SCORE: N/10 and PASS or FAIL.""",
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
    min_score = 5.0

    def _evaluate(self, context: ProjectContext) -> GateResult:
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

Score >= 5 = PASS (MVP with documented risks is acceptable).
Score < 5 = FAIL (critical unmitigated vulnerability).
End with SCORE: N/10 and PASS or FAIL.""",
            max_tokens=1500,
        )


# ---------------------------------------------------------------------------
# QA tier
# ---------------------------------------------------------------------------


class QAGate(GStackGate):
    """QA validation against the ValidationContract."""

    name = "qa_gate"
    gate_name = "qa"
    phase = "qa"
    min_score = 5.0

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
    min_score = 5.0

    def _evaluate(self, context: ProjectContext) -> GateResult:
        all_gates = context.metadata.get("gates", [])
        # Use only the LATEST result per gate name (gates may have been retried)
        latest: dict[str, dict] = {}
        for g in all_gates:
            name = g.get("gate", "")
            if name:
                latest[name] = g
        gates = list(latest.values())

        failed = [g for g in gates if not g.get("passed", True)]
        passing_scores = [g.get("score", 0.0) for g in gates if g.get("passed", True)]
        avg = sum(passing_scores) / len(passing_scores) if passing_scores else 0.0

        if failed:
            names = ", ".join(g["gate"] for g in failed)
            return GateResult(
                gate=self.gate_name,
                passed=False,
                score=max(0.0, avg - 2.0),
                feedback=f"Cannot ship: these gates still failing = [{names}].",
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
    m = re.search(r"SCORE[^0-9]*?(\d+(?:\.\d+)?)\s*/\s*10", upper)
    if m:
        score = float(m.group(1))

    if score > 0:
        # Numeric score is authoritative — text verdict is advisory only.
        passed = score >= min_score
    else:
        # No score found — fall back to text-based PASS/FAIL detection.
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
