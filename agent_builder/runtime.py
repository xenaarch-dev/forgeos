"""
Turn an AgentSpec into something that runs.

  build_agent_class(spec) -> a ForgeAgent subclass. It runs through the normal
      ForgeAgent.run() path, so it gets GBrain logging, budget enforcement and
      SSE events for free, and HermesOrchestrator / the mesh can run it like
      any built-in agent.
  export_bundle(spec) -> the same agent for Claude Code: a subagent file for
      .claude/agents/ plus the .mcp.json entries its MCP servers need. This is
      how an agent gets real MCP and tool use: Claude Code runs the servers on
      the founder's machine. ForgeOS itself never launches an MCP command.

Imports of the agent stack are local to this module so `agent_builder.spec`
and `agent_builder.catalog` stay cheap for the API's validation path, and so
nothing here is pulled in eagerly by agents/__init__.py (circular import rule).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from agent_builder.catalog import Resolved, resolve
from agent_builder.spec import AgentSpec

if TYPE_CHECKING:  # pragma: no cover
    from forge_sdk.agent import ForgeAgent

#: ProjectContext.metadata key a caller sets to give the agent its task.
TASK_KEY = "custom_agent_task"


def compose_system_prompt(spec: AgentSpec, resolved: Resolved | None = None) -> str:
    """The agent's standing instructions: role, the founder's text, skills, tools."""
    resolved = resolved or resolve(spec)
    parts = [
        f"You are {spec.name}, a ForgeOS agent. Your job: {spec.role}",
    ]
    if spec.instructions.strip():
        parts.append("## Instructions from the founder\n" + spec.instructions.strip())
    for skill in resolved.skills:
        parts.append(f"## Skill: {skill.name}\n{skill.body}")
    if resolved.tools:
        lines = []
        for tool in resolved.tools:
            ready = all(os.getenv(k) for k in tool.env)
            state = "available" if ready else f"not configured (needs {', '.join(tool.env)})"
            lines.append(f"- {tool.name}: {tool.description} [{state}]")
        parts.append(
            "## Tools assigned to you\n"
            "Plan around these. When one is not configured, say what you would do "
            "with it instead of pretending it ran.\n" + "\n".join(lines)
        )
    parts.append(
        "## Output\nReturn Markdown. Lead with the result, then the details. "
        "Never claim an action happened unless you did it."
    )
    return "\n\n".join(parts)


def build_agent_class(spec: AgentSpec) -> "type[ForgeAgent]":
    from forge_sdk.agent import ForgeAgent  # local: see module docstring

    resolved = resolve(spec)
    system_prompt = compose_system_prompt(spec, resolved)
    artifact = f"agents/{spec.slug}/OUTPUT.md"

    def _execute(self, context) -> dict[str, Any]:  # noqa: ANN001 - ForgeAgent hook
        task = str(context.metadata.get(TASK_KEY) or context.idea or "").strip()
        if not task:
            raise ValueError(f"{spec.slug}: no task given")
        resp = self._llm(
            context,
            task,
            system_extra=system_prompt,
            task_complexity=spec.model_tier.task_complexity,
            task_type="general",
            purpose=spec.slug,
            stream=False,
        )
        self._write(context, artifact, resp.text)
        self._emit("artifact_ready", {
            "agent": spec.slug,
            "artifact_type": "markdown",
            "title": f"{spec.name} output",
            "preview": resp.text[:280],
            "workdir_path": artifact,
        })
        return {"artifact": artifact, "chars": len(resp.text), "model": resp.model}

    class_name = "".join(part.capitalize() for part in spec.slug.split("-")) + "Agent"
    return type(class_name, (ForgeAgent,), {
        "name": spec.slug,
        "phase": spec.phase,
        "capabilities": [artifact],
        "requires": ["idea"],
        "budget_usd": spec.budget_usd,
        "tools": [t.id for t in resolved.tools],
        "spec": spec,
        "_execute": _execute,
        "__module__": __name__,
    })


def to_claude_subagent(spec: AgentSpec) -> str:
    """A .claude/agents/<slug>.md file: front matter + the composed prompt."""
    description = spec.role.replace("\n", " ").replace('"', "'")
    model = {"fast": "haiku", "balanced": "sonnet", "deep": "opus"}[spec.model_tier.value]
    body = compose_system_prompt(spec)
    resolved = resolve(spec)
    if resolved.mcp_servers:
        names = ", ".join(m.name for m in resolved.mcp_servers)
        body += f"\n\n## MCP servers\nUse these MCP servers when they help: {names}."
    return f'---\nname: {spec.slug}\ndescription: "{description}"\nmodel: {model}\n---\n\n{body}\n'


def to_mcp_json(spec: AgentSpec) -> dict:
    """The {"mcpServers": {...}} block for the project's .mcp.json."""
    return {"mcpServers": {m.name: m.to_mcp_json() for m in resolve(spec).mcp_servers}}


def export_bundle(spec: AgentSpec) -> dict:
    return {
        "files": {
            f".claude/agents/{spec.slug}.md": to_claude_subagent(spec),
        },
        "mcp": to_mcp_json(spec),
        "spec": spec.model_dump(mode="json"),
    }


__all__ = [
    "TASK_KEY", "build_agent_class", "compose_system_prompt", "export_bundle",
    "to_claude_subagent", "to_mcp_json",
]
