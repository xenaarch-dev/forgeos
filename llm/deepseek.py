"""
DeepSeek client (via OpenRouter).

Uses the OpenAI-compatible chat completions endpoint that OpenRouter
exposes. Streams over SSE when `stream=True`. Falls back to the plain
DeepSeek API if `via='deepseek'` is selected at construction time.
"""

from __future__ import annotations

import json
from typing import Any

from config import LLM, required
from .base import LLMClient, LLMError, LLMResponse


class DeepSeekClient(LLMClient):
    name = "deepseek"
    default_model = "deepseek/deepseek-chat"

    def __init__(self, model: str | None = None, via: str = "openrouter") -> None:
        super().__init__(model or LLM.deepseek_model or self.default_model)
        self.via = via
        if via == "openrouter":
            self.api_base = LLM.openrouter_base_url
            self._key_env = "OPENROUTER_API_KEY"
            self._key = LLM.openrouter_api_key
        elif via == "deepseek":
            self.api_base = "https://api.deepseek.com/v1"
            self._key_env = "DEEPSEEK_API_KEY"
            self._key = ""
        else:
            raise ValueError(f"Unknown deepseek route: {via}")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {required(self._key_env, self._key)}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://forgeos.dev",
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
            choices = data.get("choices", []) or []
            text = ""
            if choices:
                text = choices[0].get("message", {}).get("content", "") or ""
            usage = data.get("usage", {}) or {}
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

        return self._retry(call, purpose="deepseek.complete")

    def _consume_stream(self, lines) -> LLMResponse:
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
            choice = (evt.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            token = delta.get("content")
            if token:
                text_parts.append(token)
                self._stderr(token)
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
            completion_tokens=completion_tokens or _approx_tokens(full_text),
            cost_usd=self._record_cost(prompt_tokens, completion_tokens),
            raw=last_event,
        )


def _approx_tokens(text: str) -> int:
    # Cheap heuristic when API doesn't return usage on stream completion.
    return max(1, len(text) // 4)


__all__ = ["DeepSeekClient"]
