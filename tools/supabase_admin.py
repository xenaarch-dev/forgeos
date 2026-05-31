"""Supabase Management API client (subset used by ForgeOS)."""

from __future__ import annotations

from typing import Any

from config import TOOLS, required
from .http import http_request


class SupabaseAdminClient:
    def __init__(
        self,
        access_token: str | None = None,
        project_ref: str | None = None,
    ) -> None:
        self.token = access_token or TOOLS.supabase_access_token
        self.project_ref = project_ref or TOOLS.supabase_project_ref
        self.api = TOOLS.supabase_api

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {required('SUPABASE_ACCESS_TOKEN', self.token)}",
            "Content-Type": "application/json",
        }

    def list_organizations(self) -> list[dict[str, Any]]:
        data = http_request(f"{self.api}/v1/organizations", headers=self._headers())
        return list(data or [])

    def list_projects(self) -> list[dict[str, Any]]:
        data = http_request(f"{self.api}/v1/projects", headers=self._headers())
        return list(data or [])

    def create_project(
        self,
        name: str,
        org_id: str,
        region: str = "us-east-1",
        db_password: str = "",
    ) -> dict[str, Any]:
        if not db_password:
            import secrets
            db_password = secrets.token_urlsafe(20)
        return http_request(
            f"{self.api}/v1/projects",
            method="POST",
            headers=self._headers(),
            json_body={
                "name": name,
                "organization_id": org_id,
                "region": region,
                "db_pass": db_password,
                "plan": "free",
            },
        )

    def get_project_keys(self, project_ref: str | None = None) -> dict[str, Any]:
        ref = project_ref or self.project_ref
        if not ref:
            raise ValueError("Supabase project_ref required")
        return http_request(
            f"{self.api}/v1/projects/{ref}/api-keys",
            headers=self._headers(),
        )

    def run_query(self, sql: str, project_ref: str | None = None) -> dict[str, Any]:
        ref = project_ref or self.project_ref
        if not ref:
            raise ValueError("Supabase project_ref required")
        return http_request(
            f"{self.api}/v1/projects/{ref}/database/query",
            method="POST",
            headers=self._headers(),
            json_body={"query": sql},
        )

    def apply_migration(
        self, sql: str, project_ref: str | None = None, name: str = "forgeos_baseline"
    ) -> dict[str, Any]:
        ref = project_ref or self.project_ref
        if not ref:
            raise ValueError("Supabase project_ref required")
        return http_request(
            f"{self.api}/v1/projects/{ref}/database/migrations",
            method="POST",
            headers=self._headers(),
            json_body={"name": name, "query": sql},
        )


__all__ = ["SupabaseAdminClient"]
