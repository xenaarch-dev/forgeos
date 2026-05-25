"""
Hermes — ForgeOS V2 brain and coordinator.

Wraps the full build pipeline with:
- Telegram notifications at every gate and major milestone
- Self-healing (retry on crash, alert on persistent failure)
- Obsidian knowledge base writes after every build
- Dataset flywheel (appends to ~/.forgeos/dataset.jsonl)

Model routing enforced by the pipeline:
  Planning / Architecture  -> Claude Sonnet (hard/architecture tasks)
  Code generation          -> Claude Code CLI or LLM fallback
  Validation / Security    -> Claude Haiku (fast, precise)
  Scaffolding              -> qwen2.5-coder (free, local)

Hermes Agent CLI integration (optional):
  If ~/.local/bin/hermes or ~/.hermes/hermes-agent/venv/bin/hermes is
  installed, HermesGateway routes notifications through it and exposes
  a Telegram-triggered build entrypoint.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import ProjectContext


# ---------------------------------------------------------------------------
# Hermes CLI gateway (optional — used when Hermes Agent is installed)
# ---------------------------------------------------------------------------

def _find_hermes_bin() -> str | None:
    """Return path to the hermes binary if installed, else None."""
    # Prefer system PATH first
    found = shutil.which("hermes")
    if found:
        return found
    # Try well-known install locations
    candidates = [
        Path.home() / ".local" / "bin" / "hermes",
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes",
    ]
    for p in candidates:
        if p.is_file() and p.stat().st_mode & 0o111:
            return str(p)
    return None


_HERMES_BIN: str | None = _find_hermes_bin()


class HermesGateway:
    """
    Thin wrapper around the Hermes Agent CLI.

    Provides:
    - send_notification(text) — fires a one-shot agent prompt that delivers
      a Telegram message through the configured Hermes gateway.
    - is_available() — True when the hermes binary is installed.

    Falls back silently when Hermes is not installed so the rest of the
    pipeline is never blocked by missing optional tooling.
    """

    def __init__(self) -> None:
        self._bin = _HERMES_BIN

    def is_available(self) -> bool:
        return self._bin is not None

    def send_notification(self, text: str, timeout: int = 30) -> bool:
        """Send text via Hermes Agent (best-effort, never raises)."""
        if not self._bin:
            return False
        try:
            result = subprocess.run(
                [
                    self._bin,
                    "--yolo",
                    "-z",
                    f"Send this message to the configured Telegram gateway: {text}",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0
        except Exception as e:
            sys.stderr.write(f"[hermes/gateway] {e}\n")
            return False

    @staticmethod
    def skill_path() -> Path:
        """Path to the ForgeOS skill file for the Hermes Agent."""
        return Path.home() / ".hermes" / "skills" / "forgeos" / "SKILL.md"


class TelegramNotifier:
    """
    Sends messages to a Telegram chat.

    Strategy:
    1. Direct Telegram Bot API — fast, no extra deps, works when token/chat_id set.
    2. Hermes CLI gateway — used when Bot API not configured but hermes is installed.
    """

    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id
        self._enabled = bool(token and chat_id)
        self._gateway = HermesGateway()

    def send(self, text: str) -> bool:
        if not self._enabled:
            # Fall back to Hermes CLI gateway if installed
            if self._gateway.is_available():
                return self._gateway.send_notification(text)
            return False
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload = json.dumps(
            {"chat_id": self._chat_id, "text": text[:4096], "parse_mode": "Markdown"}
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return True
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            sys.stderr.write(f"[hermes/tg] {e}\n")
            return False

    def gate(self, gate_name: str, project_id: str, score: float, passed: bool) -> None:
        icon = "OK" if passed else "BLOCKED"
        self.send(
            f"*[{icon}] Gate: {gate_name}*\n"
            f"Project: `{project_id}`\n"
            f"Score: {score:.1f}/10 | {'PASS' if passed else 'FAIL'}"
        )

    def build_start(self, idea: str, project_id: str) -> None:
        self.send(
            f"*ForgeOS Build Started*\n"
            f"Idea: _{idea}_\n"
            f"ID: `{project_id}`"
        )

    def build_done(
        self,
        project_id: str,
        repo_url: str,
        backend_url: str,
        frontend_url: str,
    ) -> None:
        parts = [f"*ForgeOS Build Complete*\nID: `{project_id}`"]
        if repo_url:
            parts.append(f"Repo: {repo_url}")
        if backend_url:
            parts.append(f"Backend: {backend_url}")
        if frontend_url:
            parts.append(f"Frontend: {frontend_url}")
        if len(parts) == 1:
            parts.append("No deploy URLs — check logs.")
        self.send("\n".join(parts))

    def build_failed(self, project_id: str, stage: str, error: str) -> None:
        self.send(
            f"*ForgeOS Build FAILED*\n"
            f"ID: `{project_id}`\n"
            f"Stage: {stage}\n"
            f"Error: {error[:300]}"
        )

    def feature_done(self, feature: str, index: int, total: int) -> None:
        self.send(f"*Feature {index}/{total}* complete: _{feature}_")


class HermesOrchestrator:
    """
    ForgeOS V2 main orchestrator. Runs GStack + Missions + Deploy pipeline.

    Usage:
        hermes = HermesOrchestrator(idea="Build ContractForge")
        context = hermes.run()
    """

    def __init__(
        self,
        idea: str,
        workdir: str | None = None,
        build_id: str | None = None,
    ) -> None:
        import os
        import time
        import re as _re
        from config import RUNTIME

        if workdir:
            wd = str(Path(workdir).expanduser().resolve())
        else:
            # Create a unique per-build directory under builds/
            slug = _re.sub(r"[^a-z0-9]+", "-", idea.lower().strip())[:32].strip("-")
            ts = int(time.time())
            folder = f"{slug}-{ts}"
            builds_root = Path(RUNTIME.workdir_root).parent / "builds"
            builds_root.mkdir(parents=True, exist_ok=True)
            wd = str(builds_root / folder)

        # Load existing context if the workdir already has one (resume mode).
        ctx_path = Path(wd) / "context.json"
        if ctx_path.exists():
            try:
                self.context = ProjectContext.load(ctx_path)
                self._log(f"[hermes] RESUME: loaded existing context from {ctx_path}")
            except Exception as _e:
                self._log(f"[hermes] resume load failed ({_e}), starting fresh")
                self.context = ProjectContext.new(idea=idea, workdir=wd, build_id=build_id)
        else:
            self.context = ProjectContext.new(idea=idea, workdir=wd, build_id=build_id)
        self.tg = TelegramNotifier(
            token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        )
        self._stage_log: list[dict[str, Any]] = []

    def run(self) -> ProjectContext:
        self._log(f"[hermes] build start: {self.context.project_id}")
        self.tg.build_start(self.context.idea, self.context.project_id)
        self.context.save()

        for stage in self._build_pipeline():
            self._run_stage(stage)

        self._write_obsidian()
        self._append_dataset()
        self.tg.build_done(
            self.context.project_id,
            self.context.repo_url,
            self.context.backend_url,
            self.context.frontend_url,
        )
        return self.context

    # ------------------------------------------------------------------
    # Pipeline definition
    # ------------------------------------------------------------------

    def _build_pipeline(self) -> list[dict[str, Any]]:
        from agents.architect import ArchitectAgent
        from agents.scaffold import ScaffoldAgent
        from agents.security import SecurityAgent
        from agents.deploy import DeployAgent
        from agents.game import GameAgent
        from agents.gstack import (
            OfficeHoursGate,
            CEOReviewGate,
            EngReviewGate,
            DesignShotgunGate,
            ReviewGate,
            AdversarialGate,
            ScoreGate,
            CSOGate,
            QAGate,
            ShipGate,
        )
        from agents.mission import (
            MissionOrchestrator,
            MissionWorkerLoop,
            MissionValidator,
        )

        return [
            # Planning gate (idea viability — no spec needed)
            {"name": "office_hours",   "cls": OfficeHoursGate,   "gate": True},
            # Architecture — produces SPEC.md, ARCH.md, TASKS.json
            {"name": "architect",      "cls": ArchitectAgent,    "gate": False},
            # Business review — now has access to the spec
            {"name": "ceo_review",     "cls": CEOReviewGate,     "gate": True},
            # Design gates
            {"name": "eng_review",     "cls": EngReviewGate,     "gate": True},
            {"name": "design_shotgun", "cls": DesignShotgunGate, "gate": False},
            # Mission planning
            {"name": "mission_plan",   "cls": MissionOrchestrator, "gate": False},
            # Scaffold
            {"name": "scaffold",       "cls": ScaffoldAgent,     "gate": False},
            # Game (self-skips if not a game idea)
            {"name": "game",           "cls": GameAgent,         "gate": False},
            # Feature implementation
            {"name": "mission_work",   "cls": MissionWorkerLoop, "gate": False},
            # Review gates
            {"name": "review",         "cls": ReviewGate,        "gate": True},
            {"name": "adversarial",    "cls": AdversarialGate,   "gate": True},
            {"name": "score",          "cls": ScoreGate,         "gate": True},
            # Security
            {"name": "security",       "cls": SecurityAgent,     "gate": False},
            {"name": "cso",            "cls": CSOGate,           "gate": True},
            # QA
            {"name": "qa",             "cls": QAGate,            "gate": True},
            # Adversarial contract validation
            {"name": "validator",      "cls": MissionValidator,  "gate": False},
            # Final ship gate
            {"name": "ship",           "cls": ShipGate,          "gate": True},
            # Deploy
            {"name": "deploy",         "cls": DeployAgent,       "gate": False},
        ]

    # ------------------------------------------------------------------
    # Stage runner
    # ------------------------------------------------------------------

    def _completed_stages(self) -> set[str]:
        """Return set of stage names that already passed in a prior run (from context.json)."""
        completed = set()
        # Check agent results — may be AgentResult dataclass objects or plain dicts
        for result in (self.context.agent_results or []):
            if isinstance(result, dict):
                status = result.get("status", "")
                agent_name = result.get("agent", result.get("agent_name", ""))
            else:
                status = getattr(result, "status", "")
                agent_name = getattr(result, "agent", "")
            if status == "success" and agent_name:
                completed.add(agent_name)
                # stage name "office_hours" matches agent name "office_hours_gate"
                if agent_name.endswith("_gate"):
                    completed.add(agent_name[:-5])
        # Check gate results — always plain dicts in metadata
        for gate in self.context.metadata.get("gates", []):
            if isinstance(gate, dict) and gate.get("passed"):
                g = gate.get("gate", "")
                if g:
                    completed.add(g)
        # Check stages_done list (stage names recorded on success, bypasses agent-name mismatch)
        for stage_name in self.context.metadata.get("stages_done", []):
            if stage_name:
                completed.add(stage_name)
        return completed

    def _run_stage(self, stage: dict[str, Any]) -> None:
        name = stage["name"]
        cls = stage["cls"]
        is_gate = stage.get("gate", False)
        max_retries = 1 if is_gate else 3

        # Skip stages that already passed in a previous run (resume logic).
        completed = self._completed_stages()
        if name in completed:
            self._log(f"[hermes] -> {name} SKIPPED (already completed)")
            return

        self._log(f"[hermes] -> {name}")
        agent = cls()

        for attempt in range(1, max_retries + 1):
            try:
                result = agent.run(self.context)
                self._stage_log.append(
                    {
                        "name": name,
                        "status": result.status,
                        "duration": result.duration_seconds,
                    }
                )

                if is_gate:
                    out = result.output or {}
                    self.tg.gate(
                        name,
                        self.context.project_id,
                        float(out.get("score", 0)),
                        bool(out.get("passed", result.status == "success")),
                    )

                if result.status == "failed" and is_gate:
                    raise RuntimeError(f"Gate '{name}' failed: {result.error}")

                if result.status == "success":
                    # Record stage name for resume (agent name may differ from stage name)
                    stages_done = self.context.metadata.setdefault("stages_done", [])
                    if name not in stages_done:
                        stages_done.append(name)
                    self.context.save()
                    return

                if attempt < max_retries:
                    self._log(f"[hermes] {name} failed (attempt {attempt}), retrying…")
                    time.sleep(2 ** attempt)

            except RuntimeError:
                self.tg.build_failed(
                    self.context.project_id, name, "Gate blocked pipeline"
                )
                raise
            except Exception as e:
                self._log(f"[hermes] {name} crashed: {e}")
                if attempt == max_retries:
                    self._stage_log.append(
                        {"name": name, "status": "degraded", "error": str(e)}
                    )
                    self.tg.build_failed(
                        self.context.project_id, name, str(e)[:200]
                    )
                else:
                    time.sleep(2 ** attempt)

    # ------------------------------------------------------------------
    # Post-build hooks
    # ------------------------------------------------------------------

    def _write_obsidian(self) -> None:
        try:
            from forge_brain import ForgeBrain

            brain = ForgeBrain()
            notes = brain.compile_from(self.context)
            audited = brain.audit(notes)
            brain.write(audited)
            self._log(f"[hermes] wrote {len(audited)} Obsidian notes")
        except Exception as e:
            self._log(f"[hermes] obsidian write skipped: {e}")

    def _append_dataset(self) -> None:
        try:
            dataset_path = Path.home() / ".forgeos" / "dataset.jsonl"
            dataset_path.parent.mkdir(parents=True, exist_ok=True)
            contract = self.context.metadata.get("validation_contract", {})
            handoffs = self.context.metadata.get("mission_handoffs", [])
            gates = self.context.metadata.get("gates", [])
            avg_score = (
                sum(g.get("score", 0) for g in gates) / len(gates)
                if gates
                else 0.0
            )
            entry = {
                "project_id": self.context.project_id,
                "idea": self.context.idea,
                "spec": (self.context.spec or "")[:500],
                "validation_contract": contract,
                "gstack_score": round(avg_score, 2),
                "deploy_success": bool(
                    self.context.backend_url or self.context.frontend_url
                ),
                "handoffs": handoffs[:5],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            with dataset_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            self._log(f"[hermes] dataset entry -> {dataset_path}")
        except Exception as e:
            self._log(f"[hermes] dataset append failed: {e}")

    def _log(self, msg: str) -> None:
        try:
            sys.stderr.write(msg + "\n")
            sys.stderr.flush()
        except Exception:
            pass


__all__ = ["HermesGateway", "HermesOrchestrator", "TelegramNotifier"]
