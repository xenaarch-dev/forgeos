"""
Shared pytest configuration and helpers.

Defines skip_no_claude — a pytest.mark.skipif decorator applied to any
test class that makes live Anthropic API calls.  The probe runs once per
session (lru_cache) so it never fires more than one HTTP request.
"""

from __future__ import annotations

import functools
import json
import os
import urllib.error
import urllib.request

import pytest


@functools.lru_cache(maxsize=1)
def _claude_available() -> bool:
    """Return True only when the Anthropic API accepts requests right now."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return False
    try:
        data = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


# Re-usable decorator — attach to any integration test class
skip_no_claude = pytest.mark.skipif(
    not _claude_available(),
    reason="Claude API unavailable or rate-limited — skipping integration tests",
)
