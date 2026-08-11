"""Render REST API client (subset used by ForgeOS)."""

from __future__ import annotations

from typing import Any

from config import TOOLS, required
from tools.http import http_request

_RENDER_API = "https://api.render.com/v1"


class RenderClient:
    def __init__(
        self,
        api_key: str | None = None,
        owner_id: str | None = None,
    ) -> None:
        self.api_key = api_key or TOOLS.render_api_key
        self.owner_id = owner_id or TOOLS.render_owner_id
        self.api = _RENDER_API

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {required('RENDER_API_KEY', self.api_key)}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Owner
    # ------------------------------------------------------------------

    def get_owner_id(self) -> str:
        """GET /owners — returns the first owner's id (user or team)."""
        data = http_request(f"{self.api}/owners", headers=self._headers())
        owners = data if isinstance(data, list) else []
        if not owners:
            raise RuntimeError("Render: no owners found for this API key")
        # Each element may be {"owner": {...}} or a flat dict depending on API version.
        first = owners[0]
        owner = first.get("owner") or first
        return owner["id"]

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    def create_web_service(
        self,
        name: str,
        repo_url: str,
        branch: str = "main",
        build_cmd: str = "pip install -r requirements.txt",
        start_cmd: str = "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
        root_dir: str = "backend",
        plan: str = "free",
        region: str = "oregon",
        env_vars: dict[str, str] | None = None,
        health_check_path: str | None = None,
    ) -> dict[str, Any]:
        """POST /services — creates a web service from a GitHub repo.

        Defaults are unchanged so existing callers (agents/deploy.py) behave
        exactly as before. plan / region / env_vars / health_check_path were
        added for the mesh backend, which needs a paid Singapore instance with
        its secrets set at creation time rather than a free Oregon one.
        """
        owner_id = self.owner_id or self.get_owner_id()
        service_details: dict[str, Any] = {
            "env": "python",
            "plan": plan,
            "region": region,
            "rootDir": root_dir,
            "envSpecificDetails": {
                "buildCommand": build_cmd,
                "startCommand": start_cmd,
            },
        }
        if health_check_path:
            service_details["healthCheckPath"] = health_check_path

        body: dict[str, Any] = {
            "type": "web_service",
            "name": name,
            "ownerId": owner_id,
            "repo": repo_url,
            "branch": branch,
            "serviceDetails": service_details,
        }
        if env_vars:
            body["envVars"] = [
                {"key": k, "value": v} for k, v in sorted(env_vars.items())
            ]
        return http_request(
            f"{self.api}/services",
            method="POST",
            headers=self._headers(),
            json_body=body,
        )

    def list_services(self, limit: int = 50) -> list[dict[str, Any]]:
        """GET /services — every service this API key can see."""
        data = http_request(
            f"{self.api}/services",
            headers=self._headers(),
            params={"limit": limit},
        )
        return [item.get("service", item) for item in (data or [])]

    def set_env_vars(self, service_id: str, env_vars: dict[str, str]) -> Any:
        """PUT /services/{id}/env-vars — replaces the full env-var set."""
        return http_request(
            f"{self.api}/services/{service_id}/env-vars",
            method="PUT",
            headers=self._headers(),
            json_body=[{"key": k, "value": v} for k, v in sorted(env_vars.items())],
        )

    def get_service(self, service_id: str) -> dict[str, Any]:
        """GET /services/{service_id}."""
        return http_request(
            f"{self.api}/services/{service_id}",
            headers=self._headers(),
        )

    def trigger_deploy(self, service_id: str) -> dict[str, Any]:
        """POST /services/{service_id}/deploys."""
        return http_request(
            f"{self.api}/services/{service_id}/deploys",
            method="POST",
            headers=self._headers(),
            json_body={},
        )

    def get_deploy(self, service_id: str, deploy_id: str) -> dict[str, Any]:
        """GET /services/{service_id}/deploys/{deploy_id}."""
        return http_request(
            f"{self.api}/services/{service_id}/deploys/{deploy_id}",
            headers=self._headers(),
        )


__all__ = ["RenderClient"]
