"""
MeshRouter — free text in, RouteDecision out.

Two stages, per SPEC_AgentMesh.md §3a:

  1. Deterministic prefilter. Quick-action button payloads, slash commands and
     empty input are known strings; they must never cost an LLM call.
  2. Constrained LLM classify. claude-sonnet-4-6 via _structured_llm() with
     RouteDecision as the tool schema, so the answer is drawn from the closed
     Capability enum by construction.

Then the §3c confidence policy is applied: dispatch above 0.75, dispatch with a
hedge between 0.45 and 0.75, and never dispatch below 0.45 — ask one question
instead.

Phase 1 scope: the router returns a RouteDecision and stops. No capability
execution, no HTTP, no UI.
"""

from __future__ import annotations

from typing import Any

from forge_sdk.agent import ForgeAgent
from mesh.models import (
    CLARIFY_THRESHOLD,
    DISPATCHABLE,
    DISPLAY_NAMES,
    Capability,
    RouteDecision,
)
from models import ProjectContext


#: models.yaml stages key (§3e) — visible and overridable.
ROUTER_STAGE = "router"

#: Button payloads generated from a frontend constant, not natural language.
#: web/app/app/command/page.tsx:20. Matched before any network call.
_QUICK_ACTIONS: dict[str, dict[str, Any]] = {
    "GENERATE NDA": {
        "capability": Capability.CONTRACT,
        "rationale": "Quick action: NDA generation is a ContractForge job.",
    },
    "DRAFT OUTREACH FOR CA FIRMS": {
        "capability": Capability.OUTREACH,
        "rationale": "Quick action: CA-firm outreach drafting is an OutreachForge job.",
    },
    # No mesh capability produces metrics. Saying so is the honest outcome —
    # the alternative is the silence this whole spec exists to remove.
    "RUN MORNING METRICS": {
        "capability": Capability.UNSUPPORTED,
        "rationale": "Quick action: metrics reporting is not a mesh capability.",
        "unsupported_reason": (
            "Morning metrics isn't wired into the mesh — the dashboard reads "
            "Supabase directly. Nothing ran."
        ),
    },
}

_SLASH_COMMANDS: dict[str, Capability] = {
    "/contract": Capability.CONTRACT,
    "/outreach": Capability.OUTREACH,
    "/spec": Capability.SPEC,
    "/build": Capability.BUILD,
}

_CLASSIFY_SYSTEM = """You are the ForgeOS mesh router. You classify exactly one \
founder command into exactly one capability and return it with the \
structured_output tool. You never answer the command yourself.

CAPABILITIES THAT EXIST TODAY:
  contract  - ContractForge (LegalAgent). Indian-law documents: NDA, service
              agreement, terms and conditions, privacy policy, refund policy.
  outreach  - OutreachForge. Drafts lead and prospect messages. Drafts only;
              nothing is ever sent without a human approving it.
  spec      - SpecForge (ArchitectAgent, spec-only mode). A written spec or
              architecture for a product, with no code produced.
  build     - The full product pipeline. Use this whenever the founder wants
              software BUILT, scaffolded, shipped or deployed: an app, a site,
              a landing page, a game, a SaaS, an internal tool.

TWO NON-CAPABILITIES, both first-class answers:
  clarify     - genuinely ambiguous between capabilities, or too short to act
                on. Put exactly one question in `rationale`.
  unsupported - you understand the intent but ForgeOS has no implementation.
                Anything about meetings or calendars (MeetingForge), reviews or
                reputation (ReputationForge), CRM and client management
                (ClientForge), or querying what GBrain has learned, is
                unsupported. So is any general-knowledge question: this router
                is not a chatbot. Explain why in `unsupported_reason`.

RULES:
  - Never invent a capability. The six values above are the only legal answers.
  - `confidence` is your genuine calibrated probability that the capability is
    correct. Use the full range. Below 0.45 the system refuses to dispatch and
    asks the founder instead, which is the right outcome when you are guessing.
  - `rationale` is ONE sentence, shown verbatim in the founder's transcript.
  - `args` carries the payload for the capability, normally
    {"idea": "<the founder's request>"}.
"""


class MeshRouter(ForgeAgent):
    """Capability router. Stage 1 rules, stage 2 constrained classify, §3c policy."""

    name = "mesh_router"
    phase = "mesh"
    capabilities: list[str] = []  # the router writes no artifacts
    requires: list[str] = ["idea"]
    budget_usd = 0.02  # §3e — a ~300-token call; anything more is a bug

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, context: ProjectContext, text: str) -> RouteDecision:
        """Classify one command. Always returns a decision — never None."""
        decision = self._prefilter(text)
        if decision is None:
            decision = self._apply_confidence_policy(self._classify(context, text))

        self._emit(
            "route",
            {
                "agent": self.name,
                "capability": decision.capability.value,
                "confidence": decision.confidence,
                "rationale": decision.rationale,
                "dispatch": decision.should_dispatch,
            },
        )
        return decision

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        """ForgeAgent entry point — routes context.idea as the command text."""
        decision = self.route(context, context.idea)
        return {"route": decision.model_dump(mode="json")}

    # ------------------------------------------------------------------
    # Stage 1 — deterministic prefilter (§3a)
    # ------------------------------------------------------------------

    def _prefilter(self, text: str) -> RouteDecision | None:
        """Return a decision for known strings, or None to fall through to the LLM."""
        stripped = text.strip()

        if not stripped:
            return RouteDecision(
                capability=Capability.CLARIFY,
                confidence=0.0,
                rationale="What would you like the mesh to do?",
            )

        quick = _QUICK_ACTIONS.get(stripped.upper())
        if quick is not None:
            return RouteDecision(confidence=1.0, args={"idea": stripped}, **quick)

        if stripped.startswith("/"):
            return self._route_slash(stripped)

        return None

    def _route_slash(self, text: str) -> RouteDecision:
        head, _, rest = text.partition(" ")
        command = head.lower()
        capability = _SLASH_COMMANDS.get(command)

        if capability is None:
            known = ", ".join(sorted(_SLASH_COMMANDS))
            return RouteDecision(
                capability=Capability.UNSUPPORTED,
                confidence=1.0,
                rationale=f"Unknown slash command {command}.",
                unsupported_reason=(
                    f"{command} isn't a mesh command. Known commands: {known}. "
                    "Nothing ran."
                ),
            )

        payload = rest.strip()
        return RouteDecision(
            capability=capability,
            args={"idea": payload} if payload else {},
            confidence=1.0,
            rationale=(
                f"Slash command {command} routes directly to "
                f"{DISPLAY_NAMES[capability]}."
            ),
        )

    # ------------------------------------------------------------------
    # Stage 2 — constrained LLM classify (§3a, §3e)
    # ------------------------------------------------------------------

    def _classify(self, context: ProjectContext, text: str) -> RouteDecision:
        self._check_budget(context)
        prompt = (
            f"FOUNDER COMMAND:\n{text.strip()}\n\n"
            "Classify this command using the structured_output tool."
        )
        return self._structured_llm(
            context,
            user_prompt=prompt,
            output_model=RouteDecision,
            system_extra=_CLASSIFY_SYSTEM,
            max_tokens=1024,
            stage=ROUTER_STAGE,
        )

    # ------------------------------------------------------------------
    # Confidence policy (§3c)
    # ------------------------------------------------------------------

    def _apply_confidence_policy(self, decision: RouteDecision) -> RouteDecision:
        """Below 0.45, refuse to dispatch and ask exactly one question instead."""
        if decision.capability is Capability.CLARIFY:
            return decision
        if decision.confidence >= CLARIFY_THRESHOLD:
            return decision
        return RouteDecision(
            capability=Capability.CLARIFY,
            args=dict(decision.args),
            confidence=decision.confidence,
            rationale=self._clarify_question(decision),
        )

    @staticmethod
    def _clarify_question(decision: RouteDecision) -> str:
        """Exactly one question — §3c."""
        if decision.capability in DISPATCHABLE:
            return (
                f"I'm not confident enough to route that — did you mean "
                f"{decision.display_name}?"
            )
        options = ", ".join(c.value for c in DISPATCHABLE)
        return f"I'm not sure what to route that to — is it one of {options}?"


__all__ = ["ROUTER_STAGE", "MeshRouter"]
