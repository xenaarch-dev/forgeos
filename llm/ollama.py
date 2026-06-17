"""
Local Ollama client.

Talks to a running Ollama daemon (default http://localhost:11434) via its
native /api/chat endpoint. Streams NDJSON tokens to stderr in real time.
"""

from __future__ import annotations

import json
from typing import Any

from config import LLM
from .base import LLMClient, LLMError, LLMResponse


class OllamaClient(LLMClient):
    name = "ollama"
    default_model = "qwen2.5-coder:latest"

    def __init__(self, model: str | None = None) -> None:
        super().__init__(model or LLM.ollama_model or self.default_model)
        self.api_base = LLM.ollama_base_url

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

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
            "stream": bool(stream),
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        def call() -> LLMResponse:
            # TODO(ollama-swap): this is the localhost:11434 call site. When swapping
            # to a direct Claude API, replace OllamaClient here in llm/router.py's
            # _HARD_STACK/_MEDIUM_STACK/_LOW_STACK. See queue entry: ollama-api-swap.
            url = f"{self.api_base.rstrip('/')}/api/chat"
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
            text = (data.get("message") or {}).get("content", "") or ""
            pt = int(data.get("prompt_eval_count", 0))
            ct = int(data.get("eval_count", 0))
            return LLMResponse(
                text=text,
                model=self.model,
                prompt_tokens=pt,
                completion_tokens=ct,
                cost_usd=self._record_cost(pt, ct),
                raw=data,
            )

        return self._retry(call, purpose="ollama.complete")

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
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            last_event = evt
            if evt.get("error"):
                raise LLMError(f"Ollama error: {evt.get('error')}")
            msg = evt.get("message") or {}
            token = msg.get("content")
            if token:
                text_parts.append(token)
                self._stderr(token)
            if evt.get("done"):
                prompt_tokens = int(evt.get("prompt_eval_count", prompt_tokens))
                completion_tokens = int(evt.get("eval_count", completion_tokens))
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


__all__ = ["OllamaClient"]
