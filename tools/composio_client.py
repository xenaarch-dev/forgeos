"""
Composio client for ForgeOS.

Provides unified tool access for GitHub, Supabase, and Sentry via Composio.
Falls back to direct API calls when COMPOSIO_API_KEY is not set.
"""

from __future__ import annotations

import os
from typing import Any


def _has_composio() -> bool:
    return bool(os.environ.get("COMPOSIO_API_KEY"))


def _get_toolset() -> Any | None:
    if not _has_composio():
        return None
    try:
        from composio_claude import ComposioToolSet
        return ComposioToolSet()
    except Exception:
        return None


def get_tools(app_name: str) -> list[Any]:
    """Return Composio tools for the given app, or empty list if unavailable."""
    toolset = _get_toolset()
    if toolset is None:
        return []
    try:
        from composio_claude import App
        mapping = {
            "github": App.GITHUB,
            "supabase": App.SUPABASE,
            "sentry": App.SENTRY,
        }
        app = mapping.get(app_name.lower())
        if app is None:
            return []
        return list(toolset.get_tools(apps=[app]))
    except Exception:
        return []


__all__ = ["get_tools"]
