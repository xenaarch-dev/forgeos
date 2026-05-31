"""UptimeRobot v2 API client (subset used by ForgeOS)."""

from __future__ import annotations

import urllib.parse
from typing import Any

from config import TOOLS, required
from .http import http_request


class UptimeRobotClient:
    """UptimeRobot uses a form-encoded POST API rather than JSON."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or TOOLS.uptimerobot_api_key
        self.api = TOOLS.uptimerobot_api

    def _post(self, path: str, **fields: Any) -> dict[str, Any]:
        body = {
            "api_key": required("UPTIMEROBOT_API_KEY", self.api_key),
            "format": "json",
            **{k: v for k, v in fields.items() if v is not None},
        }
        encoded = urllib.parse.urlencode(body).encode("utf-8")
        return http_request(
            f"{self.api}{path}",
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            },
            raw_body=encoded,
        )

    def get_account_details(self) -> dict[str, Any]:
        return self._post("/getAccountDetails")

    def get_monitors(self, search: str | None = None) -> list[dict[str, Any]]:
        data = self._post("/getMonitors", search=search)
        return list((data or {}).get("monitors", []))

    def create_monitor(
        self,
        friendly_name: str,
        url: str,
        monitor_type: int = 1,
        interval: int = 300,
    ) -> dict[str, Any]:
        return self._post(
            "/newMonitor",
            friendly_name=friendly_name,
            url=url,
            type=monitor_type,
            interval=interval,
        )

    def delete_monitor(self, monitor_id: int) -> dict[str, Any]:
        return self._post("/deleteMonitor", id=monitor_id)


__all__ = ["UptimeRobotClient"]
