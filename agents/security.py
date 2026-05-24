"""
SecurityAgent.

Performs a real security audit over the scaffolded project and produces:
* SecurityReport -- critical/warnings/passed lists (gates pipeline if critical non-empty)
* SECURITY.md -- human-readable threat model and findings
* supabase/policies.sql -- refined RLS policies
* trivy.yaml + .snyk -- CI scanner configuration

Gate: pipeline blocks if SecurityReport.critical is non-empty.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from models import PipelineBlockedError, ProjectContext, SecurityReport, TaskStatus
from .base import BaseAgent


_HARDCODED_SECRET = [
    re.compile(
        r'(?:password|secret|api[_-]?key|token)\s*=\s*["\'][A-Za-z0-9_\-\/\+\.]{8,}["\']'
        , re.I,
    ),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
]

_SAFE_PATTERNS = [
    re.compile(r"os\.environ"),
    re.compile(r"os\.getenv"),
    re.compile(r"process\.env"),
    re.compile(r"settings\."),
    re.compile(r"getenv"),
    re.compile(r"\$\{"),
]

_RAW_SQL_FSTRING = re.compile(
    r'f["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\s',
    re.I,
)

_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".next", "dist", "build"}

_OWASP_CONTROLS = {
    "A01 - Broken access control": "Supabase JWT validation + RLS on every table.",
    "A02 - Cryptographic failures": "TLS terminated at Vercel/Render; secrets via env only.",
    "A03 - Injection": "SQLAlchemy parameterised queries; Pydantic + Zod input validation.",
    "A04 - Insecure design": "Threat-modelled API surface; rate limits on mutations.",
    "A05 - Security misconfiguration": "Strict CORS allow-list; security headers in Next.js.",
    "A06 - Vulnerable components": "Dependabot + Trivy + Snyk wired into CI.",
    "A07 - Identification & auth failures": "Supabase Auth handles password reset, MFA, lockout.",
    "A08 - Software & data integrity": "Webhooks verified via HMAC signatures.",
    "A09 - Logging & monitoring": "Sentry on backend + frontend; structured logs.",
    "A10 - SSRF": "No user-controlled outbound URLs without allow-list.",
}

_RLS_POLICIES = """\
-- Refined RLS policies
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

revoke all on public.users from anon;
revoke all on public.items from anon;
grant select on public.users to authenticated;
grant select, insert, update, delete on public.items to authenticated;
"""

_TRIVY = """\
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
"""


class SecurityAgent(BaseAgent):
    name = "security"
    phase = "security"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        project_root = Path(context.workdir) / "project"
        if not project_root.exists():
            raise RuntimeError("Project missing -- cannot audit")

        report = self._run_all_checks(project_root, context)

        sec_md = self._render_security_md(context, report, project_root)
        self._write(context, "SECURITY.md", sec_md)
        (project_root / "SECURITY.md").write_text(sec_md, encoding="utf-8")

        self._write_policies(project_root)
        self._write_scanner_configs(project_root)

        for t in context.tasks:
            if t.agent == "security":
                t.status = TaskStatus.DONE.value

        context.metadata["security_report"] = {
            "critical": report.critical,
            "warnings": report.warnings,
            "passed": report.passed,
        }

        if report.critical:
            self._log(
                f"[security] BLOCKED -- {len(report.critical)} critical finding(s):\n"
                + "\n".join(f"  CRITICAL: {c}" for c in report.critical)
            )
            raise PipelineBlockedError(
                f"SecurityAgent found {len(report.critical)} critical issue(s). "
                "Fix them before deploying.\n" + "\n".join(report.critical)
            )

        return {
            "critical": len(report.critical),
            "warnings": len(report.warnings),
            "passed": len(report.passed),
            "report": "SECURITY.md",
        }

    def _run_all_checks(
        self, project_root: Path, context: ProjectContext
    ) -> SecurityReport:
        report = SecurityReport()
        self._check_hardcoded_secrets(project_root, report)
        self._check_unauth_routes(project_root, report)
        self._check_sql_injection(project_root, report)
        self._check_env_hygiene(project_root, report)
        self._check_frontend_key_leak(project_root, report)
        return report

    def _check_hardcoded_secrets(self, project_root: Path, report: SecurityReport) -> None:
        exts = [".py", ".ts", ".tsx", ".js"]
        files = [p for ext in exts for p in project_root.rglob(f"*{ext}")]
        found = False
        for path in files:
            if any(d in _SKIP_DIRS for d in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern in _HARDCODED_SECRET:
                for match in pattern.finditer(text):
                    surrounding = text[max(0, match.start() - 60): match.end() + 60]
                    if any(safe.search(surrounding) for safe in _SAFE_PATTERNS):
                        continue
                    line = text[: match.start()].count("\n") + 1
                    rel = path.relative_to(project_root)
                    report.critical.append(f"Hardcoded secret in {rel}:{line}")
                    found = True
                    break
        if not found:
            report.passed.append("No hardcoded secrets in source files")

    def _check_unauth_routes(self, project_root: Path, report: SecurityReport) -> None:
        router_files = (
            list(project_root.rglob("routers/*.py"))
            + list(project_root.rglob("routes/*.py"))
        )
        issues: list[str] = []
        for path in router_files:
            if any(d in _SKIP_DIRS for d in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if re.search(r"@router\.(post|put|delete|patch)\s*\(", line, re.I):
                    block = "\n".join(lines[i: i + 12])
                    has_auth = any(
                        kw in block
                        for kw in ("CurrentUserDep", "require_user", "Authorization")
                    )
                    if not has_auth:
                        method = re.search(r"\.(post|put|delete|patch)", line, re.I)
                        m = method.group(1).upper() if method else "MUTATE"
                        rel = path.relative_to(project_root)
                        issues.append(f"{rel}:{i+1} -- {m} route missing auth")
        if issues:
            report.warnings.extend(issues)
        else:
            report.passed.append("All mutating routes have auth dependencies")

    def _check_sql_injection(self, project_root: Path, report: SecurityReport) -> None:
        found = False
        for path in project_root.rglob("*.py"):
            if any(d in _SKIP_DIRS for d in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for match in _RAW_SQL_FSTRING.finditer(text):
                line = text[: match.start()].count("\n") + 1
                rel = path.relative_to(project_root)
                report.critical.append(f"Raw f-string SQL injection risk in {rel}:{line}")
                found = True
        if not found:
            report.passed.append("No raw f-string SQL queries found")

    def _check_env_hygiene(self, project_root: Path, report: SecurityReport) -> None:
        env_file = project_root / ".env"
        if env_file.exists():
            text = env_file.read_text(encoding="utf-8", errors="ignore")
            real_secrets = [
                ln for ln in text.splitlines()
                if "=" in ln
                and not ln.strip().startswith("#")
                and any(k in ln.upper() for k in ("KEY", "SECRET", "TOKEN", "PASSWORD"))
                and len(ln.split("=", 1)[-1].strip()) > 4
            ]
            if real_secrets:
                report.critical.append(
                    f".env committed with {len(real_secrets)} apparent secret(s)"
                )
            else:
                report.warnings.append(".env present but appears to contain only placeholders")
        else:
            report.passed.append("No .env committed to project root")

        gitignore = project_root / ".gitignore"
        if gitignore.exists():
            gi = gitignore.read_text(encoding="utf-8", errors="ignore")
            if ".env" not in gi:
                report.warnings.append(".gitignore does not exclude .env files")
            else:
                report.passed.append(".gitignore correctly excludes .env")
        else:
            report.warnings.append("No .gitignore found")

    def _check_frontend_key_leak(self, project_root: Path, report: SecurityReport) -> None:
        pattern = re.compile(r"SUPABASE_SERVICE_ROLE_KEY", re.I)
        found = False
        for path in project_root.rglob("*.tsx"):
            if any(d in _SKIP_DIRS for d in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if pattern.search(text):
                rel = path.relative_to(project_root)
                report.critical.append(f"Service-role key in client component {rel}")
                found = True
        if not found:
            report.passed.append("No service-role key leaked into client components")

    def _render_security_md(
        self,
        context: ProjectContext,
        report: SecurityReport,
        project_root: Path,
    ) -> str:
        def rows(items: list[str], sev: str) -> str:
            return "\n".join(f"| {sev} | {item} |" for item in items)

        all_rows = "\n".join(filter(None, [
            rows(report.critical, "CRITICAL"),
            rows(report.warnings, "WARNING"),
            rows(report.passed, "PASS"),
        ])) or "| PASS | No issues detected |"

        owasp = "\n".join(f"- **{k}** -- {v}" for k, v in _OWASP_CONTROLS.items())
        status = "BLOCKED" if report.critical else "PASSED"

        return (
            "# Security Report\n\n"
            f"Project: `{context.project_id}`  \n"
            f"Gate status: **{status}**\n\n"
            "## Threat model\n\n"
            "Multi-tenant SaaS. Trust boundary is Supabase JWT. "
            "Database access restricted by RLS using auth.uid().\n\n"
            "## Controls applied\n\n"
            f"{owasp}\n\n"
            "## Findings\n\n"
            "| Severity | Finding |\n"
            "| -------- | ------- |\n"
            f"{all_rows}\n\n"
            f"Critical: {len(report.critical)} | "
            f"Warnings: {len(report.warnings)} | "
            f"Passed: {len(report.passed)}\n"
        )

    def _write_policies(self, root: Path) -> None:
        p = root / "supabase" / "policies.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_RLS_POLICIES, encoding="utf-8")

    def _write_scanner_configs(self, root: Path) -> None:
        (root / "trivy.yaml").write_text(_TRIVY, encoding="utf-8")
        (root / ".snyk").write_text(_SNYK, encoding="utf-8")
        wf = root / ".github/workflows/security.yml"
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text(_SEC_WORKFLOW, encoding="utf-8")


__all__ = ["SecurityAgent"]
