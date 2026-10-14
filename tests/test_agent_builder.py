"""Agent Builder: spec validation, catalog, store, runtime, export and API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api
from agent_builder import AgentSpec, AgentStore, AgentStoreError, resolve, validate_spec
from agent_builder.catalog import catalog_payload, skills
from agent_builder.runtime import (
    TASK_KEY,
    build_agent_class,
    compose_system_prompt,
    export_bundle,
)
from forge_sdk.agent import ForgeAgent
from models import AgentStatus, LLMResponse, ProjectContext


def _spec(**over) -> AgentSpec:
    base = dict(
        slug="test-pilot",
        name="Test Pilot",
        role="Writes and runs tests for every feature.",
        instructions="Prefer Playwright for flows.",
        model_tier="fast",
        skills=["test-writer"],
        tools=["workspace"],
        plugins=["qa-kit"],
        suit_color="#f2a65a",
        prop="clipboard",
    )
    base.update(over)
    return AgentSpec.model_validate(base)


# ---------------------------------------------------------------- spec


class TestSpec:
    def test_valid_spec_normalises_colour(self):
        assert _spec().suit_color == "#F2A65A"

    @pytest.mark.parametrize("slug", ["Bad", "1abc", "a", "has space", "x" * 50, "../etc"])
    def test_rejects_bad_slugs(self, slug):
        with pytest.raises(ValueError):
            _spec(slug=slug)

    def test_rejects_bad_colour(self):
        with pytest.raises(ValueError):
            _spec(suit_color="blue")

    def test_rejects_unknown_fields(self):
        with pytest.raises(ValueError):
            AgentSpec.model_validate({**_spec().model_dump(), "shell": "rm -rf /"})

    def test_dedupes_selections(self):
        assert _spec(skills=["test-writer", "test-writer"]).skills == ["test-writer"]

    def test_model_tier_maps_to_router_strings(self):
        assert [_spec(model_tier=t).model_tier.task_complexity for t in ("fast", "balanced", "deep")] == [
            "low", "medium", "hard",
        ]

    def test_stdio_mcp_needs_command(self):
        with pytest.raises(ValueError):
            _spec(mcp_servers=[{"name": "x", "transport": "stdio"}])

    def test_http_mcp_needs_https(self):
        with pytest.raises(ValueError):
            _spec(mcp_servers=[{"name": "x", "transport": "http", "url": "http://insecure"}])

    def test_mcp_env_takes_names_not_values(self):
        with pytest.raises(ValueError):
            _spec(mcp_servers=[{"name": "x", "command": "npx", "env": ["sk-ant-secret"]}])

    def test_duplicate_mcp_names_rejected(self):
        server = {"name": "dup", "command": "npx"}
        with pytest.raises(ValueError):
            _spec(mcp_servers=[server, server])


# ---------------------------------------------------------------- catalog


class TestCatalog:
    def test_bundled_skills_load(self):
        loaded = skills()
        for skill_id in ("clean-room-analyst", "spec-writer", "code-reviewer", "test-writer", "india-compliance"):
            assert skill_id in loaded
            assert loaded[skill_id].description
            assert loaded[skill_id].body

    def test_repo_claude_skills_are_included(self):
        assert "security-audit" in skills()

    def test_every_plugin_reference_resolves(self):
        payload = catalog_payload()
        skill_ids = {s["id"] for s in payload["skills"]}
        tool_ids = {t["id"] for t in payload["tools"]}
        mcp_names = {m["name"] for m in payload["mcp_presets"]}
        for plugin in payload["plugins"]:
            assert set(plugin["skills"]) <= skill_ids, plugin["id"]
            assert set(plugin["tools"]) <= tool_ids, plugin["id"]
            assert set(plugin["mcp"]) <= mcp_names, plugin["id"]

    def test_every_tool_module_exists(self):
        root = Path(api.__file__).parent
        for tool in catalog_payload()["tools"]:
            module_path = root / (tool["module"].replace(".", "/") + ".py")
            assert module_path.exists(), tool["module"]

    def test_validate_flags_unknowns(self):
        problems = validate_spec(_spec(skills=["nope"], tools=["nada"], plugins=["zilch"]))
        assert problems == ["unknown skill: nope", "unknown tool: nada", "unknown plugin: zilch"]

    def test_resolve_expands_plugins_without_duplicates(self):
        resolved = resolve(_spec())
        assert [s.id for s in resolved.skills] == ["test-writer", "code-reviewer"]
        assert [t.id for t in resolved.tools] == ["workspace", "browser"]
        assert [m.name for m in resolved.mcp_servers] == ["playwright"]

    def test_clean_room_skill_refuses_paywall_bypass(self):
        body = skills()["clean-room-analyst"].body.lower()
        assert "paywall" in body and "drm" in body


# ---------------------------------------------------------------- store


class TestStore:
    def test_crud_round_trip(self, tmp_path):
        store = AgentStore(tmp_path)
        store.save("alice", _spec(), create=True)
        assert store.get("alice", "test-pilot").name == "Test Pilot"
        store.save("alice", _spec(name="Test Pilot 2"), create=False)
        assert [s.name for s in store.list("alice")] == ["Test Pilot 2"]
        assert store.delete("alice", "test-pilot") is True
        assert store.list("alice") == []

    def test_owners_are_isolated(self, tmp_path):
        store = AgentStore(tmp_path)
        store.save("alice", _spec(), create=True)
        assert store.get("bob", "test-pilot") is None

    def test_odd_owner_ids_cannot_escape_root(self, tmp_path):
        store = AgentStore(tmp_path / "root")
        store.save("../../evil", _spec(), create=True)
        written = list((tmp_path / "root").rglob("*.json"))
        assert len(written) == 1 and written[0].is_relative_to(tmp_path / "root")

    def test_create_refuses_overwrite_and_update_needs_existing(self, tmp_path):
        store = AgentStore(tmp_path)
        store.save("a", _spec(), create=True)
        with pytest.raises(AgentStoreError):
            store.save("a", _spec(), create=True)
        with pytest.raises(AgentStoreError):
            store.save("a", _spec(slug="other"), create=False)

    def test_broken_file_is_skipped(self, tmp_path):
        store = AgentStore(tmp_path)
        store.save("a", _spec(), create=True)
        (tmp_path / "a" / "broken.json").write_text("{not json")
        assert [s.slug for s in store.list("a")] == ["test-pilot"]


# ---------------------------------------------------------------- runtime


class TestRuntime:
    def test_builds_a_forge_agent(self):
        cls = build_agent_class(_spec())
        assert issubclass(cls, ForgeAgent)
        assert cls.name == "test-pilot"
        assert cls.__name__ == "TestPilotAgent"
        assert cls.tools == ["workspace", "browser"]

    def test_prompt_contains_role_instructions_skills_and_tool_state(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        prompt = compose_system_prompt(_spec(tools=["github"]))
        assert "Writes and runs tests" in prompt
        assert "Prefer Playwright" in prompt
        assert "## Skill: test-writer" in prompt
        assert "not configured (needs GITHUB_TOKEN)" in prompt

    def test_run_calls_llm_with_tier_and_writes_artifact(self, tmp_path, monkeypatch):
        calls = {}

        def fake_complete(**kwargs):
            calls.update(kwargs)
            return LLMResponse(text="# Plan\nAll green.", model="fake-model")

        monkeypatch.setattr("agents.base.llm_complete", fake_complete)
        ctx = ProjectContext.new(idea="ignored", workdir=tmp_path, build_id="b1")
        ctx.metadata[TASK_KEY] = "Write tests for login"
        result = build_agent_class(_spec(model_tier="deep"))().run(ctx)

        assert result.status == AgentStatus.SUCCESS.value
        assert calls["user"] == "Write tests for login"
        assert calls["task_complexity"] == "hard"
        assert (tmp_path / "agents/test-pilot/OUTPUT.md").read_text() == "# Plan\nAll green."

    def test_export_bundle(self):
        bundle = export_bundle(_spec())
        md = bundle["files"][".claude/agents/test-pilot.md"]
        assert md.startswith("---\nname: test-pilot\n")
        assert "model: haiku" in md
        assert bundle["mcp"] == {"mcpServers": {"playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]}}}

    def test_export_env_uses_placeholders(self):
        bundle = export_bundle(_spec(plugins=["india-stack"], skills=[]))
        assert bundle["mcp"]["mcpServers"]["supabase"]["env"] == {
            "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
        }


# ---------------------------------------------------------------- API


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MESH_ALLOW_UNAUTH", "true")
    monkeypatch.setattr(api, "_agent_store", AgentStore(tmp_path / "agents"))
    api._rate_limiter.reset()
    return TestClient(api.app)


class TestApi:
    def test_catalog(self, client):
        body = client.get("/agent-builder/catalog").json()
        assert {"skills", "tools", "mcp_presets", "plugins", "model_tiers", "props"} <= set(body)

    def test_create_get_update_delete(self, client):
        payload = _spec().model_dump(mode="json")
        assert client.post("/agents/custom", json=payload).status_code == 201
        assert client.post("/agents/custom", json=payload).status_code == 409
        assert client.get("/agents/custom/test-pilot").json()["name"] == "Test Pilot"
        updated = client.post("/agents/custom/test-pilot", json={**payload, "name": "Renamed"})
        assert updated.json()["name"] == "Renamed"
        assert [a["slug"] for a in client.get("/agents/custom").json()] == ["test-pilot"]
        assert client.post("/agents/custom/test-pilot/delete").status_code == 204
        assert client.get("/agents/custom/test-pilot").status_code == 404

    def test_unknown_catalog_reference_is_422(self, client):
        payload = _spec().model_dump(mode="json") | {"skills": ["made-up"]}
        resp = client.post("/agents/custom", json=payload)
        assert resp.status_code == 422 and "unknown skill" in resp.json()["detail"]

    def test_invalid_spec_is_422(self, client):
        assert client.post("/agents/custom", json={"slug": "x"}).status_code == 422

    def test_update_cannot_rename_slug(self, client):
        payload = _spec().model_dump(mode="json")
        client.post("/agents/custom", json=payload)
        resp = client.post("/agents/custom/test-pilot", json={**payload, "slug": "other"})
        assert resp.json()["slug"] == "test-pilot"
        assert client.get("/agents/custom/other").status_code == 404

    def test_export(self, client):
        client.post("/agents/custom", json=_spec().model_dump(mode="json"))
        body = client.get("/agents/custom/test-pilot/export").json()
        assert ".claude/agents/test-pilot.md" in body["files"]

    def test_run(self, client, monkeypatch):
        monkeypatch.setattr(
            "agents.base.llm_complete",
            lambda **kw: LLMResponse(text="done: " + kw["user"], model="fake"),
        )
        client.post("/agents/custom", json=_spec().model_dump(mode="json"))
        body = client.post("/agents/custom/test-pilot/run", json={"task": "check login"}).json()
        assert body["status"] == "success"
        assert body["output"] == "done: check login"

    def test_requires_auth_when_enforced(self, client, monkeypatch):
        monkeypatch.setenv("MESH_ALLOW_UNAUTH", "false")
        assert client.get("/agents/custom").status_code == 401
