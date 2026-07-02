"""
LLM router — ModelRouter v2 (2026-07-01).

Tiered routing strategy:
  Tier 1 (bulk/scaffolding, most agent turns):
    GLM-5.2 via OpenRouter — 62.1 SWE-bench Pro, MIT, ~$1.20/$4.10 MTok.
    Requires GLM_API_KEY. Replaces qwen2.5-coder:7b as the free-tier default.

  Tier 2 (quality default, unchanged):
    claude-sonnet-4-6 — fallback when GLM is unavailable.

  Tier 3 (frontier, gated):
    claude-fable-5 — ~80.3 SWE-bench Pro, $10/$50 MTok.
    Activates only when FORGEOS_FRONTIER_TIER=true AND task_type is in
    _FRONTIER_TASK_TYPES (architecture, security). Off by default so cost
    stays predictable. Use per-run, not globally, until there is revenue.

  Offline (explicit opt-in):
    Ollama qwen2.5-coder:7b — FORGEOS_OFFLINE_MODE=true only. No API key
    required. No longer the default; capability ceiling is too low for
    production-quality ForgeOS output.

Cost rationale (not quality-only — this matters for future-you):
  Pre-revenue budget is the binding constraint. GLM-5.2 closes 80% of the
  quality gap from qwen2.5-coder at roughly 6× less cost than frontier models.
  Fable-5 is reserved for the two gates where quality matters most and errors
  are most expensive: architecture planning and CSO security review.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_log = logging.getLogger(__name__)

from config import LLM
from .base import LLMClient, LLMError, LLMResponse
from .claude import ClaudeClient
from .glm import GLMClient
from .ollama import OllamaClient

if TYPE_CHECKING:
    from models import ProjectContext


# Model IDs
_SONNET = "claude-sonnet-4-6"
_HAIKU  = "claude-haiku-4-5"
_FABLE5 = "claude-fable-5"

# Task types that route to Tier 3 (Fable-5) when FORGEOS_FRONTIER_TIER=true.
_FRONTIER_TASK_TYPES: frozenset[str] = frozenset({"architecture", "security"})

# Provider chains — each is tried left-to-right; first available wins.
# Frontier: Fable-5 → GLM-5.2 → Sonnet (when FORGEOS_FRONTIER_TIER + frontier task)
# Hard: GLM-5.2 → Sonnet (architecture, planning)
# Medium: GLM-5.2 → Sonnet (review, security gates without frontier flag)
# Low: GLM-5.2 → Sonnet (scaffold, code)
# Offline: Ollama only (FORGEOS_OFFLINE_MODE=true)
_FRONTIER_STACK = ("fable5", "glm52", "claude-sonnet")
_HARD_STACK     = ("glm52", "claude-sonnet")
_MEDIUM_STACK   = ("glm52", "claude-sonnet")
_LOW_STACK      = ("glm52", "claude-sonnet")
_OFFLINE_STACK  = ("ollama",)


def route(task_complexity: str, task_type: str) -> LLMClient:
    """Return the preferred client for a task."""
    chain = _select_chain(task_complexity, task_type)
    for name in chain:
        if _is_available(name):
            return _build(name)
    raise LLMError(
        "No LLM provider available — set GLM_API_KEY (openrouter.ai) "
        "or ANTHROPIC_API_KEY, or use FORGEOS_OFFLINE_MODE=true for Ollama"
    )


def _select_chain(task_complexity: str, task_type: str) -> tuple[str, ...]:
    if LLM.offline_mode:
        return _OFFLINE_STACK
    if LLM.frontier_tier and task_type in _FRONTIER_TASK_TYPES:
        return _FRONTIER_STACK
    if task_complexity == "hard" or task_type in ("architecture", "planning"):
        return _HARD_STACK
    if task_complexity == "medium" or task_type in ("review", "security"):
        return _MEDIUM_STACK
    return _LOW_STACK


def _build(name: str) -> LLMClient:
    if name == "fable5":
        return ClaudeClient(model=_FABLE5)
    if name == "claude-sonnet":
        return ClaudeClient(model=_SONNET)
    if name in ("claude", "claude-haiku"):
        return ClaudeClient(model=_HAIKU)
    if name == "glm52":
        return GLMClient()
    if name == "ollama":
        return OllamaClient()
    raise ValueError(f"Unknown LLM provider: {name}")


def _is_available(client_name: str) -> bool:
    if client_name in ("claude", "claude-haiku", "claude-sonnet", "fable5"):
        return bool(LLM.anthropic_api_key)
    if client_name == "glm52":
        available = bool(LLM.glm_api_key)
        if not available:
            sys.stderr.write(
                "\n[router] WARNING: GLM-5.2 is the preferred provider but GLM_API_KEY "
                "is not set. Falling back to next provider in chain. "
                "Add to ~/.bashrc: export GLM_API_KEY='sk-or-v1-...' "
                "(get a key at openrouter.ai)\n"
            )
            sys.stderr.flush()
        return available
    if client_name == "ollama":
        return True
    return False


def complete(
    *,
    context: "ProjectContext | None" = None,
    user: str,
    system_extra: str = "",
    task_complexity: str = "medium",
    task_type: str = "code",
    purpose: str = "",
    stream: bool = True,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> LLMResponse:
    """Run a chat completion with automatic routing and ledger logging.

    Full project context (if any) is rendered into the system prompt so
    the model always reasons over the latest state.
    """
    chain = _select_chain(task_complexity, task_type)
    system = _build_system_prompt(context, system_extra)
    last_err: Exception | None = None

    for client_name in chain:
        if not _is_available(client_name):
            continue
        client = _build(client_name)
        try:
            resp = client.complete(
                messages=[{"role": "user", "content": user}],
                system=system,
                stream=stream,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if context is not None:
                context.record_tokens(
                    model=resp.model,
                    purpose=purpose or task_type,
                    prompt_tokens=resp.prompt_tokens,
                    completion_tokens=resp.completion_tokens,
                    cost_usd=resp.cost_usd,
                )
                context.save()
            return resp
        except LLMError as e:
            if client_name == "glm52":
                _log.warning(
                    "[router] GLM call failed — falling back to Sonnet. Error: %s", e
                )
            last_err = e
            continue
        except Exception as e:
            if client_name == "glm52":
                _log.warning(
                    "[router] GLM call failed — falling back to Sonnet. Error: %s", e
                )
            last_err = e
            continue

    if last_err:
        raise LLMError(f"All LLM providers failed: {last_err}") from last_err
    raise LLMError("No LLM provider was available")


def _build_system_prompt(context: "ProjectContext | None", extra: str) -> str:
    base = (
        "You are an agent in ForgeOS, an autonomous multi-agent product factory. "
        "You produce production-quality output without placeholders, TODOs, or "
        "stubs. You ground every decision in the project context."
    )
    blocks: list[str] = [base]
    if extra:
        blocks.append(extra.strip())
    if context is not None:
        snapshot = _safe_summary(context)
        blocks.append("PROJECT CONTEXT (JSON):\n" + json.dumps(snapshot, indent=2, default=str))
    return "\n\n".join(blocks)


def _safe_summary(ctx: "ProjectContext") -> dict[str, Any]:
    return {
        "project_id": ctx.project_id,
        "idea": ctx.idea,
        "current_phase": ctx.current_phase,
        "stack": ctx.summary().get("stack", {}),
        "spec_excerpt": (ctx.spec or "")[:1500],
        "architecture_excerpt": (ctx.architecture or "")[:1500],
        "task_count": len(ctx.tasks),
        "failures": ctx.failures[-3:],
    }


class ModelRouter:
    """Provider-agnostic model router backed by LiteLLM and models.yaml."""

    def __init__(self) -> None:
        import yaml  # local import — only needed when ModelRouter is instantiated
        config_path = Path(__file__).parent.parent / "config" / "models.yaml"
        self.config = yaml.safe_load(config_path.read_text())

    def get_model(self, stage: str) -> str:
        if LLM.frontier_tier:
            frontier = self.config.get("frontier", {})
            if stage in frontier:
                return frontier[stage]
        return self.config["stages"].get(stage, self.config["stages"]["default"])

    def complete(
        self,
        stage: str,
        messages: list,
        tools: list | None = None,
        **kwargs: Any,
    ) -> Any:
        from litellm import completion  # local import — optional dependency

        model = self.get_model(stage)
        primary_error: Exception | None = None
        try:
            return completion(model=model, messages=messages, tools=tools, **kwargs)
        except Exception as e:
            primary_error = e

        for fallback in self.config["fallback"]:
            if fallback != model:
                try:
                    return completion(
                        model=fallback, messages=messages, tools=tools, **kwargs
                    )
                except Exception:
                    continue
        raise primary_error  # type: ignore[misc]


router = ModelRouter()

__all__ = ["LLMClient", "LLMResponse", "ModelRouter", "route", "complete", "_build_system_prompt", "router"]
