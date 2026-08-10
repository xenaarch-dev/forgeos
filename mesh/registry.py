"""
CapabilityRegistry — Capability -> adapter.

SPEC_AgentMesh.md §3f. This is the dispatch table a RouteDecision is looked up
in once the router has answered.

Routing and dispatch are deliberately separate concerns. The router always
answers from the closed Capability enum (§3a); whether an adapter is bound yet
is the registry's business, not the classifier's. `get()` returning None stays
the honest answer for anything not wired.

Phase 2 binds CONTRACT and OUTREACH. SPEC and BUILD remain unbound: SPEC waits
on the §10.2 measurement of whether a full ArchitectAgent run fits inside a
conversational turn, and BUILD delegates to POST /builds, which is Phase 3.
"""

from __future__ import annotations

from typing import Any, Iterator

from mesh.models import DISPATCHABLE, Capability


class CapabilityRegistry:
    """Bindings from a dispatchable Capability to the adapter that runs it."""

    def __init__(self) -> None:
        self._adapters: dict[Capability, Any] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, capability: Capability, adapter: Any) -> None:
        if capability not in DISPATCHABLE:
            raise ValueError(
                f"{capability.value} is a terminal routing outcome, "
                "not a dispatch target"
            )
        if capability in self._adapters:
            raise ValueError(f"{capability.value} is already registered")
        self._adapters[capability] = adapter

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, capability: Capability) -> Any | None:
        """The bound adapter, or None when nothing is wired for it yet."""
        return self._adapters.get(capability)

    def is_registered(self, capability: Capability) -> bool:
        return capability in self._adapters

    def registered(self) -> list[Capability]:
        return [c for c in DISPATCHABLE if c in self._adapters]

    def unregistered(self) -> list[Capability]:
        return [c for c in DISPATCHABLE if c not in self._adapters]

    # ------------------------------------------------------------------
    # Dunders
    # ------------------------------------------------------------------

    def __contains__(self, capability: object) -> bool:
        return capability in self._adapters

    def __len__(self) -> int:
        return len(self._adapters)

    def __iter__(self) -> Iterator[Capability]:
        return iter(self.registered())

    def __repr__(self) -> str:
        bound = ", ".join(c.value for c in self.registered()) or "empty"
        return f"<CapabilityRegistry {bound}>"


def default_registry() -> CapabilityRegistry:
    """The registry the CLI and, from Phase 3, the HTTP layer dispatch through.

    Adapter *classes* are registered, not instances: each command constructs its
    own so it can be handed a per-command event_callback for the SSE stream.

    Imports are local to keep `import mesh` cheap and to keep the adapters —
    which pull in agents, llm and forge_sdk — off the import path of anything
    that only needs the routing contracts.
    """
    from mesh.capabilities.contract import ContractCapability
    from mesh.capabilities.outreach import OutreachCapability

    registry = CapabilityRegistry()
    registry.register(Capability.CONTRACT, ContractCapability)
    registry.register(Capability.OUTREACH, OutreachCapability)
    return registry


__all__ = ["CapabilityRegistry", "default_registry"]
