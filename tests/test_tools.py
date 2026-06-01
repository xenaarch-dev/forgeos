"""
Tool client tests — verify request shape via monkeypatch (no network).
"""

from __future__ import annotations

from typing import Any

import pytest

from forgeos.tools import (
    GitHubClient,
    RenderClient,
    SentryClient,
    UptimeRobotClient,
    VercelClient,
    SupabaseAdminClient,
)
from forgeos.tools import (
    github as github_mod,
    render as render_mod,
    vercel as vercel_mod,
    supabase_admin as supabase_mod,
    sentry as sentry_mod,
    uptimerobot as uptime_mod,
)


@pytest.fixture
def fake_http(monkeypatch):
    captured: list[dict[str, Any]] = []

    def fake(url, method="GET", headers=None, json_body=None, params=None, **_kw):
        captured.append(
            {
                "url": url,
                "method": method,
                "headers": headers or {},
                "json_body": json_body,
                "params": params,
            }
        )
        if url.endswith("/owners"):
            return [{"owner": {"id": "owner_1"}}]
        if url.endswith("/user"):
            return {"login": "octocat"}
        if url.endswith("/getMonitors"):
            return {"monitors": []}
        return {"ok": True}

    # Patch http_request in each module's namespace directly.
    for mod in (github_mod, render_mod, vercel_mod, supabase_mod, sentry_mod, uptime_mod):
        monkeypatch.setattr(mod, "http_request", fake)
    return captured


def test_github_resolve_owner(monkeypatch, fake_http):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake")
    c = GitHubClient(token="ghp_fake")
    assert c.resolve_owner() == "octocat"
    assert any("/user" in x["url"] for x in fake_http)


def test_render_get_owner_id(monkeypatch, fake_http):
    monkeypatch.setenv("RENDER_API_KEY", "rnd_fake")
    c = RenderClient(api_key="rnd_fake")
    out = c.get_owner_id()
    assert out == "owner_1"
    assert any("/owners" in x["url"] for x in fake_http)


def test_vercel_uses_team_id(monkeypatch, fake_http):
    monkeypatch.setenv("VERCEL_TOKEN", "vc_fake")
    monkeypatch.setenv("VERCEL_TEAM_ID", "team_x")
    c = VercelClient(token="vc_fake", team_id="team_x")
    c.list_projects()
    assert fake_http[-1]["params"]["teamId"] == "team_x"


def test_sentry_lists_teams(monkeypatch, fake_http):
    monkeypatch.setenv("SENTRY_AUTH_TOKEN", "snt_fake")
    monkeypatch.setenv("SENTRY_ORG", "org")
    c = SentryClient(token="snt_fake", organization="org")
    out = c.list_teams()
    assert isinstance(out, list)
    assert "/organizations/org/teams/" in fake_http[-1]["url"]


def test_uptimerobot_post(monkeypatch, fake_http):
    monkeypatch.setenv("UPTIMEROBOT_API_KEY", "u-fake")
    c = UptimeRobotClient(api_key="u-fake")
    c.get_monitors()
    assert "/getMonitors" in fake_http[-1]["url"]
    assert fake_http[-1]["method"] == "POST"


def test_supabase_admin_lists_projects(monkeypatch, fake_http):
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "sb-fake")
    c = SupabaseAdminClient(access_token="sb-fake")
    c.list_projects()
    assert "/v1/projects" in fake_http[-1]["url"]
