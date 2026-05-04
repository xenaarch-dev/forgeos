"""Vercel REST API client (subset used by ForgeOS)."""

from __future__ import annotations

from typing import Any

from config import TOOLS, required
from .http import http_request


class VercelClient:
    def __init__(self, token: str | None = None, team_id: str | None = None) -> None:
        self.token = token or TOOLS.vercel_token
        self.team_id = team_id or TOOLS.vercel_team_id
        self.api = TOOLS.vercel_api

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {required('VERCEL_TOKEN', self.token)}",
            "Content-Type": "application/json",
        }

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params = dict(extra or {})
        if self.team_id:
            params.setdefault("teamId", self.team_id)
        return params

    def whoami(self) -> dict[str, Any]:
        return http_request(
            f"{self.api}/v2/user", headers=self._headers(), params=self._params()
        )

    def list_projects(self) -> list[dict[str, Any]]:
        data = http_request(
            f"{self.api}/v9/projects",
            headers=self._headers(),
            params=self._params(),
        )
        return list((data or {}).get("projects", []))

    def create_project(
        self,
        name: str,
        *,
        framework: str = "nextjs",
        github_repo: str | None = None,
        root_directory: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "framework": framework}
        if github_repo:
            body["gitRepository"] = {"type": "github", "repo": github_repo}
        if root_directory:
            body["rootDirectory"] = root_directory
        return http_request(
            f"{self.api}/v10/projects",
            method="POST",
            headers=self._headers(),
            params=self._params(),
            json_body=body,
        )

    def add_env_var(
        self,
        project_id: str,
        key: str,
        value: str,
        target: list[str] | None = None,
        env_type: str = "encrypted",
    ) -> dict[str, Any]:
        return http_request(
            f"{self.api}/v10/projects/{project_id}/env",
            method="POST",
            headers=self._headers(),
            params=self._params(),
            json_body={
                "key": key,
                "value": value,
                "type": env_type,
                "target": target or ["production", "preview", "development"],
            },
        )

    def trigger_deployment(
        self, project_name: str, github_repo: str, ref: str = "main"
    ) -> dict[str, Any]:
        owner, _, name = github_repo.partition("/")
        return http_request(
            f"{self.api}/v13/deployments",
            method="POST",
            headers=self._headers(),
            params=self._params(),
            json_body={
                "name": project_name,
                "target": "production",
                "gitSource": {
                    "type": "github",
                    "repo": name,
                    "org": owner,
                    "ref": ref,
                },
            },
        )

    def get_deployment(self, deployment_id: str) -> dict[str, Any]:
        return http_request(
            f"{self.api}/v13/deployments/{deployment_id}",
            headers=self._headers(),
            params=self._params(),
        )


__all__ = ["VercelClient"]
