"""ForgeOS agents.

BaseAgent is eager-loaded (no forge_sdk dependency — safe).
All agent subclasses are lazy-loaded via module __getattr__ to break the
circular import: forge_sdk.agent → agents.base → agents.__init__ →
agents.architect → forge_sdk.agent (not yet initialized).
"""

from agents.base import BaseAgent

# ---------------------------------------------------------------------------
# Lazy import map: public name → module path
# ---------------------------------------------------------------------------

_LAZY: dict[str, str] = {
    # V1 workers
    "ArchitectAgent":    "agents.architect",
    "ScaffoldAgent":     "agents.scaffold",
    "CoderAgent":        "agents.coder",
    "SecurityAgent":     "agents.security",
    "DeployAgent":       "agents.deploy",
    "GameAgent":         "agents.game",
    # GStack quality gates
    "GStackGate":        "agents.gstack",
    "OfficeHoursGate":   "agents.gstack",
    "CEOReviewGate":     "agents.gstack",
    "EngReviewGate":     "agents.gstack",
    "DesignShotgunGate": "agents.gstack",
    "ReviewGate":        "agents.gstack",
    "AdversarialGate":   "agents.gstack",
    "ScoreGate":         "agents.gstack",
    "CSOGate":           "agents.gstack",
    "QAGate":            "agents.gstack",
    "ShipGate":          "agents.gstack",
    # Launch
    "LaunchAgent":         "agents.launch",
    # Mission system
    "MissionOrchestrator": "agents.mission",
    "MissionWorker":       "agents.mission",
    "MissionWorkerLoop":   "agents.mission",
    "MissionValidator":    "agents.mission",
    # Hermes orchestrator
    "HermesGateway":      "agents.hermes",
    "HermesOrchestrator": "agents.hermes",
    "TelegramNotifier":   "agents.hermes",
}


def __getattr__(name: str):
    """Lazy-load an agent class on first access and cache it in this module."""
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(_LAZY[name])
        val = getattr(mod, name)
        globals()[name] = val   # cache — subsequent accesses skip __getattr__
        return val
    raise AttributeError(f"module 'agents' has no attribute {name!r}")


__all__ = [
    # Always available
    "BaseAgent",
    # V1 workers
    "ArchitectAgent",
    "ScaffoldAgent",
    "CoderAgent",
    "SecurityAgent",
    "DeployAgent",
    "GameAgent",
    # GStack gates
    "GStackGate",
    "OfficeHoursGate",
    "CEOReviewGate",
    "EngReviewGate",
    "DesignShotgunGate",
    "ReviewGate",
    "AdversarialGate",
    "ScoreGate",
    "CSOGate",
    "QAGate",
    "ShipGate",
    # Launch
    "LaunchAgent",
    # Mission system
    "MissionOrchestrator",
    "MissionWorker",
    "MissionWorkerLoop",
    "MissionValidator",
    # Hermes
    "HermesGateway",
    "HermesOrchestrator",
    "TelegramNotifier",
]
