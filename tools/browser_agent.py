"""
ForgeOS BrowserAgent.

Automates UI tasks that have no stable API:
- GitHub: create org-level repos through the web UI (fallback when token missing)
- Render: trigger manual deploys + fetch service URLs
- Namecheap: register domains from the CLI

Uses the browser_use stub (Playwright-backed) when the real cdp-use package is
unavailable. Falls back to a no-op result with a descriptive error when even
Playwright is absent.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class BrowserResult:
    success: bool
    url: str
    action: str
    output: str
    errors: str = ""


class BrowserAgent:
    """Lightweight browser automation agent backed by browser_use / Playwright."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._llm_model = os.environ.get("BROWSER_LLM", "claude-haiku-4-5-20251001")

    # ------------------------------------------------------------------
    # GitHub
    # ------------------------------------------------------------------

    def create_github_repo(
        self,
        repo_name: str,
        description: str = "",
        private: bool = False,
        org: str | None = None,
    ) -> BrowserResult:
        """Create a GitHub repository via the API (token) or browser UI (fallback)."""
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            return self._gh_api_create(repo_name, description, private, org, token)
        return self._gh_browser_create(repo_name, description, private, org)

    def _gh_api_create(
        self,
        name: str,
        description: str,
        private: bool,
        org: str | None,
        token: str,
    ) -> BrowserResult:
        try:
            import httpx

            url = (
                f"https://api.github.com/orgs/{org}/repos"
                if org
                else "https://api.github.com/user/repos"
            )
            resp = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={"name": name, "description": description, "private": private},
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return BrowserResult(
                    success=True,
                    url=data.get("html_url", ""),
                    action="github.create_repo",
                    output=f"Created repo: {data.get('full_name', name)}",
                )
            return BrowserResult(
                success=False,
                url="",
                action="github.create_repo",
                output="",
                errors=f"GitHub API error {resp.status_code}: {resp.text[:200]}",
            )
        except Exception as e:
            return BrowserResult(
                success=False, url="", action="github.create_repo", output="", errors=str(e)
            )

    def _gh_browser_create(
        self,
        name: str,
        description: str,
        private: bool,
        org: str | None,
    ) -> BrowserResult:
        task = (
            f"Go to https://github.com/new, fill in repository name '{name}', "
            f"description '{description}', set visibility to "
            f"{'private' if private else 'public'}, and click Create repository. "
            "Return the new repository URL."
        )
        return self._run_browser_task(task, "github.create_repo_browser")

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def trigger_render_deploy(self, deploy_hook_url: str) -> BrowserResult:
        """POST to a Render deploy hook URL."""
        try:
            import httpx

            resp = httpx.post(deploy_hook_url, timeout=30)
            if resp.status_code in (200, 201):
                return BrowserResult(
                    success=True,
                    url=deploy_hook_url,
                    action="render.deploy",
                    output="Render deploy triggered",
                )
            return BrowserResult(
                success=False,
                url=deploy_hook_url,
                action="render.deploy",
                output="",
                errors=f"Render hook returned {resp.status_code}",
            )
        except Exception as e:
            return BrowserResult(
                success=False, url=deploy_hook_url, action="render.deploy", output="", errors=str(e)
            )

    def get_render_service_url(self, service_name: str) -> BrowserResult:
        """Retrieve the public URL of a Render service via the Render API."""
        api_key = os.environ.get("RENDER_API_KEY")
        if not api_key:
            return BrowserResult(
                success=False,
                url="",
                action="render.get_url",
                output="",
                errors="RENDER_API_KEY not set",
            )
        try:
            import httpx

            resp = httpx.get(
                "https://api.render.com/v1/services",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                params={"name": service_name, "limit": 5},
                timeout=15,
            )
            if resp.status_code == 200:
                services = resp.json()
                for svc in services:
                    s = svc.get("service", {})
                    if s.get("name") == service_name:
                        slug = s.get("serviceDetails", {}).get("url", "")
                        return BrowserResult(
                            success=True,
                            url=slug,
                            action="render.get_url",
                            output=f"Service URL: {slug}",
                        )
            return BrowserResult(
                success=False,
                url="",
                action="render.get_url",
                output="",
                errors=f"Service {service_name!r} not found or API error {resp.status_code}",
            )
        except Exception as e:
            return BrowserResult(
                success=False, url="", action="render.get_url", output="", errors=str(e)
            )

    # ------------------------------------------------------------------
    # Namecheap
    # ------------------------------------------------------------------

    def register_domain(self, domain: str) -> BrowserResult:
        """Register a domain on Namecheap via browser automation."""
        task = (
            f"Go to https://www.namecheap.com/domains/registration/results/?domain={domain}, "
            "find the .com listing, click Add to Cart, proceed through checkout. "
            "Return the confirmation page URL."
        )
        return self._run_browser_task(task, "namecheap.register")

    def check_domain_available(self, domain: str) -> BrowserResult:
        """Check if a domain is available without purchasing."""
        api_user = os.environ.get("NAMECHEAP_API_USER")
        api_key = os.environ.get("NAMECHEAP_API_KEY")
        client_ip = os.environ.get("NAMECHEAP_CLIENT_IP", "")
        if api_user and api_key and client_ip:
            return self._namecheap_api_check(domain, api_user, api_key, client_ip)
        return self._run_browser_task(
            f"Check if {domain} is available at namecheap.com and return the availability.",
            "namecheap.check",
        )

    def _namecheap_api_check(
        self, domain: str, api_user: str, api_key: str, client_ip: str
    ) -> BrowserResult:
        try:
            import httpx

            sld, _, tld = domain.rpartition(".")
            resp = httpx.get(
                "https://api.namecheap.com/xml.response",
                params={
                    "ApiUser": api_user,
                    "ApiKey": api_key,
                    "UserName": api_user,
                    "ClientIp": client_ip,
                    "Command": "namecheap.domains.check",
                    "DomainList": domain,
                },
                timeout=15,
            )
            available = 'Available="true"' in resp.text
            return BrowserResult(
                success=True,
                url="",
                action="namecheap.check",
                output=f"{domain} is {'available' if available else 'taken'}",
            )
        except Exception as e:
            return BrowserResult(
                success=False, url="", action="namecheap.check", output="", errors=str(e)
            )

    # ------------------------------------------------------------------
    # Generic browser task runner
    # ------------------------------------------------------------------

    def _run_browser_task(self, task: str, action: str) -> BrowserResult:
        try:
            import asyncio as _asyncio

            return _asyncio.get_event_loop().run_until_complete(
                self._async_run_task(task, action)
            )
        except RuntimeError:
            # Already in an event loop (Jupyter / async context)
            import concurrent.futures as _cf
            with _cf.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self._async_run_task(task, action))
                return future.result(timeout=120)

    async def _async_run_task(self, task: str, action: str) -> BrowserResult:
        try:
            import browser_use
            from browser_use import Agent, BrowserConfig

            config = BrowserConfig(headless=self.headless)
            agent = Agent(
                task=task,
                llm=self._build_llm(),
                browser_config=config,
            )
            output = await agent.run(max_steps=20)
            return BrowserResult(success=True, url="", action=action, output=str(output))
        except Exception as e:
            return BrowserResult(
                success=False, url="", action=action, output="", errors=str(e)
            )

    def _build_llm(self) -> Any:
        try:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=self._llm_model, temperature=0)
        except ImportError:
            pass
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model="gpt-4o-mini", temperature=0)
        except ImportError:
            pass
        raise RuntimeError("No LangChain LLM available for browser_use agent")


__all__ = ["BrowserAgent", "BrowserResult"]
