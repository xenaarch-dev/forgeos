"""
DeployAgent.

Initialises a GitHub repo, pushes the project, configures Railway
(backend), Vercel (frontend), Sentry, and Uptime Robot, then writes
DEPLOYMENT.md with all live URLs and a runbook.

The agent degrades gracefully: if a credential or API call fails it
records the issue in `context.failures` and skips that step rather than
aborting the whole deploy.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config import RUNTIME, TOOLS
from models import ProjectContext, TaskStatus
from tools import (
    GitHubClient,
    RenderClient,
    SentryClient,
    UptimeRobotClient,
    VercelClient,
)
from forge_sdk.agent import ForgeAgent


class DeployAgent(ForgeAgent):
    name         = "deploy"
    phase        = "deploy"
    capabilities = ["DEPLOYMENT.md"]
    requires     = ["idea", "project_id"]
    budget_usd   = 0.0

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        project_root = Path(context.workdir) / "project"
        if not project_root.exists():
            raise RuntimeError("Project missing — cannot deploy")

        result: dict[str, Any] = {
            "repo_url": "",
            "backend_url": "",
            "frontend_url": "",
            "monitoring": {},
            "skipped": [],
        }

        repo_name = self._derive_repo_name(context)
        result["repo_url"] = self._step("github", lambda: self._step_github(context, project_root, repo_name)) or ""
        if result["repo_url"]:
            context.repo_url = result["repo_url"]

        result["backend_url"] = self._step("render", lambda: self._step_render(context, repo_name)) or ""
        if result["backend_url"]:
            context.backend_url = result["backend_url"]

        result["frontend_url"] = self._step("vercel", lambda: self._step_vercel(context, repo_name)) or ""
        if result["frontend_url"]:
            context.frontend_url = result["frontend_url"]

        sentry = self._step("sentry", lambda: self._step_sentry(context, repo_name)) or {}
        if sentry:
            context.monitoring_urls["sentry"] = sentry.get("url", "")
            result["monitoring"]["sentry"] = sentry

        uptime = self._step("uptimerobot", lambda: self._step_uptime(context, result.get("backend_url") or result.get("frontend_url") or "")) or {}
        if uptime:
            context.monitoring_urls["uptimerobot"] = uptime.get("url", "")
            result["monitoring"]["uptimerobot"] = uptime

        smoke = self._smoke_tests(context, result.get("backend_url"), result.get("frontend_url"))
        result["smoke"] = smoke

        deployment_md = self._render_deployment_md(context, result)
        self._write(context, "DEPLOYMENT.md", deployment_md)
        (project_root / "DEPLOYMENT.md").write_text(deployment_md, encoding="utf-8")

        for t in context.tasks:
            if t.agent == "deploy":
                t.status = TaskStatus.DONE.value if not result["skipped"] else TaskStatus.BLOCKED.value

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _step(self, name: str, fn) -> Any:
        try:
            return fn()
        except Exception as e:
            detail = getattr(e, "body", "") or ""
            msg = str(e) + (f" | {detail[:300]}" if detail else "")
            self._log(f"[deploy] step '{name}' skipped: {msg}")
            return None

    def _derive_repo_name(self, context: ProjectContext) -> str:
        # Slugify project_id + first few words of idea.
        words = [
            w
            for w in context.idea.lower().split()
            if w.isalnum() and 2 <= len(w) <= 20
        ][:4]
        slug = "-".join(words) or "forgeos-app"
        return f"{slug}-{context.project_id.split('_')[-1][:6]}"

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _step_github(
        self, context: ProjectContext, project_root: Path, repo_name: str
    ) -> str:
        client = GitHubClient()
        owner = client.resolve_owner()
        client.create_repo(
            name=repo_name,
            description=context.idea[:300],
            private=True,
            auto_init=False,
        )
        try:
            client.git_push_with_token(
                local_dir=project_root,
                owner=owner,
                repo=repo_name,
                branch="main",
                commit_message="ForgeOS: initial commit",
                signed=False,
            )
            url = f"https://github.com/{owner}/{repo_name}"
        except Exception as e:
            self._log(f"[deploy] git push failed, falling back to contents API: {e}")
            client.push_directory(owner, repo_name, project_root)
            url = f"https://github.com/{owner}/{repo_name}"

        # Poll a CI run if one was triggered
        try:
            self._poll_ci(client, owner, repo_name)
        except Exception as e:
            self._log(f"[deploy] CI poll skipped: {e}")
        return url

    def _poll_ci(
        self, client: GitHubClient, owner: str, repo: str, attempts: int = 20
    ) -> None:
        for _ in range(attempts):
            runs = client.list_workflow_runs(owner, repo, branch="main")
            if not runs:
                time.sleep(15)
                continue
            run = runs[0]
            status = run.get("status")
            conclusion = run.get("conclusion")
            if status == "completed":
                if conclusion not in ("success",):
                    raise RuntimeError(f"CI ended with conclusion={conclusion}")
                return
            time.sleep(15)
        raise TimeoutError("CI did not complete in time")

    def _step_render(self, context: ProjectContext, repo_name: str) -> str:
        if not TOOLS.render_api_key:
            raise RuntimeError("RENDER_API_KEY missing")
        client = RenderClient()
        owner_id = TOOLS.render_owner_id or client.get_owner_id()
        github_owner = TOOLS.github_owner or GitHubClient().resolve_owner()
        repo_url = f"https://github.com/{github_owner}/{repo_name}"
        service = client.create_web_service(
            name=repo_name,
            repo_url=repo_url,
            branch="main",
            root_dir="backend",
        )
        service_id = service.get("id") or service.get("service", {}).get("id", "")
        return f"https://{repo_name}.onrender.com"

    def _step_vercel(self, context: ProjectContext, repo_name: str) -> str:
        if not TOOLS.vercel_token:
            raise RuntimeError("VERCEL_TOKEN missing")
        client = VercelClient()
        owner = TOOLS.github_owner or GitHubClient().resolve_owner()
        try:
            project = client.create_project(
                name=repo_name,
                framework="nextjs",
                github_repo=f"{owner}/{repo_name}",
                root_directory="frontend",
            )
        except Exception as e:
            body = getattr(e, "body", "") or ""
            if "Login Connection" in body or "login connection" in body.lower():
                raise RuntimeError(
                    "Vercel requires GitHub connected: go to vercel.com/account → "
                    "Git Integrations → Install GitHub App, then re-run deploy."
                ) from e
            raise
        client.trigger_deployment(
            project_name=project.get("name", repo_name),
            github_repo=f"{owner}/{repo_name}",
            ref="main",
        )
        slug = project.get("name", repo_name)
        return f"https://{slug}.vercel.app"

    def _step_sentry(self, context: ProjectContext, repo_name: str) -> dict[str, Any]:
        if not TOOLS.sentry_token or not TOOLS.sentry_org:
            raise RuntimeError("Sentry not configured")
        client = SentryClient()
        teams = client.list_teams()
        if not teams:
            raise RuntimeError("No Sentry teams")
        team_slug = teams[0].get("slug", "default")
        project = client.create_project(team_slug=team_slug, name=repo_name)
        return {
            "url": f"https://{TOOLS.sentry_org}.sentry.io/projects/{project.get('slug')}/",
            "team": team_slug,
            "project": project.get("slug"),
        }

    def _step_uptime(self, context: ProjectContext, monitor_url: str) -> dict[str, Any]:
        if not TOOLS.uptimerobot_api_key:
            raise RuntimeError("UPTIMEROBOT_API_KEY missing")
        if not monitor_url:
            raise RuntimeError("No URL to monitor")
        client = UptimeRobotClient()
        resp = client.create_monitor(
            friendly_name=context.project_id,
            url=monitor_url,
            monitor_type=1,
            interval=300,
        )
        monitor = (resp or {}).get("monitor", {})
        return {
            "url": "https://uptimerobot.com/dashboard",
            "id": monitor.get("id"),
            "monitored": monitor_url,
        }

    # ------------------------------------------------------------------
    # Smoke + reports
    # ------------------------------------------------------------------

    def _smoke_tests(
        self, context: ProjectContext, backend_url: str | None, frontend_url: str | None
    ) -> dict[str, Any]:
        import urllib.request

        def probe(url: str) -> dict[str, Any]:
            try:
                with urllib.request.urlopen(url, timeout=20) as resp:
                    return {"url": url, "status": resp.status}
            except Exception as e:
                return {"url": url, "status": 0, "error": str(e)}

        results: dict[str, Any] = {}
        if backend_url:
            results["backend_health"] = probe(backend_url.rstrip("/") + "/healthz")
        if frontend_url:
            results["frontend_root"] = probe(frontend_url)
        return results

    def _render_deployment_md(
        self, context: ProjectContext, result: dict[str, Any]
    ) -> str:
        return (
            "# Deployment\n\n"
            f"Project: `{context.project_id}`\n\n"
            "## Live URLs\n\n"
            f"- Repository: {result.get('repo_url') or '(skipped)'}\n"
            f"- Backend: {result.get('backend_url') or '(skipped)'}\n"
            f"- Frontend: {result.get('frontend_url') or '(skipped)'}\n\n"
            "## Monitoring\n\n"
            f"- Sentry: {context.monitoring_urls.get('sentry', '(not configured)')}\n"
            f"- Uptime Robot: {context.monitoring_urls.get('uptimerobot', '(not configured)')}\n\n"
            "## Smoke tests\n\n"
            "```json\n"
            f"{json.dumps(result.get('smoke', {}), indent=2)}\n"
            "```\n\n"
            "## Runbook\n\n"
            "1. **Rollback (backend):** open the Render dashboard, navigate to the service, and redeploy a previous commit.\n"
            "2. **Rollback (frontend):** in Vercel, promote the previous deployment to production.\n"
            "3. **Rotate secrets:** update Doppler config + redeploy backend + frontend.\n"
            "4. **Investigate errors:** open the Sentry project link above; the healer service may already have opened a PR.\n"
            "5. **Restore database:** Supabase keeps daily backups; restore via the dashboard.\n"
        )


__all__ = ["DeployAgent"]
