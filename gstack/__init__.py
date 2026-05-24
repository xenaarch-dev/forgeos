"""GStack — ForgeOS quality gate runner."""
from .runner import GStackRunner
from .gates import GATE_REGISTRY

__all__ = ['GStackRunner', 'GATE_REGISTRY']
