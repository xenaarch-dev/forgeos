"""
Anthropic Claude client.

Uses the Messages API (v1) over plain HTTPS so we don't take a hard
dependency on the Anthropic SDK. Supports streaming Server-Sent Events
and reports prompt/completion tokens.
"""

from __future__ import annotations

import json
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from config import LLM, required
from .base import LLMClient, LLMError, LLMResponse

_T = TypeVar("_T", bound=BaseModel)


class ClaudeClient(LLMClient):
    name = "claude"
    default_model = "claude-haiku-4-5"  # cheap fallback; override via ANTHROPIC_MODEL
    api_base = "https://api.anthropic.com/v1"
    api_version = "2023-06-01"

    def __init__(self, model: str | None = None) -> None:
        super().__init__(model or LLM.anthropic_model or self.default_model)

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": required("ANTHROPIC_API_KEY", LLM.anthropic_api_key),
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        *,
        stream: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        stage: str = "default",
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        if stream:
            payload["stream"] = True

        def call() -> LLMResponse:
            url = f"{self.api_base}/messages"
            if stream:
                stream_iter = self._http_json(
                    url=url,
                    headers=self._headers(),
                    payload=payload,
                    stream=True,
                )
                return self._consume_stream(stream_iter)  # type: ignore[arg-type]
            raw = self._http_json(
                url=url,
                headers=self._headers(),
                payload=payload,
                stream=False,
            )
            data = json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)
            text = "".join(
                blk.get("text", "")
                for blk in data.get("content", [])
                if blk.get("type") == "text"
            )
            usage = data.get("usage", {}) or {}
            pt = int(usage.get("input_tokens", 0))
            ct = int(usage.get("output_tokens", 0))
            return LLMResponse(
                text=text,
                model=self.model,
                prompt_tokens=pt,
                completion_tokens=ct,
                cost_usd=self._record_cost(pt, ct),
                raw=data,
            )

        return self._retry(call, purpose="claude.complete")

    # ------------------------------------------------------------------
    # Structured output via tool_use
    # ------------------------------------------------------------------

    def complete_structured(
        self,
        messages: list[dict[str, str]],
        output_model: Type[_T],
        system: str | None = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        stage: str = "default",
    ) -> _T:
        """Call the Messages API with tool_use to get a Pydantic-validated output.

        Uses model_router.get_model(stage) when a stage is provided, falling back
        to "claude-sonnet-4-6" if the router is unavailable.
        """
        # Lazy import avoids circular dependency: router.py imports ClaudeClient
        try:
            from llm.router import router as model_router
            model = model_router.get_model(stage)
        except Exception:
            model = "claude-sonnet-4-6"

        tools = [
            {
                "name": "structured_output",
                "description": "Return the structured agent output. Use this tool to respond.",
                "input_schema": output_model.model_json_schema(),
            }
        ]
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "tools": tools,
            "tool_choice": {"type": "tool", "name": "structured_output"},
        }
        if system:
            payload["system"] = system

        def call() -> _T:
            raw = self._http_json(
                url=f"{self.api_base}/messages",
                headers=self._headers(),
                payload=payload,
                stream=False,
            )
            data = json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)
            for block in data.get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == "structured_output":
                    return output_model(**block["input"])
            raise LLMError(
                f"No structured_output tool_use block in response. "
                f"stop_reason={data.get('stop_reason')} content={data.get('content', [])[:1]}"
            )

        return self._retry(call, purpose="claude.complete_structured")

    # ------------------------------------------------------------------
    # SSE consumption
    # ------------------------------------------------------------------

    def _consume_stream(self, lines) -> LLMResponse:
        text_parts: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        last_event: dict[str, Any] = {}

        for raw_line in lines:
            if not raw_line:
                continue
            try:
                line = raw_line.decode("utf-8") if isinstance(raw_line, (bytes, bytearray)) else raw_line
            except Exception:
                continue
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                evt = json.loads(data)
            except json.JSONDecodeError:
                continue
            last_event = evt
            etype = evt.get("type", "")
            if etype == "content_block_delta":
                delta = evt.get("delta", {}) or {}
                token = delta.get("text", "")
                if token:
                    text_parts.append(token)
                    self._stderr(token)
            elif etype == "message_start":
                usage = evt.get("message", {}).get("usage", {}) or {}
                prompt_tokens = int(usage.get("input_tokens", prompt_tokens))
            elif etype == "message_delta":
                usage = evt.get("usage", {}) or {}
                completion_tokens = int(usage.get("output_tokens", completion_tokens))
            elif etype == "error":
                err = evt.get("error", {})
                raise LLMError(
                    f"Claude stream error: {err.get('type')}: {err.get('message')}"
                )
        self._stderr("\n")
        full_text = "".join(text_parts)
        return LLMResponse(
            text=full_text,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=self._record_cost(prompt_tokens, completion_tokens),
            raw=last_event,
        )


__all__ = ["ClaudeClient"]
