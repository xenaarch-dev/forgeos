"""Railway GraphQL client (subset used by ForgeOS)."""

from __future__ import annotations

from typing import Any

from config import TOOLS, required
from .http import http_request


class RailwayClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or TOOLS.railway_token
        self.api = TOOLS.railway_api

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {required('RAILWAY_TOKEN', self.token)}",
            "Content-Type": "application/json",
        }

    def query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        data = http_request(
            self.api,
            method="POST",
            headers=self._headers(),
            json_body=payload,
        )
        if isinstance(data, dict) and data.get("errors"):
            raise RuntimeError(f"Railway error: {data['errors']}")
        return (data or {}).get("data", {})

    def me(self) -> dict[str, Any]:
        return self.query("query { me { id email } }").get("me", {})

    def create_project(self, name: str, description: str = "") -> dict[str, Any]:
        q = """
        mutation projectCreate($input: ProjectCreateInput!) {
          projectCreate(input: $input) { id name }
        }
        """
        return self.query(
            q, {"input": {"name": name, "description": description}}
        ).get("projectCreate", {})

    def create_environment(self, project_id: str, name: str = "production") -> dict[str, Any]:
        q = """
        mutation environmentCreate($input: EnvironmentCreateInput!) {
          environmentCreate(input: $input) { id name }
        }
        """
        return self.query(
            q, {"input": {"projectId": project_id, "name": name}}
        ).get("environmentCreate", {})

    def get_project_environments(self, project_id: str) -> list[dict[str, Any]]:
        q = """
        query project($id: String!) {
          project(id: $id) {
            environments { edges { node { id name } } }
          }
        }
        """
        data = self.query(q, {"id": project_id})
        edges = data.get("project", {}).get("environments", {}).get("edges", [])
        return [e["node"] for e in edges]

    def create_service_from_repo(
        self,
        project_id: str,
        repo: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        q = """
        mutation serviceCreate($input: ServiceCreateInput!) {
          serviceCreate(input: $input) { id name }
        }
        """
        return self.query(
            q,
            {
                "input": {
                    "projectId": project_id,
                    "source": {"repo": repo, "branch": branch},
                }
            },
        ).get("serviceCreate", {})

    def deploy_service(
        self, service_id: str, environment_id: str
    ) -> dict[str, Any]:
        q = """
        mutation serviceInstanceDeployV2($serviceId: String!, $environmentId: String!) {
          serviceInstanceDeployV2(serviceId: $serviceId, environmentId: $environmentId)
        }
        """
        return self.query(q, {"serviceId": service_id, "environmentId": environment_id})

    def restart_service(self, service_id: str, environment_id: str) -> dict[str, Any]:
        q = """
        mutation serviceInstanceRedeploy($serviceId: String!, $environmentId: String!) {
          serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
        }
        """
        return self.query(q, {"serviceId": service_id, "environmentId": environment_id})

    def get_deployment(self, deployment_id: str) -> dict[str, Any]:
        q = """
        query deployment($id: String!) {
          deployment(id: $id) { id status url }
        }
        """
        return self.query(q, {"id": deployment_id}).get("deployment", {})


__all__ = ["RailwayClient"]
