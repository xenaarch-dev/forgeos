"""
Hermes LLM client.

Routes completions through the Hermes Agent CLI (claude code-executor wrapper).
Falls back silently when the hermes binary is not installed -- the router
will pick the next provider in the chain (Ollama or Claude directly).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import os
from typing import Any

from .base import LLMClient, LLMError, LLMResponse


def _find_hermes_bin() -> str | None:
    found = shutil.which("hermes")
    if found:
        return found
    candidates = [
        os.path.expanduser("~/.local/bin/hermes"),
        os.path.expanduser("~/.hermes/hermes-agent/venv/bin/hermes"),
    ]
    for p in candidates:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


_HERMES_BIN: str | None = _find_hermes_bin()

_TOKEN_RE = re.compile(r"tokens?[:\s]+(\d+)", re.I)


class HermesClient(LLMClient):
    """LLM client that routes completions through the Hermes Agent CLI."""

    name = "hermes"
    default_model = "claude-code-via-hermes"

    def __init__(self, model: str | None = None) -> None:
        super().__init__(model or self.default_model)
        self._bin = _HERMES_BIN

    @classmethod
    def is_available(cls) -> bool:
        return _HERMES_BIN is not None

    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        *,
        stream: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        if not self._bin:
            raise LLMError("hermes CLI not installed")

        # Build a single prompt from messages
        prompt_parts: list[str] = []
        if system:
            prompt_parts.append(f"[SYSTEM]\n{system}\n")
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            prompt_parts.append(f"[{role.upper()}]\n{content}\n")
        prompt = "\n".join(prompt_parts)

        task_file = self._write_task(prompt)
        try:
            result = subprocess.run(
                [self._bin, "run-task", "--file", task_file, "--print"],
                capture_output=True,
                timeout=600,
            )
            if result.returncode != 0:
                err = result.stderr.decode("utf-8", errors="replace")[:300]
                raise LLMError(f"hermes run-task failed: {err}")

            output = result.stdout.decode("utf-8", errors="replace")
            stderr_text = result.stderr.decode("utf-8", errors="replace")
            tokens = self._parse_token_count(stderr_text)

            return LLMResponse(
                text=output,
                model=self.model,
                prompt_tokens=tokens,
                completion_tokens=0,
                cost_usd=0.0,
            )
        finally:
            try:
                os.unlink(task_file)
            except Exception:
                pass

    def _write_task(self, prompt: str) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
            encoding="utf-8",
            prefix="hermes_task_",
        ) as f:
            f.write(prompt)
            return f.name

    def _parse_token_count(self, stderr: str) -> int:
        m = _TOKEN_RE.search(stderr)
        return int(m.group(1)) if m else 0


__all__ = ["HermesClient"]
