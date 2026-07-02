"""
ModelRouter v2 — unit tests.

Tests confirm:
  - Tier 1 (GLM-5.2) is the default when GLM_API_KEY is set.
  - Tier 3 (Fable-5) activates only when FORGEOS_FRONTIER_TIER=true
    AND task_type is in _FRONTIER_TASK_TYPES.
  - Missing GLM_API_KEY emits a clear warning and falls through to Tier 2.
  - FORGEOS_OFFLINE_MODE=true routes to OllamaClient.
  - qwen2.5-coder:7b is NOT selected for any non-offline task.
  - ModelRouter.get_model() returns frontier model when flag is set.
"""

from __future__ import annotations

import importlib
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

import llm.router as _router_module


# ---------------------------------------------------------------------------
# Helpers — reload the module with specific env vars
# ---------------------------------------------------------------------------


def _router(env: dict):
    """Return the router module with a fresh LLM config baked in from env."""
    with patch.dict("os.environ", env, clear=False):
        # Force config to re-read env by reimporting config and router.
        import config as _cfg_mod
        import importlib as _il
        _il.reload(_cfg_mod)
        _il.reload(_router_module)
        from llm.router import _select_chain, _is_available, _build, route
        return _select_chain, _is_available, _build, route


# ---------------------------------------------------------------------------
# _select_chain — tier selection
# ---------------------------------------------------------------------------


class TestSelectChain:
    def test_offline_mode_returns_offline_stack(self):
        with patch.dict("os.environ", {"FORGEOS_OFFLINE_MODE": "true"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _select_chain, _OFFLINE_STACK
            assert _select_chain("hard", "architecture") == _OFFLINE_STACK
            assert _select_chain("low", "code") == _OFFLINE_STACK

    def test_frontier_flag_off_architecture_gets_hard_stack(self):
        with patch.dict("os.environ", {"FORGEOS_FRONTIER_TIER": "false", "FORGEOS_OFFLINE_MODE": "false"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _select_chain, _HARD_STACK
            assert _select_chain("hard", "architecture") == _HARD_STACK

    def test_frontier_flag_on_architecture_gets_frontier_stack(self):
        with patch.dict("os.environ", {"FORGEOS_FRONTIER_TIER": "true", "FORGEOS_OFFLINE_MODE": "false"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _select_chain, _FRONTIER_STACK
            assert _select_chain("hard", "architecture") == _FRONTIER_STACK

    def test_frontier_flag_on_security_gets_frontier_stack(self):
        with patch.dict("os.environ", {"FORGEOS_FRONTIER_TIER": "true", "FORGEOS_OFFLINE_MODE": "false"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _select_chain, _FRONTIER_STACK
            assert _select_chain("hard", "security") == _FRONTIER_STACK

    def test_frontier_flag_on_review_does_not_get_frontier_stack(self):
        """CSOGate uses task_type='security' not 'review'; plain review never gets Fable-5."""
        with patch.dict("os.environ", {"FORGEOS_FRONTIER_TIER": "true", "FORGEOS_OFFLINE_MODE": "false"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _select_chain, _FRONTIER_STACK, _MEDIUM_STACK
            chain = _select_chain("medium", "review")
            assert chain != _FRONTIER_STACK
            assert chain == _MEDIUM_STACK

    def test_low_tasks_use_medium_stack(self):
        with patch.dict("os.environ", {"FORGEOS_FRONTIER_TIER": "false", "FORGEOS_OFFLINE_MODE": "false"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _select_chain, _LOW_STACK
            assert _select_chain("low", "code") == _LOW_STACK


# ---------------------------------------------------------------------------
# _is_available — availability + warning
# ---------------------------------------------------------------------------


class TestIsAvailable:
    def test_glm52_available_when_key_set(self):
        with patch.dict("os.environ", {"GLM_API_KEY": "test-key"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _is_available
            assert _is_available("glm52") is True

    def test_glm52_unavailable_when_key_missing_and_warns(self, capsys):
        env = dict(os.environ)
        env.pop("GLM_API_KEY", None)
        with patch.dict("os.environ", env, clear=True):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _is_available
            result = _is_available("glm52")
        assert result is False
        captured = capsys.readouterr()
        assert "GLM_API_KEY" in captured.err
        assert "WARNING" in captured.err

    def test_fable5_available_when_anthropic_key_set(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _is_available
            assert _is_available("fable5") is True

    def test_ollama_always_available(self):
        import importlib; import config; importlib.reload(config)
        importlib.reload(_router_module)
        from llm.router import _is_available
        assert _is_available("ollama") is True


import os


# ---------------------------------------------------------------------------
# complete() — GLM call failure warning (Task 1 gap)
# ---------------------------------------------------------------------------


class TestCompleteGLMCallFailure:
    """When GLM_API_KEY is set but the API call raises, a WARNING must be logged.
    Silently falling back to Sonnet without logging was the original Task 1 gap."""

    def test_glm_call_failure_logs_warning_and_falls_back_to_sonnet(self, caplog):
        fake_resp = MagicMock()
        fake_resp.model = "claude-sonnet-4-6"
        fake_resp.prompt_tokens = 10
        fake_resp.completion_tokens = 5
        fake_resp.cost_usd = 0.0

        env = {
            "GLM_API_KEY": "sk-or-v1-test",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "FORGEOS_OFFLINE_MODE": "false",
            "FORGEOS_FRONTIER_TIER": "false",
        }
        with patch.dict("os.environ", env, clear=False):
            import config; importlib.reload(config)
            import llm.glm; importlib.reload(llm.glm)
            importlib.reload(_router_module)

            with patch("llm.glm.GLMClient.complete", side_effect=_router_module.LLMError("network timeout")), \
                 patch("llm.claude.ClaudeClient.complete", return_value=fake_resp), \
                 caplog.at_level(logging.WARNING, logger="llm.router"):
                from llm.router import complete as _c
                result = _c(user="ping", stream=False)

        assert result is fake_resp, "Expected Sonnet fallback response"
        warns = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warns, "No WARNING logged when GLM call failed — silent fallback is the bug"
        assert any("GLM" in r.message for r in warns), "Warning should mention GLM"
        assert any("fall" in r.message.lower() for r in warns), "Warning should mention fallback"


# ---------------------------------------------------------------------------
# _build — correct client types
# ---------------------------------------------------------------------------


class TestBuild:
    def test_fable5_builds_claude_client_with_correct_model(self):
        import importlib; import config; importlib.reload(config)
        importlib.reload(_router_module)
        from llm.router import _build
        from llm.claude import ClaudeClient
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _build, _FABLE5
            client = _build("fable5")
            assert isinstance(client, ClaudeClient)
            assert client.model == _FABLE5

    def test_glm52_builds_glm_client(self):
        with patch.dict("os.environ", {"GLM_API_KEY": "test-key"}, clear=False):
            import importlib
            import config; importlib.reload(config)
            import llm.glm; importlib.reload(llm.glm)
            importlib.reload(_router_module)
            from llm.router import _build
            from llm.glm import GLMClient
            client = _build("glm52")
            assert isinstance(client, GLMClient)

    def test_claude_sonnet_builds_claude_client(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import _build, _SONNET
            from llm.claude import ClaudeClient
            client = _build("claude-sonnet")
            assert isinstance(client, ClaudeClient)
            assert client.model == _SONNET

    def test_offline_builds_ollama_client(self):
        import importlib; import config; importlib.reload(config)
        importlib.reload(_router_module)
        from llm.router import _build
        from llm.ollama import OllamaClient
        client = _build("ollama")
        assert isinstance(client, OllamaClient)


# ---------------------------------------------------------------------------
# ModelRouter.get_model — YAML + frontier flag
# ---------------------------------------------------------------------------


class TestModelRouterGetModel:
    def _get_router(self, env: dict):
        with patch.dict("os.environ", env, clear=False):
            import importlib; import config; importlib.reload(config)
            importlib.reload(_router_module)
            from llm.router import ModelRouter
            return ModelRouter()

    def test_default_stage_returns_glm(self):
        r = self._get_router({"FORGEOS_FRONTIER_TIER": "false"})
        model = r.get_model("scaffold")
        assert "glm" in model.lower() or "zhipuai" in model.lower()

    def test_architect_returns_glm_without_frontier(self):
        r = self._get_router({"FORGEOS_FRONTIER_TIER": "false"})
        model = r.get_model("architect")
        assert "fable" not in model.lower()

    def test_architect_returns_fable5_with_frontier(self):
        r = self._get_router({"FORGEOS_FRONTIER_TIER": "true"})
        model = r.get_model("architect")
        assert model == "claude-fable-5"

    def test_security_returns_fable5_with_frontier(self):
        r = self._get_router({"FORGEOS_FRONTIER_TIER": "true"})
        model = r.get_model("security")
        assert model == "claude-fable-5"

    def test_cso_gate_returns_fable5_with_frontier(self):
        r = self._get_router({"FORGEOS_FRONTIER_TIER": "true"})
        model = r.get_model("cso_gate")
        assert model == "claude-fable-5"

    def test_legal_returns_sonnet_regardless_of_frontier(self):
        for flag in ("true", "false"):
            r = self._get_router({"FORGEOS_FRONTIER_TIER": flag})
            model = r.get_model("legal")
            assert model == "claude-sonnet-4-6"

    def test_gbrain_index_returns_ollama(self):
        r = self._get_router({"FORGEOS_FRONTIER_TIER": "false"})
        model = r.get_model("gbrain_index")
        assert "qwen" in model.lower() or "ollama" in model.lower()

    def test_qwen_not_returned_for_default_stages(self):
        """qwen2.5-coder:7b must not appear for non-index stages."""
        r = self._get_router({"FORGEOS_FRONTIER_TIER": "false"})
        for stage in ("scaffold", "worker", "validator", "pm_agent", "eval_agent", "architect", "default"):
            model = r.get_model(stage)
            assert "qwen" not in model.lower(), f"qwen leaked into stage={stage}: {model}"
