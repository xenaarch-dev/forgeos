"""
The Agent Builder catalog: everything a custom agent can be given.

  Skills  — SKILL.md folders (the Anthropic skill format: YAML front matter
            with name + description, then Markdown instructions). Loaded from
            skills/ and .claude/skills/. Drop any SKILL.md folder from a GitHub
            skills repo into skills/ and it appears here, no code change.
  Tools   — the integrations in tools/ that already exist and work.
  MCP     — presets for MCP servers (the three in .claude/settings.json plus
            GitHub); a spec can also declare its own.
  Plugins — named bundles of skills + tools + MCP servers, applied together.

resolve() expands a spec's plugins into concrete skills/tools/MCP so the
runtime and the exporters see one flat list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from agent_builder.spec import AgentSpec, McpServer

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIRS: tuple[Path, ...] = (REPO_ROOT / "skills", REPO_ROOT / ".claude" / "skills")
MAX_SKILL_CHARS = 12_000


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    description: str
    body: str
    source: str  # repo-relative path of the SKILL.md

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description, "source": self.source}


_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Minimal YAML front matter reader: top-level `key: value` lines only."""
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t", "#")):
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, match.group(2)


def load_skill(path: Path) -> Skill | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _parse_front_matter(text)
    skill_id = path.parent.name
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", skill_id):
        return None
    return Skill(
        id=skill_id,
        name=meta.get("name", skill_id),
        description=meta.get("description", "").strip()[:500],
        body=body.strip()[:MAX_SKILL_CHARS],
        source=str(path.relative_to(REPO_ROOT)),
    )


@lru_cache(maxsize=1)
def skills() -> dict[str, Skill]:
    found: dict[str, Skill] = {}
    for root in SKILL_DIRS:
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            skill = load_skill(skill_md)
            if skill and skill.id not in found:
                found[skill.id] = skill
    return found


# ---------------------------------------------------------------------------
# Tools — only integrations that exist in tools/
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    description: str
    module: str
    env: tuple[str, ...] = ()

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description,
                "module": self.module, "env": list(self.env)}


TOOLS: dict[str, Tool] = {t.id: t for t in (
    Tool("workspace", "Workspace files", "Read the build context and write artifacts into the build workdir.", "forge_sdk.agent"),
    Tool("github", "GitHub", "Create repos, push code, branches and pull requests.", "tools.github", ("GITHUB_TOKEN",)),
    Tool("vercel", "Vercel", "Create projects and deploy frontends.", "tools.vercel", ("VERCEL_TOKEN",)),
    Tool("render", "Render", "Deploy and inspect backend services.", "tools.render", ("RENDER_API_KEY",)),
    Tool("supabase", "Supabase admin", "Service-role database and auth administration.", "tools.supabase_admin", ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")),
    Tool("sentry", "Sentry", "Read production errors for the self-healing loop.", "tools.sentry", ("SENTRY_DSN",)),
    Tool("uptime", "UptimeRobot", "Create and read uptime monitors.", "tools.uptimerobot", ("UPTIMEROBOT_API_KEY",)),
    Tool("http", "HTTP fetch", "Fetch public web pages and APIs.", "tools.http"),
    Tool("browser", "Browser agent", "Drive a headless browser for QA and research.", "tools.browser_agent"),
    Tool("media", "Media generation", "Generate images and video through fal.ai.", "tools.fal_client", ("FAL_KEY",)),
)}


# ---------------------------------------------------------------------------
# MCP presets
# ---------------------------------------------------------------------------


MCP_PRESETS: dict[str, McpServer] = {m.name: m for m in (
    McpServer(name="supabase", command="npx", args=["-y", "@supabase/mcp-server-supabase@latest"], env=["SUPABASE_ACCESS_TOKEN"]),
    McpServer(name="context7", command="npx", args=["-y", "@upstash/context7-mcp@latest"]),
    McpServer(name="playwright", command="npx", args=["@playwright/mcp@latest"]),
    McpServer(name="github", transport="http", url="https://api.githubcopilot.com/mcp/"),
)}


# ---------------------------------------------------------------------------
# Plugins — bundles
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Plugin:
    id: str
    name: str
    description: str
    skills: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    mcp: tuple[str, ...] = ()

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description,
                "skills": list(self.skills), "tools": list(self.tools), "mcp": list(self.mcp)}


PLUGINS: dict[str, Plugin] = {p.id: p for p in (
    Plugin("ship-kit", "Ship Kit", "Everything to push and deploy: GitHub, Vercel, Render.",
           tools=("github", "vercel", "render"), mcp=("github",)),
    Plugin("qa-kit", "QA Kit", "Write tests, drive the browser, review code.",
           skills=("test-writer", "code-reviewer"), tools=("browser",), mcp=("playwright",)),
    Plugin("research-kit", "Research Kit", "Study how existing products work and turn it into an original spec.",
           skills=("clean-room-analyst", "spec-writer"), tools=("http", "browser"), mcp=("context7",)),
    Plugin("india-stack", "India Stack", "INR, GST, DPDP and Indian Contract Act defaults.",
           skills=("india-compliance",), tools=("supabase",), mcp=("supabase",)),
    Plugin("ops-kit", "Ops Kit", "Watch production: errors, uptime, self-healing.",
           tools=("sentry", "uptime")),
)}


# ---------------------------------------------------------------------------
# Validation + resolution
# ---------------------------------------------------------------------------


def validate_spec(spec: AgentSpec) -> list[str]:
    """Every reference in a spec must exist in the catalog. Returns problems."""
    problems: list[str] = []
    known_skills = skills()
    problems += [f"unknown skill: {s}" for s in spec.skills if s not in known_skills]
    problems += [f"unknown tool: {t}" for t in spec.tools if t not in TOOLS]
    problems += [f"unknown plugin: {p}" for p in spec.plugins if p not in PLUGINS]
    for plugin_id in spec.plugins:
        plugin = PLUGINS.get(plugin_id)
        if plugin:
            problems += [f"plugin {plugin_id} needs missing skill: {s}"
                         for s in plugin.skills if s not in known_skills]
    return problems


@dataclass
class Resolved:
    skills: list[Skill] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)
    mcp_servers: list[McpServer] = field(default_factory=list)


def resolve(spec: AgentSpec) -> Resolved:
    """Flatten plugins into the spec's own selections, order-preserving."""
    skill_ids = list(spec.skills)
    tool_ids = list(spec.tools)
    mcp: dict[str, McpServer] = {m.name: m for m in spec.mcp_servers}
    for plugin_id in spec.plugins:
        plugin = PLUGINS.get(plugin_id)
        if not plugin:
            continue
        skill_ids += plugin.skills
        tool_ids += plugin.tools
        for name in plugin.mcp:
            mcp.setdefault(name, MCP_PRESETS[name])
    known = skills()
    return Resolved(
        skills=[known[s] for s in dict.fromkeys(skill_ids) if s in known],
        tools=[TOOLS[t] for t in dict.fromkeys(tool_ids) if t in TOOLS],
        mcp_servers=list(mcp.values()),
    )


def catalog_payload() -> dict:
    """The JSON the builder UI renders its pickers from."""
    return {
        "skills": [s.public() for s in skills().values()],
        "tools": [t.public() for t in TOOLS.values()],
        "mcp_presets": [{"name": m.name, **m.to_mcp_json()} for m in MCP_PRESETS.values()],
        "plugins": [p.public() for p in PLUGINS.values()],
        "model_tiers": ["fast", "balanced", "deep"],
        "props": ["wrench", "clipboard", "shield", "megaphone", "scroll", "magnifier", "rocket", "brain"],
    }


__all__ = [
    "MCP_PRESETS", "PLUGINS", "Plugin", "Resolved", "Skill", "TOOLS", "Tool",
    "catalog_payload", "load_skill", "resolve", "skills", "validate_spec",
]
