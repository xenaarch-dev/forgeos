"""
Agent Builder — user-defined ForgeOS agents with skills, tools, MCP and plugins.

    spec.py     AgentSpec: the declarative definition (pure data)
    catalog.py  skills (SKILL.md folders), tools, MCP presets, plugin bundles
    store.py    flat-file persistence, one JSON per agent per owner
    runtime.py  spec -> ForgeAgent subclass, and spec -> Claude Code export

Only the light modules are exported here; import agent_builder.runtime
directly when you need to run an agent (it pulls in the agent stack).
"""

from agent_builder.catalog import catalog_payload, resolve, validate_spec
from agent_builder.spec import AgentSpec, McpServer, ModelTier, Prop
from agent_builder.store import AgentStore, AgentStoreError

__all__ = [
    "AgentSpec", "AgentStore", "AgentStoreError", "McpServer", "ModelTier", "Prop",
    "catalog_payload", "resolve", "validate_spec",
]
