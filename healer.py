"""
Self-healing daemon.

Runs in a loop alongside deployed projects:

* Every 5 minutes, polls Sentry for new unresolved issues. For each one
  it asks Claude for a fix, opens a branch + PR with the change, and
  attempts to auto-merge once CI is green.
* Every 60 seconds, polls Uptime Robot. If a monitor reports DOWN it
  triggers a Railway service restart.

All autonomous actions are logged to `HEALER_LOG.md`.
"""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import RUNTIME, TOOLS
from llm.router import complete as llm_complete
from tools import GitHubClient, RailwayClient, SentryClient, UptimeRobotClient


@dataclass
class HealerTarget:
    """Configuration for a single deployed product to be healed."""

    project_id: str
    github_owner: str
    github_repo: str
    sentry_project: str
    railway_service_id: str = ""
    railway_environment_id: str = ""
    uptime_monitor_id: int = 0
    log_path: str = "HEALER_LOG.md"


class Healer:
    def __init__(self, target: HealerTarget) -> None:
        self.target = target
        self.gh = GitHubClient()
        self.sentry = SentryClient()
        self.railway = RailwayClient() if TOOLS.railway_token else None
        self.uptime = UptimeRobotClient() if TOOLS.uptimerobot_api_key else None
        self._seen_issue_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Public loop
    # ------------------------------------------------------------------

    def run_forever(self) -> None:
        self._log("starting healer loop")
        sentry_next = 0.0
        uptime_next = 0.0
        while True:
            now = time.time()
            try:
                if now >= sentry_next:
                    self.tick_sentry()
                    sentry_next = now + RUNTIME.healer_sentry_interval
                if now >= uptime_next:
                    self.tick_uptime()
                    uptime_next = now + RUNTIME.healer_uptime_interval
            except KeyboardInterrupt:
                self._log("healer interrupted, exiting")
                return
            except Exception as e:
                self._log(f"healer iteration error: {e}\n{traceback.format_exc()}")
            time.sleep(min(sentry_next, uptime_next) - time.time() + 0.1 if sentry_next else 30)

    # ------------------------------------------------------------------
    # Sentry tick
    # ------------------------------------------------------------------

    def tick_sentry(self) -> None:
        try:
            issues = self.sentry.list_unresolved_issues(self.target.sentry_project)
        except Exception as e:
            self._log(f"sentry poll failed: {e}")
            return

        for issue in issues:
            issue_id = str(issue.get("id"))
            if not issue_id or issue_id in self._seen_issue_ids:
                continue
            try:
                self._handle_issue(issue)
            except Exception as e:
                self._log(f"failed to handle issue {issue_id}: {e}")
            finally:
                self._seen_issue_ids.add(issue_id)

    def _handle_issue(self, issue: dict[str, Any]) -> None:
        issue_id = str(issue.get("id"))
        title = issue.get("title", "Sentry issue")
        culprit = issue.get("culprit", "") or issue.get("metadata", {}).get("filename", "")

        self._log(f"new issue {issue_id}: {title} ({culprit})")

        prompt = (
            f"A Sentry issue was reported on the live application.\n\n"
            f"TITLE: {title}\n"
            f"CULPRIT: {culprit}\n"
            f"PAYLOAD:\n{json.dumps(issue, indent=2, default=str)[:4000]}\n\n"
            "Propose a minimal patch as one or more file blocks tagged with "
            "the relative path from the repo root. Always include a clear "
            "fix; if you cannot infer the exact change, output a TODO note "
            "in the relevant file with the diagnostic steps required."
        )
        try:
            resp = llm_complete(
                user=prompt,
                system_extra=(
                    "You are an autonomous bug-fix agent. Be conservative — "
                    "make the smallest change that addresses the symptom. "
                    "Always add a regression test."
                ),
                task_complexity="medium",
                task_type="review",
                purpose="healer.fix",
                stream=False,
                max_tokens=3000,
                temperature=0.1,
            )
        except Exception as e:
            self._log(f"LLM unavailable, cannot propose fix: {e}")
            return

        files = self._parse_files(resp.text)
        if not files:
            self._log(f"no files in fix suggestion for {issue_id}")
            return

        branch = f"healer/issue-{issue_id}"
        try:
            self.gh.create_branch(
                self.target.github_owner, self.target.github_repo, branch
            )
        except Exception as e:
            self._log(f"branch create failed for {branch}: {e}")
            return

        for relpath, content in files.items():
            try:
                self.gh.put_file(
                    owner=self.target.github_owner,
                    repo=self.target.github_repo,
                    path=relpath,
                    content=content.encode("utf-8"),
                    message=f"healer: fix #{issue_id} in {relpath}",
                    branch=branch,
                )
            except Exception as e:
                self._log(f"put_file failed for {relpath}: {e}")

        try:
            pr = self.gh.create_pull_request(
                owner=self.target.github_owner,
                repo=self.target.github_repo,
                title=f"healer: fix Sentry issue #{issue_id} — {title[:60]}",
                head=branch,
                base="main",
                body=f"Automated fix proposed by ForgeOS Healer for issue {issue_id}.",
            )
            number = pr.get("number")
            self._log(f"opened PR #{number} for issue {issue_id}")
        except Exception as e:
            self._log(f"PR creation failed: {e}")
            return

        # Wait briefly for CI then attempt merge
        merged = self._poll_and_merge(int(number)) if number else False
        if merged:
            try:
                self.sentry.resolve_issue(issue_id)
                self._log(f"resolved Sentry issue {issue_id}")
            except Exception as e:
                self._log(f"resolve_issue failed: {e}")

    def _poll_and_merge(self, pr_number: int, attempts: int = 20) -> bool:
        for _ in range(attempts):
            time.sleep(15)
            runs = self.gh.list_workflow_runs(
                self.target.github_owner, self.target.github_repo, branch=f"healer/issue-{pr_number}"
            )
            if not runs:
                continue
            run = runs[0]
            if run.get("status") != "completed":
                continue
            if run.get("conclusion") != "success":
                self._log(f"CI failed for PR #{pr_number}; skipping auto-merge")
                return False
            try:
                self.gh.merge_pull_request(
                    self.target.github_owner, self.target.github_repo, pr_number, merge_method="squash"
                )
                self._log(f"auto-merged PR #{pr_number}")
                return True
            except Exception as e:
                self._log(f"merge failed for PR #{pr_number}: {e}")
                return False
        return False

    # ------------------------------------------------------------------
    # Uptime tick
    # ------------------------------------------------------------------

    def tick_uptime(self) -> None:
        if not self.uptime:
            return
        try:
            monitors = self.uptime.get_monitors()
        except Exception as e:
            self._log(f"uptime poll failed: {e}")
            return
        for m in monitors:
            if (
                self.target.uptime_monitor_id
                and int(m.get("id", 0)) != self.target.uptime_monitor_id
            ):
                continue
            status = int(m.get("status", 0))
            # 9 = down (per UptimeRobot status codes)
            if status == 9:
                self._handle_downtime(m)

    def _handle_downtime(self, monitor: dict[str, Any]) -> None:
        self._log(f"DOWN detected on monitor {monitor.get('id')} ({monitor.get('url')}) — restarting Railway")
        if not (self.railway and self.target.railway_service_id and self.target.railway_environment_id):
            self._log("railway not configured; cannot restart")
            return
        try:
            self.railway.restart_service(
                self.target.railway_service_id, self.target.railway_environment_id
            )
            self._log("restart_service issued")
        except Exception as e:
            self._log(f"restart_service failed: {e}")

    # ------------------------------------------------------------------
    # Logging + parsing helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] {msg}\n"
        try:
            Path(self.target.log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.target.log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass
        try:
            import sys

            sys.stderr.write(line)
        except Exception:
            pass

    @staticmethod
    def _parse_files(text: str) -> dict[str, str]:
        import re

        out: dict[str, str] = {}
        for m in re.finditer(r"```([^\n`]+)\n(.*?)```", text, re.S):
            header = m.group(1).strip()
            content = m.group(2)
            if "/" in header or header.endswith((".py", ".ts", ".tsx", ".js", ".sql", ".md")):
                out[header] = content
        return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="ForgeOS healer")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sentry-project", required=True)
    parser.add_argument("--railway-service-id", default="")
    parser.add_argument("--railway-environment-id", default="")
    parser.add_argument("--uptime-monitor-id", type=int, default=0)
    parser.add_argument("--log-path", default="HEALER_LOG.md")
    args = parser.parse_args(argv)

    target = HealerTarget(
        project_id=args.project_id,
        github_owner=args.owner,
        github_repo=args.repo,
        sentry_project=args.sentry_project,
        railway_service_id=args.railway_service_id,
        railway_environment_id=args.railway_environment_id,
        uptime_monitor_id=args.uptime_monitor_id,
        log_path=args.log_path,
    )
    Healer(target).run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
