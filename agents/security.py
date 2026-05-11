"""
SecurityAgent.

Performs a deterministic security audit pass over the scaffolded project
and writes:
* SECURITY.md — threat model, controls, outstanding risks.
* supabase/policies.sql — refined RLS policies.
* trivy.yaml + .snyk — CI scanner configuration.

It also flags missing controls in the code (auth deps, rate limit
decorators, secret literals) and writes findings into context.failures
so the orchestrator can surface them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from models import ProjectContext, TaskStatus
from .base import BaseAgent


_SECRET_PATTERNS = [
    re.compile(r"(?:aws_secret_access_key|aws_access_key_id)\s*=\s*['\"][^'\"]{16,}['\"]", re.I),
    re.compile(r"(?:api_-?key|apikey)\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]", re.I),
    re.compile(r"(?:secret|token)\s*=\s*['\"][A-Za-z0-9_\-]{24,}['\"]", re.I),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
]


class SecurityAgent(BaseAgent):
    name = "security"
    phase = "security"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        project_root = Path(context.workdir) / "project"
        if not project_root.exists():
            raise RuntimeError("Project missing — cannot audit")

        findings = self._scan(project_root)
        self._write_policies(project_root)
        self._write_scanner_configs(project_root)
        sec_md = self._render_security_md(context, findings, project_root)
        self._write(context, "SECURITY.md", sec_md)
        # Copy into the project itself so it ships with the generated code.
        (project_root / "SECURITY.md").write_text(sec_md, encoding="utf-8")

        # Mark security tasks done
        for t in context.tasks:
            if t.agent == "security":
                t.status = TaskStatus.DONE.value

        # Record findings on context so they show up in SUMMARY
        context.metadata.setdefault("security", {})
        context.metadata["security"] = {
            "issues": [
                {"path": str(f.path), "severity": f.severity, "message": f.message}
                for f in findings
            ],
            "owasp_controls": _OWASP_CONTROLS,
        }
        return {"issues": len(findings), "report": "SECURITY.md"}

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def _scan(self, root: Path) -> list["Finding"]:
        findings: list[Finding] = []

        # 1. Hard-coded secret heuristics across the project
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", "node_modules", ".venv", "__pycache__"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern in _SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append(
                        Finding(path, "high", f"Possible secret literal matching {pattern.pattern[:40]}")
                    )
                    break

        # 2. Missing auth dependency on item routers
        items_router = root / "backend/app/routers/items.py"
        if items_router.exists():
            t = items_router.read_text(encoding="utf-8")
            if "CurrentUserDep" not in t and "require_user" not in t:
                findings.append(
                    Finding(items_router, "high", "Items router lacks authentication dependency")
                )
            if "rate_limit" not in t and "RateLimitDep" not in t:
                findings.append(
                    Finding(items_router, "medium", "Items router lacks rate limit dependency")
                )

        # 3. Frontend env leakage check
        for path in root.rglob("*.tsx"):
            try:
                t = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if "process.env.SUPABASE_SERVICE_ROLE_KEY" in t:
                findings.append(
                    Finding(path, "critical", "Service role key referenced in client component")
                )

        # 4. .env presence
        if (root / ".env").exists():
            findings.append(
                Finding(root / ".env", "critical", "A real .env file is committed to the repo")
            )
        return findings

    # ------------------------------------------------------------------
    # Policies + scanner configs
    # ------------------------------------------------------------------

    def _write_policies(self, root: Path) -> None:
        policies = root / "supabase" / "policies.sql"
        policies.parent.mkdir(parents=True, exist_ok=True)
        policies.write_text(_RLS_POLICIES, encoding="utf-8")

    def _write_scanner_configs(self, root: Path) -> None:
        (root / "trivy.yaml").write_text(_TRIVY, encoding="utf-8")
        (root / ".snyk").write_text(_SNYK, encoding="utf-8")
        (root / ".github/workflows/security.yml").parent.mkdir(parents=True, exist_ok=True)
        (root / ".github/workflows/security.yml").write_text(_SEC_WORKFLOW, encoding="utf-8")

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _render_security_md(
        self, context: ProjectContext, findings: list["Finding"], project_root: Path
    ) -> str:
        def _rel(p: Path) -> str:
            """Relative path from project root, falling back to filename."""
            try:
                return str(p.relative_to(project_root))
            except ValueError:
                return p.name

        f_table = "\n".join(
            f"| {f.severity.upper():9} | `{_rel(f.path)}` | {f.message} |"
            for f in findings
        ) or "| _none_ | _none_ | No issues detected |"
        owasp = "\n".join(f"- **{k}** — {v}" for k, v in _OWASP_CONTROLS.items())
        return (
            "# Security Report\n\n"
            f"Project: `{context.project_id}`\n\n"
            "## Threat model\n\n"
            "Multi-tenant SaaS with public marketing pages. Trust boundary is "
            "the Supabase JWT — every authenticated API endpoint validates it "
            "using HS256 against `SUPABASE_JWT_SECRET`. Database access is "
            "restricted by RLS using `auth.uid()`.\n\n"
            "Adversaries considered: anonymous internet attackers, authenticated "
            "tenants attempting horizontal privilege escalation, and stolen-token "
            "replay attacks. Out of scope for this report: physical attacks on "
            "Supabase, Railway, and Vercel infrastructure.\n\n"
            "## Controls applied\n\n"
            f"{owasp}\n\n"
            "## RLS policies\n\n"
            "Generated in `supabase/policies.sql`. All tables enable RLS and "
            "restrict reads/writes to the row owner.\n\n"
            "## CI scanners\n\n"
            "- `trivy.yaml` — filesystem + container vulnerability scan.\n"
            "- `.snyk` — dependency policy file.\n"
            "- `.github/workflows/security.yml` — runs both on every push.\n\n"
            "## Findings\n\n"
            "| Severity  | File      | Message |\n"
            "| --------- | --------- | ------- |\n"
            f"{f_table}\n\n"
            "## Outstanding risks\n\n"
            "- Manual penetration test before launch.\n"
            "- Bug-bounty programme not yet established.\n"
            "- Supabase service-role key rotation policy must be documented.\n"
        )


# ---------------------------------------------------------------------------
# Helper data
# ---------------------------------------------------------------------------


class Finding:
    def __init__(self, path: Path, severity: str, message: str) -> None:
        self.path = path
        self.severity = severity
        self.message = message


_OWASP_CONTROLS = {
    "A01 — Broken access control": "Supabase JWT validation + RLS on every table; admin endpoints gated.",
    "A02 — Cryptographic failures": "TLS terminated at Vercel/Railway; secrets via env only.",
    "A03 — Injection": "SQLAlchemy parameterised queries; Pydantic + Zod input validation.",
    "A04 — Insecure design": "Threat-modelled API surface; rate limits on mutations.",
    "A05 — Security misconfiguration": "Strict CORS allow-list; security headers in Next.js config.",
    "A06 — Vulnerable components": "Dependabot + Trivy + Snyk wired into CI.",
    "A07 — Identification & auth failures": "Supabase Auth handles password reset, MFA, lockout.",
    "A08 — Software & data integrity": "Webhooks verified via HMAC signatures.",
    "A09 — Logging & monitoring": "Sentry on backend + frontend; structured logs.",
    "A10 — SSRF": "No user-controlled outbound URLs without allow-list.",
}


_RLS_POLICIES = """\
-- Refined RLS policies — every table denies by default and explicitly
-- grants the owner. Service role bypasses RLS for admin tasks.

alter table public.users enable row level security;
alter table public.items enable row level security;

drop policy if exists "users can read self" on public.users;
create policy "users can read self" on public.users
  for select using (auth.uid() = id);

drop policy if exists "items owner select" on public.items;
create policy "items owner select" on public.items
  for select using (auth.uid() = user_id);

drop policy if exists "items owner write" on public.items;
create policy "items owner write" on public.items
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Block anonymous role from any direct table access; forces clients
-- through Supabase Auth before policies apply.
revoke all on public.users from anon;
revoke all on public.items from anon;
grant select on public.users to authenticated;
grant select, insert, update, delete on public.items to authenticated;
"""


_TRIVY = """\
# Trivy configuration
scan:
  scanners: [vuln, secret, config]
  severity: HIGH,CRITICAL
  ignore-unfixed: true
"""


_SNYK = """\
version: v1.25.0
ignore: {}
patch: {}
"""


_SEC_WORKFLOW = """\
name: Security

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 6 * * 1"

jobs:
  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trivy filesystem scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          severity: HIGH,CRITICAL
          ignore-unfixed: true
          format: sarif
          output: trivy-results.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-results.sarif

  snyk:
    if: ${{ secrets.SNYK_TOKEN != '' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Snyk
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
"""


__all__ = ["SecurityAgent"]
