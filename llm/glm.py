"""
GLM-5.2 client via OpenRouter (OpenAI-compatible API).

Requires GLM_API_KEY (an OpenRouter API key — get one at openrouter.ai).
Model is controlled by GLM_MODEL env var; verify the exact slug against
https://openrouter.ai/models after adding the key — Zhipu models are listed
under "zhipuai/..." on OpenRouter.

Capability (June 2026): 62.1 SWE-bench Pro, 81.0 Terminal-Bench 2.1,
1M context, MIT license, 753B total / 40B active params.
Cost: ~$1.20/$4.10 per MTok input/output — ~6× cheaper than frontier models.
Self-hosting on RTX 4050 (6GB) is not feasible; use hosted API only.

This client replaces qwen2.5-coder:7b as Tier 1 (bulk/scaffolding) default.
qwen2.5-coder remains available via FORGEOS_OFFLINE_MODE=true only.
"""

from __future__ import annotations

import json
from typing import Any

from config import LLM
from .base import LLMClient, LLMError, LLMResponse


class GLMClient(LLMClient):
    name = "glm"
    # Default model slug on OpenRouter — verify at openrouter.ai/models.
    default_model = "zhipuai/glm-z1-32b"

    def __init__(self, model: str | None = None) -> None:
        super().__init__(model or LLM.glm_model or self.default_model)
        if not LLM.glm_api_key:
            raise LLMError(
                "GLM_API_KEY is not set. "
                "Add to ~/.bashrc: export GLM_API_KEY='sk-or-v1-...' "
                "Get a key at openrouter.ai (free tier available)."
            )
        self.api_base = LLM.glm_base_url

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {LLM.glm_api_key}",
            "Content-Type": "application/json",
            # OpenRouter routing headers (optional but recommended).
            "HTTP-Referer": "https://github.com/xenaarch-dev/forgeos",
            "X-Title": "ForgeOS",
        }

    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        *,
        stream: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        msgs: list[dict[str, str]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        def call() -> LLMResponse:
            url = f"{self.api_base.rstrip('/')}/chat/completions"
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
            if data.get("error"):
                raise LLMError(f"GLM error: {data['error']}")
            choices = data.get("choices") or []
            text = (choices[0].get("message", {}) if choices else {}).get("content", "") or ""
            usage = data.get("usage") or {}
            pt = int(usage.get("prompt_tokens", 0))
            ct = int(usage.get("completion_tokens", 0))
            return LLMResponse(
                text=text,
                model=self.model,
                prompt_tokens=pt,
                completion_tokens=ct,
                cost_usd=self._record_cost(pt, ct),
                raw=data,
            )

        return self._retry(call, purpose="glm.complete")

    def _consume_stream(self, lines) -> LLMResponse:
        """Parse OpenAI-compatible SSE stream (data: {...} lines)."""
        text_parts: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        last_event: dict[str, Any] = {}

        for raw_line in lines:
            if not raw_line:
                continue
            try:
                line = (
                    raw_line.decode("utf-8")
                    if isinstance(raw_line, (bytes, bytearray))
                    else raw_line
                )
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
            if evt.get("error"):
                raise LLMError(f"GLM stream error: {evt['error']}")
            choices = evt.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                token = delta.get("content")
                if token:
                    text_parts.append(token)
                    self._stderr(token)
            # Some OpenRouter models emit usage in the final chunk.
            usage = evt.get("usage") or {}
            if usage:
                prompt_tokens = int(usage.get("prompt_tokens", prompt_tokens))
                completion_tokens = int(usage.get("completion_tokens", completion_tokens))

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


__all__ = ["GLMClient"]
