"""
ArchitectAgent.

Receives the raw idea, produces:
* SPEC.md — full PRD
* ARCH.md — architecture decision record + diagrams + ERD + API map
* TASKS.json — atomic task list
* STACK.json — chosen stack
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from forge_sdk.agent import ForgeAgent
from models import ProjectContext, StackChoice, Task, TaskStatus
from models.outputs.architect_output import ArchitectOutput

_GBRAIN_TECHNICAL = (
    Path(__file__).resolve().parent.parent / "gbrain" / "patterns" / "technical.json"
)


SYSTEM_PROMPT = """\
You are the ArchitectAgent in ForgeOS. You receive a single English idea
and decide the technology stack and break the project into atomic tasks
that downstream agents (scaffold, coder, security, deploy) will implement
without further human input.

Stack-selection rules (pick the lightest option that still serves the idea):
- Simple CRUD SaaS → Next.js 14 + FastAPI + Supabase
- Real-time → add Upstash Kafka or Ably
- ML/AI → add Python ML service, FastAPI inference endpoint, modal.com or Replicate
- Data platform → add ClickHouse or TimescaleDB + dbt + Apache Superset
- Mobile → React Native + Expo + same FastAPI backend
- Enterprise multi-tenant → add SAML SSO, per-tenant DB isolation, usage metering
- CLI tool → Python + Typer + PyPI packaging

Always justify each stack choice in ARCH.md.
Keep the scope tight: only build features the idea explicitly demands.
Tasks must be atomic, ordered, and tagged with the correct downstream agent.
Valid task agents: "scaffold", "coder", "security", "deploy".
Valid phases: "scaffold", "code", "security", "deploy".
"""


def _bullets(text: str) -> str:
    if not text:
        return "- (none)"
    return "\n".join(
        f"- {line.strip()}"
        for line in str(text).splitlines()
        if line.strip()
    ) or "- (none)"


class ArchitectAgent(ForgeAgent):
    name = "architect"
    phase = "architect"
    capabilities = ["SPEC.md", "ARCH.md", "TASKS.json", "STACK.json"]
    requires = ["idea"]
    budget_usd = 0.0  # runs first — no prior spend to guard against

    def __init__(
        self,
        event_callback: Any = None,
        logger: Any = None,
        *,
        _gbrain_path: Path | None = None,
    ) -> None:
        super().__init__(event_callback=event_callback, logger=logger)
        self._gbrain_context = self._load_gbrain_patterns(
            _gbrain_path or _GBRAIN_TECHNICAL
        )

    # ------------------------------------------------------------------
    # GBrain — learned patterns from previous builds
    # ------------------------------------------------------------------

    @staticmethod
    def _load_gbrain_patterns(path: Path) -> str:
        """Read technical.json and return a formatted string for the system prompt.

        Returns empty string silently if the file is absent, empty, or malformed.
        """
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return ""
        patterns = data.get("patterns") or []
        if not patterns:
            return ""
        lines: list[str] = ["Learned patterns from previous builds:"]
        for i, p in enumerate(patterns, 1):
            lines.append(f"\n[{i}] {p.get('title', '')}")
            tags = p.get("tags") or []
            if tags:
                lines.append(f"Tags: {', '.join(tags)}")
            if p.get("when_to_use"):
                lines.append(f"When to use: {p['when_to_use']}")
            if p.get("pattern"):
                lines.append(f"Pattern: {p['pattern']}")
            if p.get("example"):
                lines.append(f"Example:\n```\n{p['example'].strip()}\n```")
        return "\n".join(lines)

    @property
    def _system_prompt(self) -> str:
        """Full system prompt: GBrain patterns (if any) prepended to SYSTEM_PROMPT."""
        if self._gbrain_context:
            return f"{self._gbrain_context}\n\n{SYSTEM_PROMPT}"
        return SYSTEM_PROMPT

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        # Step 1: deterministic stack classification (never uses LLM alone)
        stack = self._decide_stack(context)
        context.stack = stack

        # Step 2: produce validated ArchitectOutput via structured LLM or fallback
        output = self._produce_architect_output(context, stack)

        # Step 3: write all artifacts from the validated model
        context.spec = output.spec_md
        context.architecture = output.arch_md
        self._write(context, "STACK.json", json.dumps(asdict(stack), indent=2))
        self._write(context, "SPEC.md", output.spec_md)
        self._write(context, "ARCH.md", output.arch_md)

        # Step 4: produce full task objects (with IDs + dependencies) for TASKS.json
        tasks = self._produce_tasks(context, stack)
        context.tasks = tasks
        self._write(context, "TASKS.json", json.dumps([asdict(t) for t in tasks], indent=2))

        # Return ArchitectOutput fields + legacy keys (extra="ignore" lets tests parse cleanly)
        return {
            **output.model_dump(),
            "stack": asdict(stack),
            "spec_path": "SPEC.md",
            "arch_path": "ARCH.md",
            "tasks_path": "TASKS.json",
            "task_count": len(tasks),
        }

    # ------------------------------------------------------------------
    # Structured output production
    # ------------------------------------------------------------------

    def _produce_architect_output(
        self, context: ProjectContext, stack: StackChoice
    ) -> ArchitectOutput:
        """Try Claude structured output first; fall back to deterministic templates."""
        try:
            return self._produce_structured_architect_output(context, stack)
        except Exception as e:
            self._log(f"[architect] structured output unavailable ({e}), using fallback")
            return self._produce_legacy_architect_output(context, stack)

    def _produce_structured_architect_output(
        self, context: ProjectContext, stack: StackChoice
    ) -> ArchitectOutput:
        pm = context.metadata.get("pm_output", {})
        pm_block = ""
        if pm.get("spec_additions"):
            additions = "\n".join(f"  - {a}" for a in pm["spec_additions"])
            pm_block = (
                f"\nPM RESEARCH ADDITIONS (must be included in SPEC.md features):\n"
                f"{additions}\n"
            )
        prompt = (
            f"IDEA: {context.idea}\n\n"
            f"CHOSEN STACK:\n{json.dumps(asdict(stack), indent=2)}\n"
            f"{pm_block}\n"
            "Produce the full product architecture using the structured_output tool.\n\n"
            "SPEC.md requirements:\n"
            "- Problem statement (2+ sentences)\n"
            "- Target users (2+ bullet points)\n"
            "- Core features (numbered, at least 5)\n"
            "- Non-features / out-of-scope (2+ items)\n"
            "- Success metrics (3+ measurable KPIs)\n\n"
            "ARCH.md requirements:\n"
            "- Stack justification (explain every choice)\n"
            "- System diagram as ```mermaid graph TD``` block\n"
            "- Data model as ```mermaid erDiagram``` block\n"
            "- API surface table (| Method | Path | Purpose | Auth |)\n\n"
            "api_routes: list every route as 'METHOD /path' (e.g. 'GET /healthz').\n"
            "task_titles: ordered list of ≥5 atomic build tasks.\n"
            "estimated_phases: integer 3–20 based on idea complexity.\n"
            "product_name: short marketable name (2–4 words)."
        )
        return self._structured_llm(
            context,
            user_prompt=prompt,
            output_model=ArchitectOutput,
            system_extra=self._system_prompt,
            max_tokens=8192,
        )

    def _produce_legacy_architect_output(
        self, context: ProjectContext, stack: StackChoice
    ) -> ArchitectOutput:
        """Build ArchitectOutput from deterministic fallback templates (no LLM needed)."""
        spec_md, arch_md = self._produce_spec_and_arch(context, stack)
        baseline_tasks = self._baseline_tasks(stack)
        return ArchitectOutput(
            product_name=self._extract_product_name(context.idea),
            tech_stack=asdict(stack),
            spec_md=spec_md,
            arch_md=arch_md,
            api_routes=self._extract_api_routes(arch_md),
            task_titles=[t.title for t in baseline_tasks],
            estimated_phases=min(20, max(3, len(baseline_tasks))),
            stack_frontend=stack.frontend,
            stack_backend=stack.backend,
            stack_database=stack.database,
        )

    @staticmethod
    def _extract_product_name(idea: str) -> str:
        m = re.search(
            r'(?:build|create|make|develop)\s+(?:a|an)\s+(.+?)(?:\s+for\s|\s+that\s|\s+which\s|\s+using\s|$)',
            idea,
            re.I,
        )
        if m:
            raw = m.group(1).strip()
            return " ".join(w.capitalize() for w in raw.split()[:4])
        words = [w.capitalize() for w in idea.split() if len(w) > 2]
        return " ".join(words[:3]) if words else "Product"

    @staticmethod
    def _extract_api_routes(arch_md: str) -> list[str]:
        routes = []
        for line in arch_md.splitlines():
            m = re.match(r'\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*(/[^\s|]+)', line)
            if m:
                routes.append(f"{m.group(1)} {m.group(2).strip()}")
        return routes if routes else ["GET /healthz", "GET /api/items", "POST /api/items"]

    # ------------------------------------------------------------------
    # Stack selection
    # ------------------------------------------------------------------

    def _decide_stack(self, context: ProjectContext) -> StackChoice:
        idea = context.idea.lower()
        rules = {
            "ml": any(k in idea for k in ("ml", "ai ", "model", "predict", "llm", "neural", "vision", "nlp")),
            "realtime": any(k in idea for k in ("realtime", "real-time", "live", "streaming", "chat ")),
            "data": any(k in idea for k in ("analytics", "data platform", "data warehouse", "etl", "olap")),
            "mobile": any(k in idea for k in ("mobile app", "ios", "android", "react native")),
            "enterprise": any(k in idea for k in ("enterprise", "multi-tenant", "saml", "sso")),
            "cli": "cli" in idea or "command line" in idea or "terminal tool" in idea,
        }

        # Defaults — simple CRUD SaaS
        stack = StackChoice(
            frontend="Next.js 14 (App Router) + Tailwind + Shadcn/ui",
            backend="FastAPI",
            database="Supabase (Postgres)",
            cache="Upstash Redis",
            queue="Upstash Redis (Streams)",
            auth="Supabase Auth",
            payments="Lemon Squeezy",
            email="Resend",
            monitoring="Sentry + Uptime Robot",
            ci_cd="GitHub Actions",
            deployment="Railway (backend) + Vercel (frontend)",
        )

        if rules["realtime"]:
            stack.queue = "Upstash Kafka"
            stack.extras["realtime"] = "Ably"
        if rules["ml"]:
            stack.extras["ml_service"] = "FastAPI inference + MLflow + Great Expectations"
            stack.extras["gpu"] = "modal.com"
        if rules["data"]:
            stack.database = "Supabase (Postgres) + ClickHouse"
            stack.extras["transform"] = "dbt"
            stack.extras["bi"] = "Apache Superset"
        if rules["mobile"]:
            stack.frontend = "React Native + Expo"
        if rules["enterprise"]:
            stack.auth = "Supabase Auth + SAML SSO (WorkOS)"
            stack.extras["tenancy"] = "per-tenant Postgres schemas"
            stack.extras["metering"] = "Stripe metered billing"
        if rules["cli"]:
            stack.frontend = "Python Typer CLI"
            stack.backend = "Python (no server)"
            stack.deployment = "PyPI"
            stack.payments = "(none)"
            stack.auth = "(none)"

        # Optional refinement via LLM — falls back silently to deterministic picks
        try:
            resp = self._llm(
                context,
                user_prompt=(
                    "Refine the stack JSON for this product idea.\n\n"
                    f"IDEA: {context.idea}\n\n"
                    f"PROPOSED STACK:\n{json.dumps(asdict(stack), indent=2)}\n\n"
                    "Return ONLY a JSON object with the same keys, adjusting any "
                    "choices you think are wrong. Add `extras` keys for niche tech."
                ),
                system_extra=self._system_prompt,
                task_complexity="hard",
                task_type="architecture",
                purpose="architect.stack",
                max_tokens=2048,
            )
            data = self._extract_json_block(resp.text)
            extras = data.pop("extras", {}) if isinstance(data, dict) else {}
            for k, v in (data or {}).items():
                if hasattr(stack, k) and isinstance(v, str):
                    setattr(stack, k, v)
            if isinstance(extras, dict):
                stack.extras.update({k: str(v) for k, v in extras.items()})
        except Exception as e:
            self._log(f"[architect] LLM stack refinement skipped: {e}")
        return stack

    # ------------------------------------------------------------------
    # Spec + arch generation
    # ------------------------------------------------------------------

    def _produce_spec_and_arch(
        self, context: ProjectContext, stack: StackChoice
    ) -> tuple[str, str]:
        try:
            resp = self._llm(
                context,
                user_prompt=(
                    f"IDEA:\n{context.idea}\n\n"
                    f"STACK:\n{json.dumps(asdict(stack), indent=2)}\n\n"
                    "Produce two markdown documents. The first one MUST be "
                    "fenced as ```spec\n...\n```. The second one MUST be "
                    "fenced as ```arch\n...\n```.\n\n"
                    "SPEC.md must include: Problem, Target users, Core features (numbered), "
                    "Non-features (out of scope), Success metrics.\n\n"
                    "ARCH.md must include: Stack justification (explain every choice), "
                    "System diagram (a ```mermaid``` block, graph TD), Data model ERD "
                    "(another ```mermaid``` block, erDiagram), API surface map (table of "
                    "endpoints with method, path, purpose, auth)."
                ),
                system_extra=self._system_prompt,
                task_complexity="hard",
                task_type="architecture",
                purpose="architect.spec_arch",
                max_tokens=6000,
            )
            spec = self._extract_block(resp.text, "spec")
            arch = self._extract_block(resp.text, "arch")
            if spec and arch:
                return spec, arch
        except Exception as e:
            self._log(f"[architect] LLM spec/arch failed, falling back: {e}")

        return self._fallback_spec(context, stack), self._fallback_arch(context, stack)

    def _fallback_spec(self, context: ProjectContext, stack: StackChoice) -> str:
        return (
            f"# Product Specification\n\n"
            f"## Problem\n\n{context.idea}\n\n"
            "## Target users\n\n"
            "- Primary users derived from the idea statement.\n\n"
            "## Core features\n\n"
            "1. User authentication and onboarding.\n"
            "2. Core workflow described by the idea.\n"
            "3. Persistence of user data and audit trail.\n"
            "4. Subscription/billing if monetised.\n"
            "5. Observability dashboards for owner.\n\n"
            "## Non-features\n\n"
            "- Mobile native unless requested.\n"
            "- Multi-region deployment.\n\n"
            "## Success metrics\n\n"
            "- Activation rate within 7 days.\n"
            "- Weekly active users.\n"
            "- Subscription conversion.\n"
        )

    def _fallback_arch(self, context: ProjectContext, stack: StackChoice) -> str:
        s = stack
        rendered = (
            f"# Architecture Decision Record\n\n"
            f"## Idea\n\n> {context.idea}\n\n"
            "## Stack & justification\n\n"
            f"- **Frontend** — `{s.frontend}` — fastest path to production-ready UI.\n"
            f"- **Backend** — `{s.backend}` — async-friendly Python with strong typing.\n"
            f"- **Database** — `{s.database}` — managed Postgres with auth+storage.\n"
            f"- **Cache** — `{s.cache}` — serverless Redis, no infra to manage.\n"
            f"- **Queue** — `{s.queue}` — works for low-volume background jobs.\n"
            f"- **Auth** — `{s.auth}` — built-in JWT + RLS support.\n"
            f"- **Payments** — `{s.payments}` — covers global tax/MoR concerns.\n"
            f"- **Email** — `{s.email}` — modern transactional API.\n"
            f"- **Monitoring** — `{s.monitoring}` — error + uptime tracking.\n"
            f"- **CI/CD** — `{s.ci_cd}` — first-class GitHub integration.\n"
            f"- **Deployment** — `{s.deployment}` — splits stateful + edge layers correctly.\n\n"
            "## System diagram\n\n"
            "```mermaid\n"
            "graph TD\n"
            "  user([User]) --> fe[Next.js Frontend]\n"
            "  fe --> be[FastAPI Backend]\n"
            "  be --> db[(Supabase Postgres)]\n"
            "  be --> cache[(Upstash Redis)]\n"
            "  be --> queue[(Upstash Streams)]\n"
            "  be --> email[Resend]\n"
            "  be --> pay[Lemon Squeezy]\n"
            "  fe --> sentry[Sentry]\n"
            "  be --> sentry\n"
            "```\n\n"
            "## Data model (ERD)\n\n"
            "```mermaid\n"
            "erDiagram\n"
            "  USER ||--o{ WORKSPACE : owns\n"
            "  WORKSPACE ||--o{ ITEM : contains\n"
            "  USER {\n"
            "    uuid id PK\n"
            "    text email\n"
            "    timestamptz created_at\n"
            "  }\n"
            "  WORKSPACE {\n"
            "    uuid id PK\n"
            "    uuid owner_id FK\n"
            "    text name\n"
            "  }\n"
            "  ITEM {\n"
            "    uuid id PK\n"
            "    uuid workspace_id FK\n"
            "    jsonb data\n"
            "    timestamptz created_at\n"
            "  }\n"
            "```\n\n"
            "## API surface\n\n"
            "| Method | Path | Purpose | Auth |\n"
            "| ------ | ---- | ------- | ---- |\n"
            "| GET    | /healthz | liveness probe | public |\n"
            "| POST   | /api/auth/exchange | exchange Supabase JWT | public |\n"
            "| GET    | /api/items | list user items | required |\n"
            "| POST   | /api/items | create item | required |\n"
            "| PATCH  | /api/items/{id} | update item | required |\n"
            "| DELETE | /api/items/{id} | delete item | required |\n"
            "| POST   | /api/billing/webhook | LemonSqueezy webhook | signed |\n"
        )
        return rendered

    # ------------------------------------------------------------------
    # Task list
    # ------------------------------------------------------------------

    def _baseline_tasks(self, stack: StackChoice) -> list[Task]:
        """Deterministic task baseline — always ≥11 tasks, no LLM required."""
        scaffold = Task.new("Generate project skeleton + configs", "scaffold", "scaffold")
        db = Task.new("Apply Supabase schema + RLS placeholders", "scaffold", "scaffold", [scaffold.id])
        be_health = Task.new("Backend: healthz + auth exchange + base middleware", "coder", "code", [db.id])
        be_crud = Task.new("Backend: items CRUD endpoints with Pydantic models", "coder", "code", [be_health.id])
        be_billing = Task.new("Backend: LemonSqueezy webhook handler", "coder", "code", [be_health.id])
        fe_shell = Task.new("Frontend: app shell + auth flow", "coder", "code", [be_health.id])
        fe_dashboard = Task.new("Frontend: items dashboard + forms", "coder", "code", [fe_shell.id, be_crud.id])
        fe_pricing = Task.new("Frontend: pricing + checkout link", "coder", "code", [fe_shell.id, be_billing.id])
        tests = Task.new("Tests: backend pytest + frontend vitest (>=80%)", "coder", "code", [be_crud.id, fe_dashboard.id])
        sec = Task.new("Security: OWASP audit + RLS + rate limits", "security", "security", [tests.id])
        deploy = Task.new("Deploy: GitHub repo, Railway, Vercel, monitoring", "deploy", "deploy", [sec.id])
        tasks = [scaffold, db, be_health, be_crud, be_billing, fe_shell, fe_dashboard, fe_pricing, tests, sec, deploy]
        if "ml_service" in stack.extras:
            tasks.append(Task.new("ML: training script + inference endpoint + MLflow", "coder", "code", [be_health.id]))
        return tasks

    def _produce_tasks(
        self, context: ProjectContext, stack: StackChoice
    ) -> list[Task]:
        baseline = self._baseline_tasks(stack)

        # Optional LLM enrichment
        try:
            resp = self._llm(
                context,
                user_prompt=(
                    f"Given the IDEA:\n{context.idea}\n\nand STACK:\n"
                    f"{json.dumps(asdict(stack), indent=2)}\n\n"
                    "Return additional atomic tasks (max 6) as a JSON array. "
                    "Each item: {title, agent, phase, depends_on:[]}. "
                    "Valid agents: scaffold|coder|security|deploy. "
                    "Valid phases: scaffold|code|security|deploy."
                ),
                system_extra=self._system_prompt,
                task_complexity="medium",
                task_type="architecture",
                purpose="architect.tasks",
                max_tokens=1200,
            )
            extras_data = self._extract_json_block(resp.text)
            if isinstance(extras_data, list):
                for item in extras_data[:6]:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title") or "").strip()
                    agent = str(item.get("agent") or "coder").strip()
                    phase = str(item.get("phase") or "code").strip()
                    if not title:
                        continue
                    baseline.append(Task.new(title, agent, phase, []))
        except Exception as e:
            self._log(f"[architect] LLM task enrichment skipped: {e}")

        return baseline


__all__ = ["ArchitectAgent"]
