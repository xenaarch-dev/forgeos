"""
OutreachCapability — the mesh adapter over OutreachForgeAgent.

SPEC_AgentMesh.md §4c. OutreachForgeAgent already *is* a ForgeAgent, so this
adapter is thin: it derives a lead from the command, calls draft_message(), and
normalises the result into a MeshArtifact.

HARD RULE, carried over verbatim from agents/outreach.py and not weakened here:
nothing sends automatically; no message leaves this system until a human calls
mark_approved() and then manually triggers the send.

This adapter therefore calls exactly two things on the wrapped agent —
draft_message() and queue_for_approval(), which writes status='drafted'. It
never calls mark_approved(). It never calls mark_sent(). The mesh must not
become the loophole that bypasses the gate (§7b).
"""

from __future__ import annotations

import os
import re
from typing import Any

from agents.outreach import OutreachForgeAgent
from forge_sdk.agent import ForgeAgent
from mesh.models import ArtifactType, MeshArtifact, mesh_args
from models import ProjectContext

#: Relpath of the reviewable artifact, relative to the command workdir.
ARTIFACT_RELPATH = "artifacts/outreach.md"

_DEFAULT_PLATFORM = "email"
_DEFAULT_NAME = "Prospect"

_FOR_PATTERN = re.compile(r"\bfor\s+(?:(?:a|an|the|my|our)\s+)?([^.,;\n]{2,60})", re.I)


class OutreachCapability(ForgeAgent):
    """OutreachForge, addressed as a mesh capability. Drafts only."""

    name = "outreach_capability"
    phase = "mesh"
    capabilities = [ARTIFACT_RELPATH, "outreach_leads"]
    requires = ["idea"]
    budget_usd = 0.05

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        args = mesh_args(context)
        lead = self._lead(context, args)

        agent = OutreachForgeAgent()
        draft = agent.draft_message(lead)
        queued, queue_error = self._queue(agent, lead, draft)

        body = self._compose(context, lead, draft, queued, queue_error)
        path = self._write(context, ARTIFACT_RELPATH, body)

        artifact = MeshArtifact(
            agent=self.name,
            artifact_type=ArtifactType.EMAIL,
            title=f"Outreach draft — {lead['name']}",
            body=body,
            slug="outreach",
            workdir_path=ARTIFACT_RELPATH,
        )
        self._emit(
            "artifact_ready",
            {
                "agent": self.name,
                "type": artifact.artifact_type.value,
                "title": artifact.title,
                "preview": artifact.preview(),
            },
        )

        return {
            "artifact": artifact.model_dump(mode="json"),
            "artifact_path": str(path),
            "draft": draft,
            "lead": lead,
            "queued_for_approval": queued,
            "queue_error": queue_error,
            # Stated in the output, not just the docstring, so any consumer of
            # this result can see the invariant rather than assume it.
            "sent": False,
            "approved": False,
        }

    # ------------------------------------------------------------------
    # Human-review queue — the only side effect, and it sends nothing
    # ------------------------------------------------------------------

    def _queue(
        self, agent: OutreachForgeAgent, lead: dict[str, str], draft: str
    ) -> tuple[bool, str | None]:
        """Queue the draft at status='drafted' for a human to review.

        Degrades rather than fails: a draft that exists but could not be queued
        is still worth keeping, and losing it because Supabase is unreachable
        would be the worse outcome. Either way nothing is sent.
        """
        if not (
            os.environ.get("SUPABASE_URL")
            and os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        ):
            reason = "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set"
            self._emit("queue_skipped", {"agent": self.name, "reason": reason})
            return False, reason

        try:
            agent.queue_for_approval(lead, draft)
            return True, None
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            self._emit("queue_skipped", {"agent": self.name, "reason": reason})
            return False, reason

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def _lead(self, context: ProjectContext, args: dict[str, str]) -> dict[str, str]:
        """Build the lead dict draft_message() expects.

        Structured values in args always win; Phase 3's HTTP surface is what
        will carry them. The fallback keeps the founder's own words as the fit
        context rather than inventing a plausible-sounding one.
        """
        return {
            "name": args.get("name") or self._derive_name(context.idea),
            "platform": args.get("platform") or _DEFAULT_PLATFORM,
            "handle": args.get("handle", ""),
            "fit_context": args.get("fit_context") or context.idea.strip(),
        }

    @staticmethod
    def _derive_name(idea: str) -> str:
        match = _FOR_PATTERN.search(idea or "")
        if not match:
            return _DEFAULT_NAME
        candidate = match.group(1).strip().strip("\"'")
        return candidate or _DEFAULT_NAME

    @staticmethod
    def _compose(
        context: ProjectContext,
        lead: dict[str, str],
        draft: str,
        queued: bool,
        queue_error: str | None,
    ) -> str:
        queue_line = (
            "> Queued in outreach_leads at status='drafted'."
            if queued
            else f"> Not queued: {queue_error}."
        )
        return (
            "\n".join(
                [
                    f"# Outreach draft — {lead['name']}",
                    "",
                    f"> Command: {context.idea.strip()}",
                    f"> Platform: {lead['platform']}",
                    f"> Fit context: {lead['fit_context']}",
                    queue_line,
                    ">",
                    "> NOT SENT. This is a draft. No message leaves ForgeOS until a"
                    " human approves it and triggers the send by hand.",
                    "",
                    "---",
                    "",
                    draft.strip(),
                ]
            )
            + "\n"
        )


__all__ = ["ARTIFACT_RELPATH", "OutreachCapability"]
