"""OutreachForgeAgent — standalone outreach utility for ContractForge.

Drafts personalized first-touch messages for leads and writes them to the
Supabase outreach_leads table for human review.

HARD RULE: Nothing sends automatically. No message leaves this system until
a human calls mark_approved() and then manually triggers the send.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from forge_sdk.agent import ForgeAgent
from models import LLMError, ProjectContext


_SYSTEM_PROMPT = """\
You are the OutreachForge copywriter for ContractForge.

ContractForge: AI contract generator for Indian freelancers.
- ₹1,499 per contract or ₹2,499/month unlimited
- Instant generation, legally sound under Indian Contract Act 1872
- GST-compliant, DPDP Act 2023 compliant
- Mumbai jurisdiction by default

Voice: direct, peer-to-peer. No marketing language. No exclamation marks.
Write as one builder to another. Short. Specific to the person.
"""

_DRAFT_PROMPT = """\
Write a first-touch outreach message for this lead.

Name: {name}
Platform: {platform}
Handle: {handle}
Fit context: {fit_context}

Rules:
- Max 4 sentences
- Reference something specific from their fit context that makes ContractForge relevant
- No "Hi there", no "Hope this finds you well"
- No exclamation marks
- End with a question or soft CTA, not a hard sell
- Match the platform register: X = very short; email = slightly longer; linkedin = professional but brief
"""


class OutreachForgeAgent(ForgeAgent):
    """Draft and queue first-touch outreach for ContractForge leads.

    Not a HermesOrchestrator pipeline stage. Use the public methods directly:
    draft_message() → queue_for_approval() → mark_approved() → mark_sent()
    """

    name = "outreach_forge"
    phase = "outreach"
    capabilities = ["outreach_leads"]
    requires = []
    budget_usd = 0.05

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        raise NotImplementedError(
            "OutreachForgeAgent is a standalone utility. "
            "Use draft_message() / queue_for_approval() directly."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draft_message(self, lead: dict) -> str:
        """Draft a personalized first-touch message.

        Args:
            lead: dict with name, platform, fit_context (required); handle (optional).

        Returns:
            Draft message string. Not yet queued or sent.
        """
        required_keys = ("name", "platform", "fit_context")
        missing = [k for k in required_keys if not lead.get(k)]
        if missing:
            raise ValueError(f"Lead missing required fields: {missing}")

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY not set — OutreachForgeAgent requires Claude")

        from llm.claude import ClaudeClient
        from llm.router import _build_system_prompt

        client = ClaudeClient()
        system = _build_system_prompt(None, _SYSTEM_PROMPT)
        prompt = _DRAFT_PROMPT.format(
            name=lead["name"],
            platform=lead["platform"],
            handle=lead.get("handle", ""),
            fit_context=lead["fit_context"],
        )
        resp = client.complete(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            max_tokens=512,
            temperature=0.3,
        )
        return resp.text.strip()

    def queue_for_approval(self, lead: dict, draft: str) -> None:
        """Write lead + draft to outreach_leads with status='drafted'.

        NOTHING SENDS. No auto-send. Ever. Under any condition.
        """
        client = self._supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "name": lead["name"],
            "handle": lead.get("handle"),
            "platform": lead.get("platform"),
            "fit_context": lead.get("fit_context"),
            "draft_message": draft,
            "status": "drafted",
            "updated_at": now,
        }
        result = client.table("outreach_leads").insert(payload).execute()
        if getattr(result, "error", None):
            raise RuntimeError(f"Supabase insert failed: {result.error}")

    def get_pending_approvals(self) -> list:
        """Return all rows with status='drafted', ordered by created_at."""
        client = self._supabase_client()
        result = (
            client.table("outreach_leads")
            .select("*")
            .eq("status", "drafted")
            .order("created_at")
            .execute()
        )
        return result.data or []

    def mark_approved(self, lead_id: str) -> None:
        """Set status='approved' and record approved_at timestamp."""
        client = self._supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        result = (
            client.table("outreach_leads")
            .update({"status": "approved", "approved_at": now, "updated_at": now})
            .eq("id", lead_id)
            .execute()
        )
        if getattr(result, "error", None):
            raise RuntimeError(f"Supabase update failed: {result.error}")

    def mark_sent(self, lead_id: str) -> None:
        """Set status='sent' and record sent_at timestamp."""
        client = self._supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        result = (
            client.table("outreach_leads")
            .update({"status": "sent", "sent_at": now, "updated_at": now})
            .eq("id", lead_id)
            .execute()
        )
        if getattr(result, "error", None):
            raise RuntimeError(f"Supabase update failed: {result.error}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _supabase_client():
        """Return a supabase-py client using service role key."""
        try:
            from supabase import create_client
        except ImportError as e:
            raise RuntimeError("supabase-py not installed — run: pip install supabase") from e

        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        return create_client(url, key)


__all__ = ["OutreachForgeAgent"]
