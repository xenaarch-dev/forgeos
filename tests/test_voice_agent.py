"""Tests for VoiceAgent and AGENT_VOICE_LINES.

All tests are instant — no audio hardware or mpg123 required.
"""

from __future__ import annotations

import asyncio
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.voice_agent import AGENT_VOICE_LINES, VoiceAgent

_REQUIRED_AGENTS = {
    "pm", "architect", "scaffold", "security",
    "eval", "legal", "worker", "deploy", "pipeline",
}
_REQUIRED_EVENTS = {"start", "done", "fail"}


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestVoiceAgentInstantiation:
    def test_default_instantiation(self):
        agent = VoiceAgent()
        assert agent.voice_id == "en-GB-RyanNeural"
        assert agent.silent is False

    def test_custom_voice_id(self):
        agent = VoiceAgent(voice_id="en-US-JennyNeural")
        assert agent.voice_id == "en-US-JennyNeural"

    def test_silent_flag(self):
        agent = VoiceAgent(silent=True)
        assert agent.silent is True

    def test_instantiation_with_all_params(self):
        agent = VoiceAgent(voice_id="en-AU-NatashaNeural", silent=True)
        assert agent.voice_id == "en-AU-NatashaNeural"
        assert agent.silent is True


# ---------------------------------------------------------------------------
# Silent mode — speak() must print fallback, never call TTS
# ---------------------------------------------------------------------------

class TestSilentMode:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_speak_silent_prints_fallback(self, capsys):
        agent = VoiceAgent(silent=True)
        self._run(agent.speak("Hello world"))
        captured = capsys.readouterr()
        assert "Hello world" in captured.out
        assert "🔊 [AGENT]:" in captured.out

    def test_speak_silent_does_not_call_edge_tts(self):
        agent = VoiceAgent(silent=True)
        with patch("agents.voice_agent.VoiceAgent._tts_and_play") as mock_tts:
            self._run(agent.speak("test"))
            mock_tts.assert_not_called()

    def test_speak_sync_silent_prints_fallback(self, capsys):
        agent = VoiceAgent(silent=True)
        agent.speak_sync("Pipeline started")
        captured = capsys.readouterr()
        assert "Pipeline started" in captured.out

    def test_fallback_format(self, capsys):
        agent = VoiceAgent(silent=True)
        agent._fallback("Custom message")
        captured = capsys.readouterr()
        assert captured.out.strip() == "🔊 [AGENT]: Custom message"


# ---------------------------------------------------------------------------
# TTS error → silent fallback, never crash
# ---------------------------------------------------------------------------

class TestFallbackOnError:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_speak_falls_back_when_tts_raises(self, capsys):
        agent = VoiceAgent(silent=False)
        with patch.object(agent, "_tts_and_play", side_effect=RuntimeError("no audio")):
            self._run(agent.speak("Test fallback"))
        captured = capsys.readouterr()
        assert "Test fallback" in captured.out

    def test_speak_falls_back_when_mpg123_missing(self, capsys):
        agent = VoiceAgent(silent=False)
        with patch.object(agent, "_tts_and_play", side_effect=FileNotFoundError("mpg123")):
            self._run(agent.speak("No player"))
        captured = capsys.readouterr()
        assert "No player" in captured.out

    def test_speak_never_raises(self):
        agent = VoiceAgent(silent=False)
        with patch.object(agent, "_tts_and_play", side_effect=Exception("boom")):
            # Must not propagate
            asyncio.run(agent.speak("safe"))


# ---------------------------------------------------------------------------
# say() helper
# ---------------------------------------------------------------------------

class TestSayHelper:
    def test_say_calls_speak_sync(self):
        agent = VoiceAgent(silent=True)
        with patch.object(agent, "speak_sync") as mock_speak:
            agent.say("pm", "start")
            mock_speak.assert_called_once_with(AGENT_VOICE_LINES["pm"]["start"])

    def test_say_unknown_agent_does_not_crash(self):
        agent = VoiceAgent(silent=True)
        agent.say("nonexistent_agent", "start")  # should be silent, no exception

    def test_say_unknown_event_does_not_crash(self):
        agent = VoiceAgent(silent=True)
        agent.say("pm", "unknown_event")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AGENT_VOICE_LINES structure
# ---------------------------------------------------------------------------

class TestAgentVoiceLines:
    def test_all_required_agent_keys_present(self):
        missing = _REQUIRED_AGENTS - set(AGENT_VOICE_LINES.keys())
        assert not missing, f"Missing agent keys: {missing}"

    def test_every_agent_has_start_done_fail(self):
        for agent, lines in AGENT_VOICE_LINES.items():
            missing = _REQUIRED_EVENTS - set(lines.keys())
            assert not missing, f"Agent '{agent}' missing events: {missing}"

    def test_all_lines_are_non_empty_strings(self):
        for agent, lines in AGENT_VOICE_LINES.items():
            for event, text in lines.items():
                assert isinstance(text, str) and text.strip(), (
                    f"Empty line for {agent}.{event}"
                )

    def test_line_count(self):
        assert len(AGENT_VOICE_LINES) == len(_REQUIRED_AGENTS)
