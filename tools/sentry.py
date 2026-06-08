"""Sentry REST API client (subset used by ForgeOS)."""

from __future__ import annotations

from typing import Any

from config import TOOLS, required
from .http import http_request


class SentryClient:
    def __init__(self, token: str | None = None, organization: str | None = None) -> None:
        self.token = token or TOOLS.sentry_token
        self.organization = organization or TOOLS.sentry_org
        self.api = TOOLS.sentry_api

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {required('SENTRY_AUTH_TOKEN', self.token)}",
            "Content-Type": "application/json",
        }

    def list_teams(self) -> list[dict[str, Any]]:
        org = required("SENTRY_ORG", self.organization)
        data = http_request(f"{self.api}/organizations/{org}/teams/", headers=self._headers())
        return list(data or [])

    def create_project(
        self,
        team_slug: str,
        name: str,
        platform: str = "python",
    ) -> dict[str, Any]:
        org = required("SENTRY_ORG", self.organization)
        return http_request(
            f"{self.api}/teams/{org}/{team_slug}/projects/",
            method="POST",
            headers=self._headers(),
            json_body={"name": name, "slug": name, "platform": platform},
        )

    def get_project_keys(self, project_slug: str) -> list[dict[str, Any]]:
        org = required("SENTRY_ORG", self.organization)
        data = http_request(
            f"{self.api}/projects/{org}/{project_slug}/keys/",
            headers=self._headers(),
        )
        return list(data or [])

    def list_unresolved_issues(
        self, project_slug: str, limit: int = 25
    ) -> list[dict[str, Any]]:
        org = required("SENTRY_ORG", self.organization)
        data = http_request(
            f"{self.api}/projects/{org}/{project_slug}/issues/",
            headers=self._headers(),
            params={"query": "is:unresolved", "limit": limit},
        )
        return list(data or [])

    def get_issue(self, issue_id: str) -> dict[str, Any]:
        return http_request(
            f"{self.api}/issues/{issue_id}/",
            headers=self._headers(),
        )

    def resolve_issue(self, issue_id: str) -> dict[str, Any]:
        return http_request(
            f"{self.api}/issues/{issue_id}/",
            method="PUT",
            headers=self._headers(),
            json_body={"status": "resolved"},
        )


__all__ = ["SentryClient"]
