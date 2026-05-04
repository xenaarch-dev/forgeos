"""
Shared base class and types for all ForgeOS LLM clients.

Every client implements `complete(messages, system, stream, ...)` and
returns an `LLMResponse`. Streaming writes tokens to stderr in real time
when `stream=True`. Retries with exponential backoff are built-in.
"""

from __future__ import annotations

import abc
import json
import random
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from config import LLM, estimate_cost


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMError(RuntimeError):
    pass


class LLMClient(abc.ABC):
    """Abstract LLM client."""

    name: str = "base"
    default_model: str = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or self.default_model

    @abc.abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        *,
        stream: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Run a chat completion."""

    # ------------------------------------------------------------------
    # Helpers shared across clients
    # ------------------------------------------------------------------

    def _retry(
        self,
        fn: Callable[[], Any],
        purpose: str = "",
    ) -> Any:
        delay = LLM.retry_initial_delay
        last_err: Exception | None = None
        for attempt in range(1, LLM.max_retries + 1):
            try:
                return fn()
            except LLMError as e:
                last_err = e
                msg = str(e).lower()
                # Retry on rate-limit / transient classes only
                retryable = any(
                    s in msg
                    for s in (
                        "rate",
                        "timeout",
                        "temporarily",
                        "overloaded",
                        "503",
                        "502",
                        "429",
                        "504",
                    )
                )
                if not retryable or attempt == LLM.max_retries:
                    raise
                jitter = random.uniform(0, 0.5)
                sleep_for = delay + jitter
                self._stderr(
                    f"\n[{self.name}] {purpose or 'request'} failed "
                    f"(attempt {attempt}/{LLM.max_retries}): {e}. "
                    f"Retrying in {sleep_for:.1f}s\n"
                )
                time.sleep(sleep_for)
                delay *= 2
        if last_err:
            raise last_err
        raise LLMError("retry loop exited without success")

    def _stderr(self, text: str) -> None:
        try:
            sys.stderr.write(text)
            sys.stderr.flush()
        except Exception:
            pass

    def _http_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any] | None = None,
        method: str = "POST",
        stream: bool = False,
        timeout: float | None = None,
    ) -> Iterable[bytes] | bytes:
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout or LLM.request_timeout)
        except urllib.error.HTTPError as e:
            raw = b""
            try:
                raw = e.read()
            except Exception:
                pass
            raise LLMError(
                f"HTTP {e.code} from {self.name}: {raw.decode('utf-8', errors='ignore')[:500]}"
            ) from e
        except urllib.error.URLError as e:
            raise LLMError(f"Network error from {self.name}: {e.reason}") from e

        if stream:
            return self._iter_stream(resp)
        return resp.read()

    @staticmethod
    def _iter_stream(resp: Any) -> Iterable[bytes]:
        # Yield raw bytes line-by-line for SSE / NDJSON parsers downstream.
        while True:
            chunk = resp.readline()
            if not chunk:
                break
            yield chunk

    def _record_cost(
        self, prompt_tokens: int, completion_tokens: int
    ) -> float:
        return estimate_cost(self.model, prompt_tokens, completion_tokens)


__all__ = ["LLMClient", "LLMResponse", "LLMError"]
