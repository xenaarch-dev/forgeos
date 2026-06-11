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
    ) -> dict[str, Any]:
        """POST /services — creates a web service from a GitHub repo."""
        owner_id = self.owner_id or self.get_owner_id()
        body: dict[str, Any] = {
            "type": "web_service",
            "name": name,
            "ownerId": owner_id,
            "repo": repo_url,
            "branch": branch,
            "serviceDetails": {
                "env": "python",
                "plan": "free",
                "region": "oregon",
                "rootDir": root_dir,
                "envSpecificDetails": {
                    "buildCommand": build_cmd,
                    "startCommand": start_cmd,
                },
            },
        }
        return http_request(
            f"{self.api}/services",
            method="POST",
            headers=self._headers(),
            json_body=body,
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
