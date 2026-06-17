"""
LaunchAgent — stage 20, final stage.

Runs after DeployAgent. Produces LAUNCH.md with three human-review-gated
draft sections:
  - Product Hunt listing draft
  - Outreach seed list (5–10 ICP entries from SPEC.md + pm_output)
  - Launch announcement thread (Xena's voice, 3–5 tweets)

A "Campaign Videos" stub section references FalClient asset types
(build_a_brand, app_screens, product_sizzle) but does NOT call the
provider — generation is gated on FAL_API_KEY being set.

Gate: False — never blocks the pipeline. On failure, records
context.metadata["launch_skipped"] = True and logs the error.

Notification: fires a Telegram message via TelegramNotifier when LAUNCH.md
is ready (best-effort, never raises, degrades silently if not configured).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forge_sdk.agent import ForgeAgent
from models import ProjectContext


_LAUNCH_SYSTEM = """\
You are a go-to-market writer for Padmaja Kotoky (Xena), solo founder at Xenarch/ForgeOS.

Voice rules (mandatory — no exceptions):
- Direct and specific. Real product names, real tech, real numbers.
- No "excited to announce", "game-changer", "revolutionary", "disrupting".
- No launch emojis: 🚀 💡 ⚡️ 🔥 ✨ — use none.
- Lowercase is fine. Fragments are fine. Builder-to-builder tone.
- No filler. Every sentence earns its place.

Generate exactly these three H2 sections and no other content:

## Product Hunt Draft

Name: (product name, ≤ 60 chars)
Tagline: (one-liner, ≤ 60 chars, no emoji, no "revolutionary")
Description: (3–4 sentences, ≤ 260 chars total, what it does + who it's for + why now)

### Gallery captions
1. (screen 1)
2. (screen 2)
3. (screen 3)

### First comment
(founder note from Padmaja — personal, builder-to-builder, ≤ 300 chars)

## Outreach Seed

| Handle | Platform | Context |
|--------|----------|---------|
(5–10 rows. Handle = plausible X or LinkedIn handle pattern. Platform = x or linkedin. Context = one sentence why they'd care about this specific product.)

Run for each entry you want to queue:
    python3 agents/distribution/outreach_queue.py add --handle "<handle>" --platform "<platform>"

## Launch Thread

(3–5 tweets, Xena's voice)
[1/N] (what the product does, ≤ 280 chars)
[2/N] (what ForgeOS built — tech stack specifics)
[3/N] (live URL + CTA)
"""


class LaunchAgent(ForgeAgent):
    name         = "launch"
    phase        = "launch"
    capabilities = ["LAUNCH.md"]
    requires     = ["idea", "project_id", "spec", "frontend_url", "backend_url", "repo_url"]
    budget_usd   = 0.0
    tools        = []

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        spec = self._read(context, "SPEC.md") or context.spec or ""
        pm_output = context.metadata.get("pm_output", {})
        icp_note = pm_output.get("icp", "") if isinstance(pm_output, dict) else ""

        frontend_url = context.frontend_url or ""
        backend_url  = context.backend_url or ""
        repo_url     = context.repo_url or ""
        live_url     = frontend_url or backend_url or ""

        user_prompt = self._build_prompt(
            idea=context.idea,
            spec=spec,
            icp_note=icp_note,
            frontend_url=frontend_url,
            backend_url=backend_url,
            repo_url=repo_url,
        )

        resp = self._llm(
            context,
            user_prompt,
            system_extra=_LAUNCH_SYSTEM,
            task_complexity="medium",
            task_type="text",
            purpose="launch_draft",
            max_tokens=2048,
            temperature=0.4,
        )

        launch_md = _render_launch_md(
            sections=resp.text,
            project_id=context.project_id,
            live_url=live_url,
        )

        self._write(context, "LAUNCH.md", launch_md)

        project_dir = Path(context.workdir) / "project"
        if project_dir.exists():
            (project_dir / "LAUNCH.md").write_text(launch_md, encoding="utf-8")

        context.metadata["launch_draft_ready"] = True
        context.metadata["launch_needs_review"] = True

        _notify_launch_ready(context, self._log)

        return {
            "launch_md_written": True,
            "live_url": live_url,
        }

    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        idea: str,
        spec: str,
        icp_note: str,
        frontend_url: str,
        backend_url: str,
        repo_url: str,
    ) -> str:
        url_lines = "\n".join(
            f"- {label}: {url}"
            for label, url in [
                ("Frontend", frontend_url),
                ("Backend", backend_url),
                ("Repo", repo_url),
            ]
            if url
        )
        icp_section = f"\nICP note from PMAgent:\n{icp_note}\n" if icp_note else ""
        return (
            f"Product idea: {idea}\n\n"
            f"SPEC.md (truncated to 3000 chars):\n{spec[:3000]}\n"
            f"{icp_section}"
            f"\nLive URLs:\n{url_lines or '(none yet)'}\n"
        )


# ---------------------------------------------------------------------------
# Module-level helpers (pure functions — easier to test)
# ---------------------------------------------------------------------------

def _render_launch_md(sections: str, project_id: str, live_url: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    checklist_url = live_url or "(no URL yet)"
    return (
        "# LAUNCH.md\n\n"
        "> DRAFT — all content requires Padmaja's review before posting.\n"
        f"> Generated: {timestamp}\n"
        f"> ForgeOS build: `{project_id}`\n\n"
        "---\n\n"
        f"{sections.strip()}\n\n"
        "---\n\n"
        "## Campaign Videos\n\n"
        "> Status: pending — set FAL_API_KEY, then run:\n"
        "> `python3 tools/fal_client.py generate --type build_a_brand --prompt '...'`\n\n"
        "| Asset | Type | Duration |\n"
        "|-------|------|----------|\n"
        "| `build_a_brand` | brand overview | 15s |\n"
        "| `app_screens` | product walkthrough | 20s |\n"
        "| `product_sizzle` | launch reel | 30s |\n\n"
        "---\n\n"
        "## Checklist\n\n"
        "- [ ] Review Product Hunt draft\n"
        "- [ ] Review outreach seed list\n"
        "- [ ] Review launch thread\n"
        f"- [ ] Confirm live URL: {checklist_url}\n"
        "- [ ] Generate campaign videos (FAL_API_KEY required)\n"
        "- [ ] Product Hunt submission (when ≥ 10 paying customers)\n"
    )


def _notify_launch_ready(context: ProjectContext, log_fn) -> None:
    """Send Telegram notification — best-effort, never raises."""
    try:
        from agents.hermes import TelegramNotifier
        tg = TelegramNotifier(
            token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        )
        tg.send(
            f"*LAUNCH.md ready for review*\n"
            f"Project: `{context.project_id}`\n"
            "3 draft sections: PH listing · outreach seed · launch thread.\n"
            "Review LAUNCH.md before posting anything."
        )
    except Exception as e:
        log_fn(f"[launch] telegram notify skipped: {e}")


__all__ = ["LaunchAgent"]
