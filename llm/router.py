"""
LLM router.

Chooses the right model for a given task based on complexity and type.
Also exposes a `complete()` convenience that automatically threads the
full ProjectContext as system context, logs token usage, and falls back
gracefully if the preferred provider is unavailable.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from config import LLM
from .base import LLMClient, LLMError, LLMResponse
from .claude import ClaudeClient
from .deepseek import DeepSeekClient
from .ollama import OllamaClient

if TYPE_CHECKING:
    from models import ProjectContext


# Task complexity / type → client preference order.
# We always try the primary client first, then the fallbacks.
_HARD_STACK = ("ollama", "claude")
_MEDIUM_STACK = ("ollama", "claude")
_LOW_STACK = ("ollama", "claude")


def route(task_complexity: str, task_type: str) -> LLMClient:
    """Return the preferred client for a task."""
    chain = _select_chain(task_complexity, task_type)
    primary = chain[0]
    return _build(primary)


def _select_chain(task_complexity: str, task_type: str) -> tuple[str, ...]:
    if task_complexity == "hard" or task_type == "architecture":
        return _HARD_STACK
    if task_complexity == "medium" or task_type in ("review", "security"):
        return _MEDIUM_STACK
    return _LOW_STACK


def _build(name: str) -> LLMClient:
    if name == "claude":
        return ClaudeClient()
    if name == "deepseek":
        return DeepSeekClient(via="openrouter")
    if name == "ollama":
        return OllamaClient()
    raise ValueError(f"Unknown LLM provider: {name}")


def _is_available(client_name: str) -> bool:
    if client_name == "claude":
        return bool(LLM.anthropic_api_key)
    if client_name == "deepseek":
        return bool(LLM.openrouter_api_key)
    if client_name == "ollama":
        # Always assume local Ollama is reachable; a runtime error will
        # demote it on actual failure.
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

    The full project context (if any) is rendered into the system prompt
    so the model always reasons over the latest state.
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
            last_err = e
            continue
        except Exception as e:  # network/key/etc
            last_err = e
            continue
    if last_err:
        raise LLMError(f"All LLM providers failed: {last_err}") from last_err
    raise LLMError("No LLM provider was available")


def _build_system_prompt(
    context: "ProjectContext | None", extra: str
) -> str:
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
    # Avoid stuffing huge agent_results / token_ledger into the system prompt.
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


__all__ = ["LLMClient", "LLMResponse", "route", "complete"]
