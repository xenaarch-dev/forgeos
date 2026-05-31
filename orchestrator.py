"""
ForgeOS V2 — orchestrator entry point.

The default pipeline is now driven by HermesOrchestrator which runs:
  GStack planning gates -> ArchitectAgent -> GStack design gates ->
  MissionOrchestrator -> ScaffoldAgent -> MissionWorkerLoop ->
  GStack review gates -> SecurityAgent -> GStack CSO gate ->
  QAGate -> MissionValidator -> ShipGate -> DeployAgent

Use --legacy flag to run the original flat pipeline without GStack or Missions.

Usage:
    # Default (V2 — GStack + Missions + Hermes)
    PYTHONPATH=. python3 orchestrator.py --idea "Build ContractForge"

    # Legacy (V1 — flat pipeline, faster, no gates)
    PYTHONPATH=. python3 orchestrator.py --idea "..." --legacy

    # Resume an existing build
    PYTHONPATH=. python3 orchestrator.py --idea "..." --workdir builds/<id>
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

from agents import (
    ArchitectAgent,
    BaseAgent,
    CoderAgent,
    DeployAgent,
    GameAgent,
    ScaffoldAgent,
    SecurityAgent,
)
from config import RUNTIME
from models import AgentResult, AgentStatus, Phase, ProjectContext


# ---------------------------------------------------------------------------
# Console helper — works with or without `rich`.
# ---------------------------------------------------------------------------


class _Console:
    def __init__(self) -> None:
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.text import Text

            self._rich = Console()
            self._Panel = Panel
            self._Text = Text
        except Exception:
            self._rich = None
            self._Panel = None
            self._Text = None

    def banner(self, title: str, subtitle: str = "") -> None:
        if self._rich:
            text = self._Text(subtitle, style="dim") if subtitle else ""
            self._rich.print(self._Panel.fit(self._Text(title, style="bold magenta"), title=""))
            if subtitle:
                self._rich.print(text)
        else:
            line = "=" * max(8, len(title) + 4)
            sys.stderr.write(f"\n{line}\n  {title}\n{line}\n")
            if subtitle:
                sys.stderr.write(subtitle + "\n")
            sys.stderr.flush()

    def step(self, agent: str, status: str, detail: str = "") -> None:
        if self._rich:
            colour = {
                "running": "cyan",
                "success": "green",
                "failed": "red",
                "degraded": "yellow",
                "skipped": "dim",
            }.get(status, "white")
            self._rich.print(f"[{colour}]-> {agent:<16}[/] {status} {detail}")
        else:
            sys.stderr.write(f"-> {agent:<16} {status} {detail}\n")
            sys.stderr.flush()

    def info(self, msg: str) -> None:
        if self._rich:
            self._rich.print(f"[dim]{msg}[/dim]")
        else:
            sys.stderr.write(msg + "\n")

    def warn(self, msg: str) -> None:
        if self._rich:
            self._rich.print(f"[yellow]! {msg}[/yellow]")
        else:
            sys.stderr.write(f"! {msg}\n")

    def error(self, msg: str) -> None:
        if self._rich:
            self._rich.print(f"[red]X {msg}[/red]")
        else:
            sys.stderr.write(f"X {msg}\n")


# ---------------------------------------------------------------------------
# Legacy V1 orchestrator (kept for --legacy flag)
# ---------------------------------------------------------------------------


class Orchestrator:
    """Original flat-pipeline orchestrator. Use --legacy to activate."""

    AGENTS: list[type[BaseAgent]] = [
        ArchitectAgent,
        ScaffoldAgent,
        CoderAgent,
        GameAgent,
        SecurityAgent,
        DeployAgent,
    ]

    def __init__(self, idea: str, workdir: str | None = None) -> None:
        wd = workdir or str(Path(RUNTIME.workdir_root))
        self.context = ProjectContext.new(idea=idea, workdir=wd)
        self.console = _Console()
        self.statuses: list[dict[str, Any]] = []

    def run(self) -> ProjectContext:
        self.console.banner(
            "ForgeOS V1 (legacy)",
            f"project_id={self.context.project_id} workdir={self.context.workdir}",
        )
        self.context.save()

        for agent_cls in self.AGENTS:
            self._run_agent(agent_cls)

        if RUNTIME.enable_obsidian:
            try:
                from forge_brain import ForgeBrain

                brain = ForgeBrain()
                notes = brain.compile_from(self.context)
                audited = brain.audit(notes)
                brain.write(audited)
                self.console.info(f"Wrote {len(audited)} wiki notes to vault")
            except Exception as e:
                self.console.warn(f"forge_brain skipped: {e}")

        self._write_status_md()
        self._write_summary_md()
        return self.context

    def _run_agent(self, agent_cls: type[BaseAgent]) -> None:
        agent = agent_cls()
        attempts = 0
        last_result: AgentResult | None = None
        delay = RUNTIME.retry_backoff_base

        while attempts < RUNTIME.max_agent_retries:
            attempts += 1
            self.console.step(agent.name, "running", f"(attempt {attempts})")
            try:
                last_result = agent.run(self.context)
                last_result.retries = attempts - 1
            except Exception as e:
                self.console.error(f"{agent.name} crashed: {e}")
                tb = traceback.format_exc()
                last_result = AgentResult.started(agent.name).finalize(
                    AgentStatus.FAILED, error=f"{type(e).__name__}: {e}"
                )
                last_result.log.append(tb)
                self.context.record_agent(last_result)

            self.context.save()
            if last_result.status == AgentStatus.SUCCESS.value:
                self.console.step(
                    agent.name, "success", f"in {last_result.duration_seconds:.1f}s"
                )
                self.statuses.append({"agent": agent.name, "status": "success"})
                return

            if attempts < RUNTIME.max_agent_retries:
                self.console.warn(f"{agent.name} failed, retrying in {delay:.1f}s …")
                time.sleep(delay)
                delay *= 2
                continue

        self.console.error(
            f"{agent.name} failed after {attempts} attempts: "
            f"{last_result.error if last_result else 'unknown'}"
        )
        self.statuses.append(
            {
                "agent": agent.name,
                "status": "degraded",
                "error": last_result.error if last_result else "unknown",
            }
        )

    def _write_status_md(self) -> None:
        rows = "\n".join(
            f"- **{s['agent']}** — {s['status']}"
            + (f" — {s.get('error')}" if s.get("error") else "")
            for s in self.statuses
        ) or "- (no agents executed)"
        self.context.write_artifact(
            "STATUS.md",
            "# ForgeOS Status\n\n"
            f"Project: `{self.context.project_id}`\n"
            f"Idea: {self.context.idea}\n\n"
            "## Agent results\n\n"
            f"{rows}\n",
        )

    def _write_summary_md(self) -> None:
        s = self.context.summary()
        deploy_md = (
            f"- Repo: {s['repo_url'] or '(none)'}\n"
            f"- Backend: {s['backend_url'] or '(none)'}\n"
            f"- Frontend: {s['frontend_url'] or '(none)'}\n"
        )
        cost = s["cost_usd"]
        tokens = s["tokens"]
        self.context.write_artifact(
            "SUMMARY.md",
            "# ForgeOS Build Summary\n\n"
            f"Project: `{s['project_id']}`\n"
            f"Idea: {s['idea']}\n\n"
            "## Stack\n\n"
            "```json\n" + _safe_json(s["stack"]) + "\n```\n\n"
            "## Deployment\n\n"
            f"{deploy_md}\n"
            "## Cost & tokens\n\n"
            f"- Tokens: {tokens}\n"
            f"- Cost (USD): {cost}\n\n"
            "## Failures\n\n"
            + (
                "\n".join(
                    f"- {f.get('agent')} — {f.get('error')}" for f in s["failures"]
                )
                or "(none)"
            )
            + "\n",
        )


def _safe_json(obj: Any) -> str:
    import json

    return json.dumps(obj, indent=2, default=str)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ForgeOS orchestrator")
    parser.add_argument("--idea", help="Idea to build")
    parser.add_argument(
        "--idea-file", default="idea.txt", help="Fallback file with the idea"
    )
    parser.add_argument("--workdir", help="Workdir override")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use V1 flat pipeline (no GStack gates, no Missions)",
    )
    args = parser.parse_args(argv)

    idea = args.idea or ""
    if not idea and os.path.exists(args.idea_file):
        idea = Path(args.idea_file).read_text(encoding="utf-8").strip()
    if not idea:
        sys.stderr.write("No --idea provided and no idea.txt found. Aborting.\n")
        return 2

    if args.legacy:
        sys.stderr.write("[orchestrator] running V1 legacy pipeline\n")
        orch = Orchestrator(idea=idea, workdir=args.workdir)
        orch.run()
        sys.stderr.write(
            f"\nForgeOS V1 run complete. See {orch.context.workdir}/SUMMARY.md\n"
        )
    else:
        sys.stderr.write("[orchestrator] running V2 pipeline (GStack + Missions)\n")
        from agents.hermes import HermesOrchestrator

        hermes = HermesOrchestrator(idea=idea, workdir=args.workdir)
        try:
            ctx = hermes.run()
            sys.stderr.write(
                f"\nForgeOS V2 run complete.\n"
                f"  Project:  {ctx.project_id}\n"
                f"  Workdir:  {ctx.workdir}\n"
                f"  Repo:     {ctx.repo_url or '(none)'}\n"
                f"  Backend:  {ctx.backend_url or '(none)'}\n"
                f"  Frontend: {ctx.frontend_url or '(none)'}\n"
            )
        except RuntimeError as e:
            sys.stderr.write(f"\nForgeOS V2 STOPPED: {e}\n")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
