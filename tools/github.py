"""GitHub REST API client (subset used by ForgeOS)."""

from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path
from typing import Any

from config import TOOLS, required
from .http import APIError, http_request


class GitHubClient:
    def __init__(self, token: str | None = None, owner: str | None = None) -> None:
        self.token = token or TOOLS.github_token
        self.owner = owner or TOOLS.github_owner
        self.api = TOOLS.github_api

    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {required('GITHUB_TOKEN', self.token)}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ForgeOS",
        }

    # ------------------------------------------------------------------
    # User / org info
    # ------------------------------------------------------------------

    def get_user(self) -> dict[str, Any]:
        return http_request(f"{self.api}/user", headers=self._headers())

    def resolve_owner(self) -> str:
        if self.owner:
            return self.owner
        info = self.get_user()
        login = info.get("login")
        if not login:
            raise RuntimeError("Cannot resolve GitHub owner")
        self.owner = login
        return login

    # ------------------------------------------------------------------
    # Repo management
    # ------------------------------------------------------------------

    def create_repo(
        self,
        name: str,
        *,
        description: str = "",
        private: bool = True,
        auto_init: bool = True,
    ) -> dict[str, Any]:
        try:
            return http_request(
                f"{self.api}/user/repos",
                method="POST",
                headers=self._headers(),
                json_body={
                    "name": name,
                    "description": description,
                    "private": private,
                    "auto_init": auto_init,
                },
            )
        except APIError as e:
            if e.status == 422 and "already exists" in (e.body or ""):
                owner = self.resolve_owner()
                return self.get_repo(owner, name)
            raise

    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        return http_request(
            f"{self.api}/repos/{owner}/{repo}", headers=self._headers()
        )

    def delete_repo(self, owner: str, repo: str) -> None:
        http_request(
            f"{self.api}/repos/{owner}/{repo}",
            method="DELETE",
            headers=self._headers(),
            expect_json=False,
        )

    # ------------------------------------------------------------------
    # File push (via contents API — simple but limited to <100MB files)
    # ------------------------------------------------------------------

    def put_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: bytes,
        message: str,
        branch: str = "main",
        sha: str | None = None,
    ) -> dict[str, Any]:
        encoded = base64.b64encode(content).decode("ascii")
        body: dict[str, Any] = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        return http_request(
            f"{self.api}/repos/{owner}/{repo}/contents/{path}",
            method="PUT",
            headers=self._headers(),
            json_body=body,
        )

    def push_directory(
        self,
        owner: str,
        repo: str,
        local_dir: str | os.PathLike[str],
        branch: str = "main",
        message: str = "ForgeOS initial commit",
        ignore: tuple[str, ...] = (".git", "node_modules", "__pycache__", ".venv"),
    ) -> int:
        """Push every file under `local_dir` using the contents API.

        Returns the number of files uploaded. Use this for small
        scaffolds; for large codebases, prefer `git_push_with_token`.
        """
        root = Path(local_dir)
        n = 0
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in ignore for part in p.parts):
                continue
            rel = p.relative_to(root).as_posix()
            try:
                existing = http_request(
                    f"{self.api}/repos/{owner}/{repo}/contents/{rel}",
                    headers=self._headers(),
                    params={"ref": branch},
                )
                sha = existing.get("sha") if isinstance(existing, dict) else None
            except APIError:
                sha = None
            self.put_file(
                owner=owner,
                repo=repo,
                path=rel,
                content=p.read_bytes(),
                message=f"{message}: {rel}",
                branch=branch,
                sha=sha,
            )
            n += 1
        return n

    # ------------------------------------------------------------------
    # Workflow runs (CI polling)
    # ------------------------------------------------------------------

    def list_workflow_runs(
        self, owner: str, repo: str, branch: str = "main", per_page: int = 5
    ) -> list[dict[str, Any]]:
        data = http_request(
            f"{self.api}/repos/{owner}/{repo}/actions/runs",
            headers=self._headers(),
            params={"branch": branch, "per_page": per_page},
        )
        return list((data or {}).get("workflow_runs", []))

    def get_workflow_run(self, owner: str, repo: str, run_id: int) -> dict[str, Any]:
        return http_request(
            f"{self.api}/repos/{owner}/{repo}/actions/runs/{run_id}",
            headers=self._headers(),
        )

    # ------------------------------------------------------------------
    # Pull requests (used by the healer)
    # ------------------------------------------------------------------

    def create_branch(
        self, owner: str, repo: str, new_branch: str, from_branch: str = "main"
    ) -> dict[str, Any]:
        ref = http_request(
            f"{self.api}/repos/{owner}/{repo}/git/ref/heads/{from_branch}",
            headers=self._headers(),
        )
        sha = ref["object"]["sha"]
        return http_request(
            f"{self.api}/repos/{owner}/{repo}/git/refs",
            method="POST",
            headers=self._headers(),
            json_body={"ref": f"refs/heads/{new_branch}", "sha": sha},
        )

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> dict[str, Any]:
        return http_request(
            f"{self.api}/repos/{owner}/{repo}/pulls",
            method="POST",
            headers=self._headers(),
            json_body={"title": title, "head": head, "base": base, "body": body},
        )

    def merge_pull_request(
        self,
        owner: str,
        repo: str,
        number: int,
        merge_method: str = "squash",
    ) -> dict[str, Any]:
        return http_request(
            f"{self.api}/repos/{owner}/{repo}/pulls/{number}/merge",
            method="PUT",
            headers=self._headers(),
            json_body={"merge_method": merge_method},
        )

    # ------------------------------------------------------------------
    # Local git push (preferred for full repos)
    # ------------------------------------------------------------------

    def git_push_with_token(
        self,
        local_dir: str | os.PathLike[str],
        owner: str,
        repo: str,
        branch: str = "main",
        commit_message: str = "ForgeOS initial commit",
        signed: bool = False,
    ) -> str:
        """Initialise a git repo locally and push to GitHub via HTTPS."""
        cwd = str(Path(local_dir))
        token = required("GITHUB_TOKEN", self.token)
        url = f"https://{owner}:{token}@github.com/{owner}/{repo}.git"

        def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                cwd=cwd,
                check=check,
                capture_output=True,
                text=True,
            )

        if not (Path(cwd) / ".git").exists():
            run(["git", "init", "-b", branch])
        run(["git", "add", "-A"])
        commit_args = ["git", "commit", "-m", commit_message, "--allow-empty"]
        if signed:
            commit_args.insert(2, "-S")
        run(commit_args, check=False)
        # Configure remote
        run(["git", "remote", "remove", "origin"], check=False)
        run(["git", "remote", "add", "origin", url])
        run(["git", "branch", "-M", branch])
        run(["git", "push", "-u", "origin", branch, "--force"])
        return f"https://github.com/{owner}/{repo}"


__all__ = ["GitHubClient"]
