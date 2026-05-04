"""
Minimal HTTP helper used by every API client.

Stays dependency-free (urllib only). Surfaces errors with their response
body so callers can react to API-specific error codes.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class APIError(RuntimeError):
    def __init__(self, status: int, message: str, body: str = "") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


def http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    raw_body: bytes | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 60.0,
    expect_json: bool = True,
    retries: int = 3,
    backoff: float = 1.5,
) -> Any:
    """Issue a single HTTP request with simple retries on 5xx/429."""
    if params:
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None}
        )

    body: bytes | None = None
    headers = dict(headers or {})
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif raw_body is not None:
        body = raw_body

    last_err: Exception | None = None
    delay = backoff
    for attempt in range(1, max(1, retries) + 1):
        try:
            req = urllib.request.Request(url, data=body, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if not raw:
                    return None
                if expect_json:
                    text = raw.decode("utf-8", errors="ignore")
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
                return raw
        except urllib.error.HTTPError as e:
            last_err = e
            try:
                body_text = e.read().decode("utf-8", errors="ignore")
            except Exception:
                body_text = ""
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise APIError(e.code, e.reason or "error", body_text) from e
        except urllib.error.URLError as e:
            last_err = e
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise APIError(0, str(e.reason)) from e
    if last_err:
        raise last_err  # pragma: no cover
    raise APIError(0, "unknown error")  # pragma: no cover


__all__ = ["APIError", "http_request"]
