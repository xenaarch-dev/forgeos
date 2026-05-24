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

from models import ProjectContext, StackChoice, Task, TaskStatus
from .base import BaseAgent


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


class ArchitectAgent(BaseAgent):
    name = "architect"
    phase = "architect"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        # ---- Step 1: classify the idea & pick the stack -----------------
        stack = self._decide_stack(context)
        context.stack = stack
        self._write(context, "STACK.json", json.dumps(asdict(stack), indent=2))

        # ---- Step 2: produce SPEC.md & ARCH.md -------------------------
        spec_md, arch_md = self._produce_spec_and_arch(context, stack)
        context.spec = spec_md
        context.architecture = arch_md
        self._write(context, "SPEC.md", spec_md)
        self._write(context, "ARCH.md", arch_md)

        # ---- Step 3: produce TASKS.json --------------------------------
        tasks = self._produce_tasks(context, stack)
        context.tasks = tasks
        self._write(
            context,
            "TASKS.json",
            json.dumps([asdict(t) for t in tasks], indent=2),
        )

        # Mirror all key artefacts to .forgeos/ so the mission layer can read them.
        forgeos_dir = Path(context.workdir) / ".forgeos"
        forgeos_dir.mkdir(parents=True, exist_ok=True)
        (forgeos_dir / "SPEC.md").write_text(spec_md, encoding="utf-8")
        (forgeos_dir / "ARCH.md").write_text(arch_md, encoding="utf-8")
        (forgeos_dir / "STACK.json").write_text(json.dumps(asdict(stack), indent=2), encoding="utf-8")
        (forgeos_dir / "TASKS.json").write_text(
            json.dumps([asdict(t) for t in tasks], indent=2), encoding="utf-8"
        )
        # context.json is saved by BaseAgent.run() via context.save(); mirror it too.
        import shutil as _shutil
        ctx_src = Path(context.workdir) / "context.json"
        if ctx_src.exists():
            _shutil.copy2(ctx_src, forgeos_dir / "context.json")

        return {
            "stack": asdict(stack),
            "spec_path": "SPEC.md",
            "arch_path": "ARCH.md",
            "tasks_path": "TASKS.json",
            "task_count": len(tasks),
            "forgeos_dir": str(forgeos_dir),
        }

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
                system_extra=SYSTEM_PROMPT,
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
                system_extra=SYSTEM_PROMPT,
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

    def _produce_tasks(
        self, context: ProjectContext, stack: StackChoice
    ) -> list[Task]:
        # Deterministic baseline — guarantees a usable plan even if LLM fails.
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

        baseline = [
            scaffold, db, be_health, be_crud, be_billing,
            fe_shell, fe_dashboard, fe_pricing, tests, sec, deploy,
        ]

        # Conditional ML tasks
        if "ml_service" in stack.extras:
            ml = Task.new("ML: training script + inference endpoint + MLflow", "coder", "code", [be_health.id])
            baseline.append(ml)

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
                system_extra=SYSTEM_PROMPT,
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
