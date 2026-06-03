"""
ForgeOS — abstract base agent.

Every agent inherits from `BaseAgent` and implements `_execute(context)`.
The base class handles:
* status reporting (`AgentResult`)
* automatic context.json persistence after every run
* exception capture and conversion to `AgentResult.failed`
* helpers for LLM calls and artifact writes
"""

from __future__ import annotations

import abc
import json
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from llm.router import complete as llm_complete, _build_system_prompt
from models import AgentResult, AgentStatus, LLMError, LLMResponse, ProjectContext

_T = TypeVar("_T", bound=BaseModel)


class BaseAgent(abc.ABC):
    name: str = "base"
    phase: str = "base"

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, context: ProjectContext) -> AgentResult:
        result = AgentResult.started(self.name)
        context.current_phase = self.phase
        self._log(f"[{self.name}] starting (phase={self.phase})")
        try:
            output = self._execute(context) or {}
            result.finalize(AgentStatus.SUCCESS, output=output)
            self._log(f"[{self.name}] succeeded in {result.duration_seconds:.1f}s")
        except Exception as e:
            tb = traceback.format_exc()
            result.finalize(AgentStatus.FAILED, error=f"{type(e).__name__}: {e}")
            result.log.append(tb)
            self._log(f"[{self.name}] FAILED: {e}")
        finally:
            context.record_agent(result)
            context.save()
        return result

    @abc.abstractmethod
    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        """Subclasses implement the actual work here."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        try:
            sys.stderr.write(msg + "\n")
            sys.stderr.flush()
        except Exception:
            pass

    def _llm(
        self,
        context: ProjectContext,
        user_prompt: str,
        *,
        system_extra: str = "",
        task_complexity: str = "medium",
        task_type: str = "code",
        purpose: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.2,
        stream: bool = True,
    ) -> LLMResponse:
        return llm_complete(
            context=context,
            user=user_prompt,
            system_extra=system_extra,
            task_complexity=task_complexity,
            task_type=task_type,
            purpose=purpose or self.name,
            stream=stream,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _structured_llm(
        self,
        context: ProjectContext,
        user_prompt: str,
        output_model: Type[_T],
        *,
        system_extra: str = "",
        max_tokens: int = 4096,
    ) -> _T:
        """Call claude-sonnet-4-6 with tool_use to get a validated Pydantic output.

        Always uses ClaudeClient directly — bypasses Ollama since Ollama does
        not support the Anthropic tool_use protocol. Raises LLMError if
        ANTHROPIC_API_KEY is not set or Claude returns an unexpected response.
        """
        from llm.claude import ClaudeClient

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY not set — cannot use structured output")

        stage = self.__class__.__name__.lower().replace("agent", "").strip()
        client = ClaudeClient(model="claude-sonnet-4-6")
        system = _build_system_prompt(context, system_extra)
        result = client.complete_structured(
            messages=[{"role": "user", "content": user_prompt}],
            output_model=output_model,
            system=system,
            max_tokens=max_tokens,
            stage=stage,
        )
        context.record_tokens(
            model="claude-sonnet-4-6",
            purpose=f"{self.name}.structured",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
        )
        return result

    def _write(self, context: ProjectContext, relpath: str, content: str) -> Path:
        workdir = Path(context.workdir).resolve()
        path = (workdir / relpath).resolve()
        # Guard: never write outside the build's workdir.
        if not path.is_relative_to(workdir):
            raise ValueError(
                f"[{self.name}] _write blocked: '{relpath}' resolves outside workdir"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _read(self, context: ProjectContext, relpath: str) -> str:
        path = Path(context.workdir) / relpath
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _extract_block(self, text: str, fence: str) -> str:
        """Extract the contents of the first ```<fence> block."""
        pattern = rf"```{re.escape(fence)}\s*(.*?)```"
        m = re.search(pattern, text, flags=re.S | re.I)
        return m.group(1).strip() if m else ""

    def _extract_json_block(self, text: str) -> Any:
        block = self._extract_block(text, "json")
        if not block:
            # Fallback: first {...} or [...] in the text
            for opener, closer in (("{", "}"), ("[", "]")):
                start = text.find(opener)
                end = text.rfind(closer)
                if start != -1 and end != -1 and end > start:
                    block = text[start : end + 1]
                    break
        if not block:
            raise ValueError("No JSON block found in response")
        return json.loads(block)

    def _split_files(self, text: str) -> dict[str, str]:
        """Parse a multi-file response of the form:

        ```path/to/file.py
        <contents>
        ```
        """
        files: dict[str, str] = {}
        pattern = re.compile(r"```([^\n`]+)\n(.*?)```", re.S)
        for m in pattern.finditer(text):
            header = m.group(1).strip()
            content = m.group(2)
            if not header or " " in header.split(":", 1)[0]:
                continue
            # Skip pure language fences with no path-like header
            if "/" not in header and "." not in header:
                continue
            files[header] = content
        return files


__all__ = ["BaseAgent"]
