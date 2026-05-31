"""ForgeOS agents."""

from .base import BaseAgent
from .architect import ArchitectAgent
from .scaffold import ScaffoldAgent
from .coder import CoderAgent
from .security import SecurityAgent
from .deploy import DeployAgent
from .game import GameAgent
from .gstack import (
    GStackGate,
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
from .mission import (
    MissionOrchestrator,
    MissionWorker,
    MissionWorkerLoop,
    MissionValidator,
)
from .hermes import HermesGateway, HermesOrchestrator, TelegramNotifier

__all__ = [
    # V1 agents
    "BaseAgent",
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
