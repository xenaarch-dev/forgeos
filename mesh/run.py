"""
Mesh CLI — one command in, one transcript out.

    PYTHONPATH=. python3 -m mesh.run "generate an NDA for a fintech client"

SPEC_AgentMesh.md §8, Phase 2. This is the whole surface for now: no HTTP, no
UI. The event stream is printed rather than pushed over SSE, but it comes from
the same ForgeAgent event_callback that Phase 3 will hand to an asyncio.Queue,
so wiring the endpoint later is a change of sink, not of plumbing.

Exit codes:
    0  a capability ran, or the mesh honestly answered that it will not run one
    1  a dispatched capability failed
    2  the capability is real but has no adapter wired yet
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path
from typing import Any, Sequence

from config import RUNTIME
from mesh.models import MESH_ARGS_KEY, Capability, RouteDecision
from mesh.registry import default_registry
from mesh.router import MeshRouter
from mesh.store import MeshStore
from models import AgentStatus, ProjectContext

#: <workdir_root>/commands/<command_id>/artifacts/<slug>.md
#:
#: RUNTIME.workdir_root is what the API and production actually use, so the CLI
#: follows it rather than the other way round. Phase 3 shipped these diverged
#: (CLI wrote a relative builds/commands/); one command should not land in two
#: different places depending on how it was submitted.
COMMANDS_ROOT = str(Path(RUNTIME.workdir_root) / "commands")


def _out(line: str = "") -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _new_command_id() -> str:
    return f"cmd-{uuid.uuid4().hex[:12]}"


def _print_event(event: str, payload: dict[str, Any]) -> None:
    """Render one agent event as a transcript line."""
    if event == "route":
        return  # rendered separately, with the confidence policy applied
    if event == "artifact_ready":
        _out(f"  [artifact] {payload.get('title', '')}")
        return
    if event == "error":
        _out(f"  [error] {payload.get('error', '')}")
        return
    if event in ("start", "success", "finish"):
        _out(f"  [{event}] {payload.get('agent', '')}")
        return
    _out(f"  [{event}] {payload.get('reason', '') or payload.get('agent', '')}")


def _render_route(decision: RouteDecision) -> None:
    # CLARIFY and UNSUPPORTED are not routed anywhere, so they get no
    # "Routing to ..." line — the rationale is the whole answer.
    if decision.should_dispatch:
        _out(decision.transcript_prefix or f"Routing to {decision.display_name}.")
    _out(f"  {decision.rationale}")
    _out(f"  (confidence {decision.confidence:.2f})")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m mesh.run",
        description="Route one free-text command through the ForgeOS agent mesh.",
    )
    parser.add_argument("text", nargs="+", help="the command, e.g. 'generate an NDA'")
    parser.add_argument(
        "--workdir",
        default=None,
        help=f"command workdir (default: {COMMANDS_ROOT}/<command_id>)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="route only; print the decision and stop without dispatching",
    )
    args = parser.parse_args(argv)

    text = " ".join(args.text).strip()
    command_id = _new_command_id()
    workdir = Path(args.workdir or f"{COMMANDS_ROOT}/{command_id}")
    context = ProjectContext.new(idea=text, workdir=str(workdir), build_id=command_id)

    # Same write-through as the HTTP surface: a command submitted from the CLI
    # is still a command, and should not be invisible to the dashboard.
    store = MeshStore()
    thread_row_id = store.create_thread(command_id, text, workdir=str(workdir))

    _out(f"> {text}")
    decision = MeshRouter(event_callback=_print_event).route(context, text)
    _render_route(decision)
    store.update_thread(
        command_id,
        routed_capability=decision.capability.value,
        confidence=decision.confidence,
    )

    if decision.capability is Capability.CLARIFY:
        store.update_thread(command_id, status="clarify", detail=decision.rationale)
        return 0
    if decision.capability is Capability.UNSUPPORTED:
        _out(f"  {decision.unsupported_reason}")
        store.update_thread(
            command_id, status="unsupported", detail=decision.unsupported_reason
        )
        return 0
    if not decision.should_dispatch:
        return 0
    if args.dry_run:
        _out("  (dry run - not dispatched)")
        return 0

    adapter_cls = default_registry().get(decision.capability)
    if adapter_cls is None:
        detail = f"{decision.display_name} has no adapter wired yet. Nothing ran."
        _out(f"  {detail}")
        store.update_thread(command_id, status="unwired", detail=detail)
        return 2

    context.metadata[MESH_ARGS_KEY] = dict(decision.args)
    result = adapter_cls(event_callback=_print_event).run(context)

    if result.status != AgentStatus.SUCCESS.value:
        _out(f"  FAILED: {result.error}")
        store.update_thread(command_id, status="failed", error=result.error)
        return 1

    if thread_row_id:
        stored_artifact = (result.output or {}).get("artifact")
        if stored_artifact:
            store.insert_artifact(thread_row_id, stored_artifact)
    store.update_thread(command_id, status="success")

    artifact = result.output.get("artifact") or {}
    _out("")
    _out(f"Artifact: {artifact.get('title', '(untitled)')}")
    _out(f"  status:  {artifact.get('status', '')}")
    _out(f"  file:    {result.output.get('artifact_path', '')}")
    _out(f"  workdir: {workdir}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
