"""
ForgeSDK — ForgeAgent base class.

ForgeAgent is the developer-facing abstraction for building ForgeOS pipeline
agents. It wraps BaseAgent with:

  - Declarative capability / requirement metadata (used by agent-organizer)
  - Automatic GBrainLogger integration (per-run structured event log)
  - Per-run USD budget enforcement (raises LLMError before spend exceeds cap)
  - Event callback hook (used by api.py SSE streaming)

All existing agents (BaseAgent subclasses) remain valid — this is additive.
New agents that need the extra features inherit from ForgeAgent instead.

Compatibility guarantee: ForgeAgent.run() has the same signature as
BaseAgent.run(), so HermesOrchestrator / Orchestrator call it identically.
"""

from __future__ import annotations

import abc
import traceback
from typing import Any, Callable

from agents.base import BaseAgent
from forge_sdk.glogger import GBrainLogger
from models import AgentResult, AgentStatus, LLMError, ProjectContext


EventCallback = Callable[[str, dict[str, Any]], None]


class ForgeAgent(BaseAgent):
    """Enhanced base class for ForgeOS pipeline agents.

    Class-level attributes to declare in subclasses::

        name = "my_agent"
        phase = "build"
        capabilities = ["SPEC.md", "ARCH.md"]      # what this agent produces
        requires = ["idea", "stack"]                # what it reads from context
        budget_usd = 0.20                           # max spend; 0.0 = unlimited

    Optionally, pass event_callback and/or logger at construction time for
    SSE streaming and custom log destinations.
    """

    # Subclasses override these at the class level.
    capabilities: list[str] = []
    requires: list[str] = []
    budget_usd: float = 0.0

    def __init__(
        self,
        event_callback: EventCallback | None = None,
        logger: GBrainLogger | None = None,
    ) -> None:
        self._event_cb = event_callback
        self._logger = logger or GBrainLogger(agent_name=self.name)

    # ------------------------------------------------------------------
    # Public entry point (overrides BaseAgent.run)
    # ------------------------------------------------------------------

    def run(self, context: ProjectContext) -> AgentResult:  # type: ignore[override]
        self._logger.start(context.project_id)
        self._emit("start", {"agent": self.name, "phase": self.phase})

        result = AgentResult.started(self.name)
        context.current_phase = self.phase
        self._log(f"[{self.name}] starting (phase={self.phase})")

        try:
            self._check_budget(context)
            output = self._execute(context) or {}
            result.finalize(AgentStatus.SUCCESS, output=output)
            self._log(f"[{self.name}] succeeded in {result.duration_seconds:.1f}s")
            self._emit("success", {"agent": self.name, "output_keys": list(output)})
        except LLMError as e:
            msg = f"LLMError: {e}"
            result.finalize(AgentStatus.FAILED, error=msg)
            self._log(f"[{self.name}] FAILED: {msg}")
            self._emit("error", {"agent": self.name, "error": msg})
        except Exception as e:
            tb = traceback.format_exc()
            msg = f"{type(e).__name__}: {e}"
            result.finalize(AgentStatus.FAILED, error=msg)
            result.log.append(tb)
            self._log(f"[{self.name}] FAILED: {msg}")
            self._emit("error", {"agent": self.name, "error": msg})
        finally:
            context.record_agent(result)
            context.save()
            self._logger.finish(result)

        return result

    @abc.abstractmethod
    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        """Subclasses implement the agent's actual work here."""

    # ------------------------------------------------------------------
    # Helpers — available to subclasses
    # ------------------------------------------------------------------

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        """Log the event and forward it to the SSE callback (best-effort)."""
        self._logger.log_event(event, payload)
        if self._event_cb:
            try:
                self._event_cb(event, payload)
            except Exception:
                pass

    def _check_budget(self, context: ProjectContext) -> None:
        """Raise LLMError if the build has already exceeded this agent's budget."""
        if self.budget_usd <= 0.0:
            return
        spent = context.total_cost()
        if spent >= self.budget_usd:
            raise LLMError(
                f"{self.name}: budget exhausted "
                f"(spent=${spent:.4f} >= limit=${self.budget_usd:.2f})"
            )

    def _describe(self) -> dict[str, Any]:
        """Machine-readable agent descriptor for agent-organizer routing."""
        return {
            "name": self.name,
            "phase": self.phase,
            "capabilities": list(self.capabilities),
            "requires": list(self.requires),
            "budget_usd": self.budget_usd,
        }


__all__ = ["EventCallback", "ForgeAgent"]
