"""
ForgeOS agent mesh — a capability router with a conversational surface.

One free-text command in; a RouteDecision out. See SPEC_AgentMesh.md.

`mesh` is a top-level package, not a subpackage of `agents`: it is a
coordination layer that *consumes* agents, and nesting it under `agents/` would
invite the circular-import class of bug that `agents/__init__.py`'s lazy
`__getattr__` exists to prevent (§3f).
"""

from __future__ import annotations

from mesh.models import (
    CLARIFY_THRESHOLD,
    DISPATCHABLE,
    DISPATCH_THRESHOLD,
    DISPLAY_NAMES,
    MESH_ARGS_KEY,
    ArtifactStatus,
    ArtifactType,
    Capability,
    MeshArtifact,
    RouteDecision,
    mesh_args,
)
from mesh.registry import CapabilityRegistry, default_registry
from mesh.router import ROUTER_STAGE, MeshRouter

__all__ = [
    "CLARIFY_THRESHOLD",
    "DISPATCHABLE",
    "DISPATCH_THRESHOLD",
    "DISPLAY_NAMES",
    "MESH_ARGS_KEY",
    "ROUTER_STAGE",
    "ArtifactStatus",
    "ArtifactType",
    "Capability",
    "CapabilityRegistry",
    "MeshArtifact",
    "MeshRouter",
    "RouteDecision",
    "default_registry",
    "mesh_args",
]
