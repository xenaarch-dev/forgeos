"""
Mesh data contracts — the closed Capability enum and RouteDecision.

SPEC_AgentMesh.md §3a. The enum is deliberately *closed*: an unconstrained
classifier will confidently route to MeetingForge, a capability that does not
exist as a single line of code, and that is precisely the failure mode the mesh
exists to correct. Anything outside this enum is UNSUPPORTED, by construction.

The confidence policy of §3c is expressed here as derived properties rather than
extra model fields, so the tool schema handed to Claude stays exactly the five
fields the spec defines.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Capability(str, Enum):
    """Every legal routing outcome. There are no others."""

    CONTRACT = "contract"        # LegalAgent
    OUTREACH = "outreach"        # OutreachForgeAgent
    SPEC = "spec"                # ArchitectAgent, spec-only mode
    BUILD = "build"              # POST /builds — full pipeline
    CLARIFY = "clarify"          # ambiguous — ask one question back
    UNSUPPORTED = "unsupported"  # real intent, no implementation yet


#: Capabilities that can be dispatched to an adapter, in the order §2 lists them.
#: CLARIFY and UNSUPPORTED are terminal outcomes — they never reach the registry.
DISPATCHABLE: tuple[Capability, ...] = (
    Capability.CONTRACT,
    Capability.OUTREACH,
    Capability.SPEC,
    Capability.BUILD,
)

#: Transcript-facing names (§3d, §5a: "Routing to ContractForge — ...").
DISPLAY_NAMES: dict[Capability, str] = {
    Capability.CONTRACT: "ContractForge",
    Capability.OUTREACH: "OutreachForge",
    Capability.SPEC: "SpecForge",
    Capability.BUILD: "the build pipeline",
}

# Confidence bands — §3c. Never dispatch below CLARIFY_THRESHOLD: a wrong
# contract draft costs more than one extra question.
DISPATCH_THRESHOLD: float = 0.75
CLARIFY_THRESHOLD: float = 0.45


class RouteDecision(BaseModel):
    """One routing verdict. Also the tool schema Claude fills in during classify."""

    model_config = ConfigDict(extra="ignore")

    capability: Capability = Field(
        ...,
        description="The single capability this command routes to.",
    )
    args: dict[str, str] = Field(
        default_factory=dict,
        description='Payload for the capability, normally {"idea": "<the request>"}.',
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calibrated probability that the chosen capability is correct.",
    )
    rationale: str = Field(
        default="",
        description="One sentence, shown verbatim in the founder's transcript.",
    )
    unsupported_reason: str | None = Field(
        default=None,
        description="Required when capability is 'unsupported': why nothing ran.",
    )

    @model_validator(mode="after")
    def _never_go_quiet(self) -> "RouteDecision":
        """A decision always says something. Silence is the bug being fixed."""
        if not self.rationale.strip():
            self.rationale = f"Routed to {self.display_name}."
        if self.capability is Capability.UNSUPPORTED and not (
            self.unsupported_reason or ""
        ).strip():
            self.unsupported_reason = (
                "That isn't built yet — no implementation is wired for it. Nothing ran."
            )
        return self

    # ------------------------------------------------------------------
    # Derived confidence policy (§3c) — not part of the LLM tool schema
    # ------------------------------------------------------------------

    @property
    def display_name(self) -> str:
        return DISPLAY_NAMES.get(self.capability, self.capability.value)

    @property
    def should_dispatch(self) -> bool:
        """CLARIFY and UNSUPPORTED never dispatch; nor does anything under 0.45."""
        return (
            self.capability in DISPATCHABLE and self.confidence >= CLARIFY_THRESHOLD
        )

    @property
    def is_hedged(self) -> bool:
        """True in the 0.45–0.75 band: dispatch, but tell the founder it's a guess."""
        return self.should_dispatch and self.confidence < DISPATCH_THRESHOLD

    @property
    def transcript_prefix(self) -> str:
        if not self.is_hedged:
            return ""
        return f'Routing to {self.display_name} — say "no, I meant …" to redirect.'


__all__ = [
    "CLARIFY_THRESHOLD",
    "DISPATCHABLE",
    "DISPATCH_THRESHOLD",
    "DISPLAY_NAMES",
    "Capability",
    "RouteDecision",
]
