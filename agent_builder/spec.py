"""
AgentSpec — the declarative definition of a user-built agent.

A spec is pure data: it names the agent, describes its role, picks a model
tier, and selects skills, tools, MCP servers and plugins from the catalog
(agent_builder/catalog.py). agent_builder/runtime.py turns a spec into a
ForgeAgent subclass; nothing in this module imports the agent stack, so the
API layer can validate specs without pulling in agents/llm.

Security invariant: an MCP server entry is configuration only. ForgeOS never
spawns a stdio command or connects to a server on a spec's behalf. Specs are
exported (Claude Code subagent + .mcp.json) for the founder to run locally,
where the commands run under their own account and permissions.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
MAX_PROMPT_CHARS = 8_000


class ModelTier(str, Enum):
    """How hard the agent thinks. Maps onto llm.router task_complexity."""

    FAST = "fast"            # low    -> cheapest tier
    BALANCED = "balanced"    # medium
    DEEP = "deep"            # hard   -> architecture/security grade

    @property
    def task_complexity(self) -> str:
        # The exact strings llm.router._select_chain matches on.
        return {"fast": "low", "balanced": "medium", "deep": "hard"}[self.value]


class Prop(str, Enum):
    """The object the agent carries on the factory floor (purely visual)."""

    WRENCH = "wrench"
    CLIPBOARD = "clipboard"
    SHIELD = "shield"
    MEGAPHONE = "megaphone"
    SCROLL = "scroll"
    MAGNIFIER = "magnifier"
    ROCKET = "rocket"
    BRAIN = "brain"


class McpServer(BaseModel):
    """One MCP server this agent may use when run under Claude Code."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=40)
    transport: Literal["stdio", "http"] = "stdio"
    command: str | None = Field(default=None, max_length=200)
    args: list[str] = Field(default_factory=list, max_length=20)
    url: str | None = Field(default=None, max_length=300)
    # Names only; values are resolved from the founder's env at run time as
    # ${NAME}. Secrets are never stored in a spec.
    env: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", v):
            raise ValueError("MCP server name: letters, digits, - and _ only")
        return v

    @field_validator("env")
    @classmethod
    def _env(cls, v: list[str]) -> list[str]:
        for key in v:
            if not ENV_KEY_RE.match(key):
                raise ValueError(f"env entry {key!r} must be an UPPER_SNAKE variable name")
        return v

    @model_validator(mode="after")
    def _transport_fields(self) -> "McpServer":
        if self.transport == "stdio":
            if not self.command:
                raise ValueError(f"MCP server {self.name!r}: stdio needs a command")
            self.url = None
        else:
            if not self.url or not self.url.startswith("https://"):
                raise ValueError(f"MCP server {self.name!r}: http needs an https:// url")
            self.command, self.args = None, []
        return self

    def to_mcp_json(self) -> dict:
        """The entry shape Claude Code reads from .mcp.json / settings.json."""
        if self.transport == "http":
            return {"type": "http", "url": self.url}
        entry: dict = {"command": self.command, "args": list(self.args)}
        if self.env:
            entry["env"] = {k: f"${{{k}}}" for k in self.env}
        return entry


class AgentSpec(BaseModel):
    """A user-built agent. Validated against the catalog by catalog.validate_spec."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., description="URL-safe id, e.g. 'test-pilot'")
    name: str = Field(..., min_length=2, max_length=40)
    role: str = Field(..., min_length=4, max_length=160, description="One line: what it does")
    instructions: str = Field(default="", max_length=MAX_PROMPT_CHARS)
    phase: str = Field(default="custom", max_length=24)
    model_tier: ModelTier = ModelTier.BALANCED
    skills: list[str] = Field(default_factory=list, max_length=12)
    tools: list[str] = Field(default_factory=list, max_length=16)
    plugins: list[str] = Field(default_factory=list, max_length=8)
    mcp_servers: list[McpServer] = Field(default_factory=list, max_length=8)
    budget_usd: float = Field(default=0.25, ge=0.0, le=20.0)
    # Factory-floor appearance
    suit_color: str = "#A4D8FF"
    prop: Prop = Prop.WRENCH

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not SLUG_RE.match(v):
            raise ValueError("slug: lowercase letters, digits and -, starting with a letter (2-41 chars)")
        return v

    @field_validator("suit_color")
    @classmethod
    def _color(cls, v: str) -> str:
        if not HEX_RE.match(v):
            raise ValueError("suit_color must be a #RRGGBB hex colour")
        return v.upper()

    @field_validator("skills", "tools", "plugins")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))

    @model_validator(mode="after")
    def _unique_mcp(self) -> "AgentSpec":
        names = [m.name for m in self.mcp_servers]
        if len(names) != len(set(names)):
            raise ValueError("MCP server names must be unique within an agent")
        return self


__all__ = ["AgentSpec", "McpServer", "ModelTier", "Prop", "SLUG_RE"]
