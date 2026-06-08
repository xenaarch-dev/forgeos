"""
DesignAgent — UI/UX specification and design-system generation.

Sits in the pipeline between ArchitectAgent and ScaffoldAgent:

    ArchitectAgent  →  DesignAgent  →  ScaffoldAgent

Consumes:
  context.spec          — PRD from ArchitectAgent
  context.architecture  — ARCH.md with API surface and stack
  context.stack         — chosen frontend framework

Produces:
  DESIGN.md             — component map, layout spec, page flows
  design-tokens.json    — colour palette, typography, spacing scale
  ACCESSIBILITY.md      — WCAG 2.1 AA checklist for every component
  context.metadata["design_output"]  — structured DesignOutput

Tool registry
-------------
Each tool entry is a dict with:
  name        — short identifier (matches the tool class / CLI name)
  description — what it does in the ForgeOS context
  requires    — env vars or binaries needed to activate it
  optional    — True if the agent degrades gracefully when unavailable

The tool registry is read by agent-organizer to decide which tools to
activate before running this agent in a live build.
"""

from __future__ import annotations

from typing import Any

from forge_sdk.agent import ForgeAgent
from models import ProjectContext


TOOLS: list[dict[str, Any]] = [
    {
        "name": "figma_api",
        "description": (
            "Reads design tokens and component specs from a Figma file via the "
            "REST API. Exports frames as SVG/PNG for the component map. "
            "Writes extracted tokens to design-tokens.json."
        ),
        "requires": ["FIGMA_ACCESS_TOKEN", "FIGMA_FILE_KEY"],
        "optional": True,
    },
    {
        "name": "style_dictionary",
        "description": (
            "Transforms design-tokens.json into platform-specific outputs: "
            "CSS custom properties, Tailwind config extension, and React Native "
            "StyleSheet constants. Requires Node 20+ with style-dictionary v4."
        ),
        "requires": ["node>=20"],
        "optional": True,
    },
    {
        "name": "chromatic_snapshot",
        "description": (
            "Runs Storybook stories through Chromatic to produce baseline "
            "visual snapshots. Used in CI to catch unintended UI regressions "
            "before each deploy gate."
        ),
        "requires": ["CHROMATIC_PROJECT_TOKEN", "node>=20"],
        "optional": True,
    },
    {
        "name": "axe_accessibility",
        "description": (
            "Runs axe-core on rendered component HTML to generate a WCAG 2.1 AA "
            "violation report. Each violation is written to ACCESSIBILITY.md with "
            "its impact level, WCAG criterion, and recommended fix."
        ),
        "requires": ["node>=20", "axe-cli"],
        "optional": True,
    },
    {
        "name": "shadcn_registry",
        "description": (
            "Queries the shadcn/ui component registry to resolve which primitives "
            "map to each component in the spec. Produces an install manifest "
            "(npx shadcn add <component>) and wiring notes for ScaffoldAgent."
        ),
        "requires": ["node>=20"],
        "optional": False,
    },
    {
        "name": "llm_design_critic",
        "description": (
            "Claude Sonnet structured-output call that reviews SPEC.md + ARCH.md "
            "and produces a scored design critique: information architecture, "
            "user-flow gaps, accessibility concerns, and component hierarchy. "
            "Output is merged into DESIGN.md and the design_output metadata key."
        ),
        "requires": ["ANTHROPIC_API_KEY"],
        "optional": False,
    },
]


class DesignAgent(ForgeAgent):
    """
    Generate the UI/UX specification, design tokens, and component map
    for the generated project.

    Pipeline position: ArchitectAgent → **DesignAgent** → ScaffoldAgent

    This agent is not yet implemented. When implemented it will:

    1. Parse SPEC.md and ARCH.md to extract all user-facing screens.
    2. If FIGMA_ACCESS_TOKEN + FIGMA_FILE_KEY are set, pull tokens from
       the linked Figma file; otherwise derive them from the stack's
       design-system defaults (Shadcn → slate palette, Inter typeface,
       4-point spacing grid).
    3. Run style-dictionary to emit Tailwind config and CSS vars.
    4. Use llm_design_critic (Claude Sonnet) to produce the component map
       and page flows written to DESIGN.md.
    5. Run axe-core on static HTML stubs to seed ACCESSIBILITY.md.
    6. Write design_output to context.metadata for downstream agents.

    Raises NotImplementedError until implementation is complete — the
    pipeline degrades gracefully (HermesOrchestrator catches the failure
    and marks this stage as degraded, continuing to ScaffoldAgent).
    """

    name = "design_agent"
    phase = "design"
    capabilities = [
        "DESIGN.md",            # component map, page flows, layout spec
        "design-tokens.json",   # colour / type / spacing primitives
        "ACCESSIBILITY.md",     # WCAG 2.1 AA checklist per component
        "design_output",        # context.metadata key with structured output
    ]
    requires = [
        "idea",
        "spec",         # context.spec — written by ArchitectAgent
        "architecture", # context.architecture — written by ArchitectAgent
        "stack",        # context.stack.frontend — determines design-system
    ]
    budget_usd = 0.15   # one Claude structured call + optional Figma API reads

    #: Tool registry — read by agent-organizer to decide activation order.
    tools: list[dict[str, Any]] = TOOLS

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        raise NotImplementedError(
            "DesignAgent._execute() is not yet implemented. "
            "Implement the steps described in the class docstring, "
            "then remove this raise."
        )


__all__ = ["DesignAgent", "TOOLS"]
