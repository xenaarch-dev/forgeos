"""
ForgeOS — Core data models.

All inter-agent state is exchanged through `ProjectContext`, which is
serialized to `context.json` after each agent run. `AgentResult` captures
the output of a single agent invocation. `WikiNote` represents a knowledge
artefact written into the Obsidian vault by ForgeBrain.

These dataclasses are deliberately permissive — they accept arbitrary
metadata blobs from agents — but the canonical fields are typed.
"""

from __future__ import annotations

import abc
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable

from config import LLM, estimate_cost


# ---------------------------------------------------------------------------
# LLM types (canonical home; breaks the llm ↔ agents circular import)
# ---------------------------------------------------------------------------


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

    def _retry(self, fn: Callable[[], Any], purpose: str = "") -> Any:
        delay = LLM.retry_initial_delay
        last_err: Exception | None = None
        for attempt in range(1, LLM.max_retries + 1):
            try:
                return fn()
            except LLMError as e:
                last_err = e
                msg = str(e).lower()
                retryable = any(
                    s in msg
                    for s in ("rate", "timeout", "temporarily", "overloaded",
                               "503", "502", "429", "504")
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
        while True:
            chunk = resp.readline()
            if not chunk:
                break
            yield chunk

    def _record_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return estimate_cost(self.model, prompt_tokens, completion_tokens)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"
    SKIPPED = "skipped"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"


class Phase(str, Enum):
    ARCHITECT = "architect"
    SCAFFOLD = "scaffold"
    CODE = "code"
    SECURITY = "security"
    DEPLOY = "deploy"
    KNOWLEDGE = "knowledge"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


@dataclass
class Task:
    id: str
    title: str
    agent: str
    phase: str
    depends_on: list[str] = field(default_factory=list)
    status: str = TaskStatus.PENDING.value
    notes: str = ""
    artifacts: list[str] = field(default_factory=list)

    @classmethod
    def new(
        cls,
        title: str,
        agent: str,
        phase: str,
        depends_on: list[str] | None = None,
    ) -> "Task":
        return cls(
            id=_new_id("task"),
            title=title,
            agent=agent,
            phase=phase,
            depends_on=list(depends_on or []),
        )


@dataclass
class StackChoice:
    frontend: str = ""
    backend: str = ""
    database: str = ""
    cache: str = ""
    queue: str = ""
    auth: str = ""
    payments: str = ""
    email: str = ""
    monitoring: str = ""
    ci_cd: str = ""
    deployment: str = ""
    extras: dict[str, str] = field(default_factory=dict)


@dataclass
class TokenLedgerEntry:
    timestamp: str
    model: str
    purpose: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


@dataclass
class AgentResult:
    """The output of a single agent run."""

    agent: str
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    output: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    error: str | None = None
    retries: int = 0

    @classmethod
    def started(cls, agent: str) -> "AgentResult":
        now = _utc_now_iso()
        return cls(
            agent=agent,
            status=AgentStatus.RUNNING.value,
            started_at=now,
            finished_at=now,
            duration_seconds=0.0,
        )

    def finalize(
        self,
        status: AgentStatus,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> "AgentResult":
        self.finished_at = _utc_now_iso()
        try:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.finished_at)
            self.duration_seconds = max(0.0, (end - start).total_seconds())
        except Exception:
            self.duration_seconds = 0.0
        self.status = status.value
        if output:
            self.output.update(output)
        if error:
            self.error = error
        return self


@dataclass
class WikiNote:
    """A knowledge artefact written into the Obsidian vault."""

    title: str
    pattern: str
    when_to_use: str
    example: str
    related_patterns: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_project: str = ""
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def slug(self) -> str:
        s = "".join(c.lower() if c.isalnum() else "-" for c in self.title)
        while "--" in s:
            s = s.replace("--", "-")
        return s.strip("-") or _new_id("note")

    def to_markdown(self) -> str:
        related = "\n".join(f"- [[{r}]]" for r in self.related_patterns) or "_None_"
        tags = " ".join(f"#{t}" for t in self.tags) if self.tags else ""
        return (
            "---\n"
            f"title: {self.title}\n"
            f"created: {self.created_at}\n"
            f"updated: {self.updated_at}\n"
            f"source_project: {self.source_project}\n"
            f"tags: [{', '.join(self.tags)}]\n"
            "---\n\n"
            f"# {self.title}\n\n"
            f"{tags}\n\n"
            "## Pattern\n\n"
            f"{self.pattern}\n\n"
            "## When to use\n\n"
            f"{self.when_to_use}\n\n"
            "## Example\n\n"
            f"{self.example}\n\n"
            "## Related patterns\n\n"
            f"{related}\n"
        )


# ---------------------------------------------------------------------------
# Project context
# ---------------------------------------------------------------------------


@dataclass
class ProjectContext:
    """The single source of truth shared between agents."""

    project_id: str
    idea: str
    workdir: str
    started_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    # Agent outputs
    spec: str = ""
    architecture: str = ""
    stack: StackChoice = field(default_factory=StackChoice)
    tasks: list[Task] = field(default_factory=list)

    # Phase results
    agent_results: list[AgentResult] = field(default_factory=list)
    current_phase: str = Phase.ARCHITECT.value

    # Deployment information
    repo_url: str = ""
    backend_url: str = ""
    frontend_url: str = ""
    monitoring_urls: dict[str, str] = field(default_factory=dict)

    # Bookkeeping
    token_ledger: list[TokenLedgerEntry] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def new(cls, idea: str, workdir: str | os.PathLike[str]) -> "ProjectContext":
        wd = str(Path(workdir).expanduser().resolve())
        Path(wd).mkdir(parents=True, exist_ok=True)
        return cls(
            project_id=_new_id("proj"),
            idea=idea.strip(),
            workdir=wd,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def context_path(self) -> Path:
        return Path(self.workdir) / "context.json"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def save(self) -> Path:
        self.updated_at = _utc_now_iso()
        path = self.context_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        tmp.replace(path)
        return path

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "ProjectContext":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"No context found at {p}")
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)

        stack_data = data.pop("stack", {}) or {}
        tasks_data = data.pop("tasks", []) or []
        agent_results_data = data.pop("agent_results", []) or []
        ledger_data = data.pop("token_ledger", []) or []

        known_fields = {f.name for f in ProjectContext.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        data = {k: v for k, v in data.items() if k in known_fields}
        ctx = cls(**data)
        ctx.stack = StackChoice(**{k: v for k, v in stack_data.items() if v is not None and hasattr(StackChoice, k)})
        ctx.tasks = []
        for t in tasks_data:
            try:
                ctx.tasks.append(Task(**t))
            except TypeError:
                pass
        ctx.agent_results = []
        for a in agent_results_data:
            try:
                ctx.agent_results.append(AgentResult(**a))
            except TypeError:
                pass
        ctx.token_ledger = []
        for e in ledger_data:
            try:
                ctx.token_ledger.append(TokenLedgerEntry(**e))
            except TypeError:
                pass
        return ctx

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def record_agent(self, result: AgentResult) -> None:
        self.agent_results.append(result)
        if result.status == AgentStatus.FAILED.value:
            self.failures.append(
                {
                    "agent": result.agent,
                    "error": result.error,
                    "at": result.finished_at,
                }
            )

    def record_tokens(
        self,
        model: str,
        purpose: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> None:
        self.token_ledger.append(
            TokenLedgerEntry(
                timestamp=_utc_now_iso(),
                model=model,
                purpose=purpose,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                cost_usd=float(cost_usd),
            )
        )

    def total_cost(self) -> float:
        return round(sum(e.cost_usd for e in self.token_ledger), 4)

    def total_tokens(self) -> int:
        return sum(e.prompt_tokens + e.completion_tokens for e in self.token_ledger)

    def get_artifact_path(self, name: str) -> Path:
        return Path(self.workdir) / name

    def write_artifact(self, name: str, content: str) -> Path:
        path = self.get_artifact_path(name)
        workdir_resolved = Path(self.workdir).resolve()
        if not path.resolve().is_relative_to(workdir_resolved):
            raise ValueError(f"Artifact path '{name}' escapes workdir — write denied")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def summary(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "idea": self.idea,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "current_phase": self.current_phase,
            "stack": asdict(self.stack),
            "repo_url": self.repo_url,
            "backend_url": self.backend_url,
            "frontend_url": self.frontend_url,
            "monitoring_urls": self.monitoring_urls,
            "tokens": self.total_tokens(),
            "cost_usd": self.total_cost(),
            "failures": self.failures,
        }


# ---------------------------------------------------------------------------
# GStack / Mission models
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    gate: str
    passed: bool
    score: float
    feedback: str
    timestamp: str = field(default_factory=_utc_now_iso)


@dataclass
class ValidationAssertion:
    description: str
    category: str = "functional"


@dataclass
class ValidationContract:
    project_id: str
    assertions: list[ValidationAssertion]
    acceptance_threshold: float = 0.90
    created_at: str = field(default_factory=_utc_now_iso)


@dataclass
class MissionHandoff:
    agent: str
    feature: str
    completed: list[str]
    skipped: list[str]
    issues: list[str]
    commands_run: list[str]
    next_feature: str
    timestamp: str = field(default_factory=_utc_now_iso)


__all__ = [
    "AgentResult",
    "AgentStatus",
    "GateResult",
    "LLMClient",
    "LLMError",
    "LLMResponse",
    "MissionHandoff",
    "Phase",
    "ProjectContext",
    "StackChoice",
    "Task",
    "TaskStatus",
    "TokenLedgerEntry",
    "ValidationAssertion",
    "ValidationContract",
    "WikiNote",
]
