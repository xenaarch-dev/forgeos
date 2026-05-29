"""Pydantic output model for ArchitectAgent structured outputs."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ArchitectOutput(BaseModel):
    """Validated, structured output from ArchitectAgent.

    Replaces freeform text parsing. All LLM-generated content is forced
    through this schema via Anthropic tool_use, guaranteeing required
    fields are present and correctly typed before downstream agents run.
    """

    model_config = ConfigDict(extra="ignore")

    product_name: str = Field(..., min_length=1, description="Short product name (e.g. HabitPro)")
    tech_stack: dict = Field(..., description="Frontend/backend/DB/auth/payments choices as key-value dict")
    spec_md: str = Field(..., min_length=200, description="Full SPEC.md content (problem, users, features, metrics)")
    arch_md: str = Field(..., min_length=200, description="Full ARCH.md content (stack justification, mermaid diagrams, API table)")
    api_routes: List[str] = Field(default_factory=list, description='API routes as "METHOD /path" strings, e.g. "GET /healthz"')
    task_titles: List[str] = Field(..., min_length=3, description="Ordered task titles for downstream agents (≥3 required)")
    estimated_phases: int = Field(..., ge=3, le=20, description="Number of build phases (3–20)")
    stack_frontend: str = Field(..., min_length=1, description="Frontend technology choice")
    stack_backend: str = Field(..., min_length=1, description="Backend technology choice")
    stack_database: str = Field(..., min_length=1, description="Database technology choice")
