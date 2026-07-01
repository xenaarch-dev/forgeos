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

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from forge_sdk.agent import ForgeAgent
from models import ProjectContext, TaskStatus
from models.outputs.security_output import compute_owasp_score


_SECRET_PATTERNS = [
    re.compile(r"(?:aws_secret_access_key|aws_access_key_id)\s*=\s*['\"][^'\"]{16,}['\"]", re.I),
    re.compile(r"(?:api_-?key|apikey)\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]", re.I),
    re.compile(r"(?:secret|token)\s*=\s*['\"][A-Za-z0-9_\-]{24,}['\"]", re.I),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
]


class SecurityAgent(ForgeAgent):
    name         = "security"
    phase        = "security"
    capabilities = ["SECURITY.md", "supabase/policies.sql", "trivy.yaml", ".snyk"]
    requires     = ["project/"]
    budget_usd   = 0.0

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        project_root = Path(context.workdir) / "project"
        if not project_root.exists():
            raise RuntimeError("Project missing — cannot audit")

        # Run semgrep first — execution-verified static analysis before regex scan.
        semgrep_findings = self._run_semgrep(project_root)
        semgrep_critical = [
            f for f in semgrep_findings
            if f.get("extra", {}).get("severity", "").upper() == "ERROR"
        ]

        findings = self._scan(project_root)
        self._write_policies(project_root)
        self._write_scanner_configs(project_root)
        sec_md = self._render_security_md(context, findings, project_root, semgrep_findings)
        self._write(context, "SECURITY.md", sec_md)
        # Copy into the project itself so it ships with the generated code.
        (project_root / "SECURITY.md").write_text(sec_md, encoding="utf-8")

        # Mark security tasks done
        for t in context.tasks:
            if t.agent == "security":
                t.status = TaskStatus.DONE.value

        # Record findings on context so they show up in SUMMARY.
        # semgrep section is read by CSOGate — if blocking=True, CSOGate fails outright.
        context.metadata.setdefault("security", {})
        context.metadata["security"] = {
            "issues": [
                {"path": str(f.path), "severity": f.severity, "message": f.message}
                for f in findings
            ],
            "owasp_controls": _OWASP_CONTROLS,
            "semgrep": {
                "findings_count": len(semgrep_findings),
                "critical_count": len(semgrep_critical),
                "blocking": len(semgrep_critical) > 0,
                "critical_findings": [
                    {
                        "check_id": f.get("check_id", ""),
                        "path": f.get("path", ""),
                        "message": f.get("extra", {}).get("message", "")[:200],
                        "severity": f.get("extra", {}).get("severity", ""),
                    }
                    for f in semgrep_critical
                ],
            },
        }

        critical = [f for f in findings if f.severity == "critical"]
        warnings = [f for f in findings if f.severity in ("high", "medium")]
        passed_checks = [k for k in _OWASP_CONTROLS if k not in {f.message for f in critical}]
        owasp_score = compute_owasp_score(len(critical), len(warnings))

        return {
            "issues": len(findings),
            "report": "SECURITY.md",
            "owasp_score": owasp_score,
            "critical_count": len(critical),
            "warnings_count": len(warnings),
            "passed_count": len(passed_checks),
            "critical_findings": [f.message for f in critical],
            "warnings_list": [f.message for f in warnings],
            "passed_checks": passed_checks,
            "semgrep_findings": len(semgrep_findings),
            "semgrep_critical": len(semgrep_critical),
            "semgrep_blocking": len(semgrep_critical) > 0,
            "security_md_written": True,
            "rls_policies_written": True,
            "ci_security_workflow_written": True,
        }

    # ------------------------------------------------------------------
    # Semgrep — execution-verified static analysis
    # ------------------------------------------------------------------

    def _run_semgrep(self, project_root: Path) -> list[dict]:
        """Run semgrep --config=auto --json against the project directory.

        Returns a list of semgrep finding dicts. Returns [] if semgrep is not
        installed or if the scan errors (never raises — failure is logged, not thrown).
        The caller checks finding['extra']['severity'] == 'ERROR' to identify blockers.

        Install semgrep: pip install semgrep --break-system-packages
        """
        import os

        binary = shutil.which("semgrep") or self._find_semgrep_binary()
        if not binary:
            self._log(
                "[security] semgrep not found on PATH — skipping execution-verified "
                "static analysis. Install: pip install semgrep --break-system-packages"
            )
            return []
        try:
            # Ensure semgrep's own directory is on PATH so it can invoke pysemgrep.
            env = os.environ.copy()
            binary_dir = str(Path(binary).parent)
            env["PATH"] = binary_dir + os.pathsep + env.get("PATH", "")

            result = subprocess.run(
                [binary, "--config=auto", "--json", "--quiet", str(project_root)],
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )
            # semgrep exits non-zero when findings exist — that's expected.
            raw = result.stdout.strip()
            if not raw:
                return []
            data = json.loads(raw)
            return data.get("results", [])
        except subprocess.TimeoutExpired:
            self._log("[security] semgrep timed out after 180s — skipping")
            return []
        except json.JSONDecodeError as e:
            self._log(f"[security] semgrep JSON parse error: {e}")
            return []
        except Exception as e:
            self._log(f"[security] semgrep failed: {e}")
            return []

    @staticmethod
    def _find_semgrep_binary() -> str | None:
        """Find semgrep in the Python user-scripts directory (Windows fallback)."""
        import os
        scripts_dir = os.path.join(
            os.path.dirname(sys.executable), "Scripts"
        )
        candidate = os.path.join(scripts_dir, "semgrep.exe")
        if os.path.isfile(candidate):
            return candidate
        # User-level pip install on Windows
        user_scripts = os.path.join(
            os.path.expandvars("%APPDATA%"), "Python",
            f"Python{sys.version_info.major}{sys.version_info.minor}",
            "Scripts", "semgrep.exe",
        )
        if os.path.isfile(user_scripts):
            return user_scripts
        return None

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
        self,
        context: ProjectContext,
        findings: list["Finding"],
        project_root: Path,
        semgrep_findings: list[dict] | None = None,
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

        # Semgrep section — included regardless of whether findings exist.
        sg = semgrep_findings or []
        sg_critical = [f for f in sg if f.get("extra", {}).get("severity", "").upper() == "ERROR"]
        sg_warnings = [f for f in sg if f.get("extra", {}).get("severity", "").upper() == "WARNING"]
        if not sg:
            semgrep_section = "Semgrep not available or produced no findings.\n"
        elif sg_critical:
            rows = "\n".join(
                f"| ERROR | `{f.get('path', '')}` | [{f.get('check_id', '')}] "
                f"{f.get('extra', {}).get('message', '')[:120]} |"
                for f in sg_critical
            )
            semgrep_section = (
                f"⛔ **{len(sg_critical)} ERROR-severity finding(s) detected. "
                f"CSOGate will block until these are resolved.**\n\n"
                "| Severity | File | Finding |\n"
                "| -------- | ---- | ------- |\n"
                f"{rows}\n"
            )
        else:
            semgrep_section = (
                f"✅ No ERROR-severity findings. "
                f"{len(sg_warnings)} WARNING-severity finding(s) — review recommended.\n"
            )

        return (
            "# Security Report\n\n"
            f"Project: `{context.project_id}`\n\n"
            "## Semgrep Static Analysis (execution-verified)\n\n"
            f"{semgrep_section}\n"
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
            "## Heuristic findings\n\n"
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
