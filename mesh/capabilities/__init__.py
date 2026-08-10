"""
Mesh capability adapters.

Every capability is a ForgeAgent subclass (§4c), even when what it wraps is
not one. The adapter is the seam where a heterogeneous agent signature gets
normalised into the mesh contract — without editing the agent itself, so its
proven prompts are reused verbatim rather than rewritten under time pressure.

Modules import from `mesh.models` directly, never from `mesh`, so the package
__init__ can import the registry without a cycle.
"""

from __future__ import annotations

__all__: list[str] = []
