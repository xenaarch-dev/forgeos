"""
VoiceAgent — text-to-speech narrator for the ForgeOS pipeline.

Active TTS: edge-tts (free, no API key) via _tts_and_play → MP3 → mpg123.
Alternative: _tts_elevenlabs (requires ELEVENLABS_API_KEY + paid plan for
library voices) — code preserved, not the active default.

Falls back to a plain print on any error — never crashes the pipeline.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from typing import Literal


# ---------------------------------------------------------------------------
# Personality lines — one dict per agent
# ---------------------------------------------------------------------------

AGENT_VOICE_LINES: dict[str, dict[str, str]] = {
    "pm": {
        "start": "PM Agent online. Validating demand and generating spec.",
        "done":  "Spec complete. Product validated.",
        "fail":  "PM Agent blocked. Insufficient signal to proceed.",
    },
    "architect": {
        "start": "Architect online. Designing system architecture.",
        "done":  "Architecture complete. File structure committed.",
        "fail":  "Architect blocked. Spec requires clarification.",
    },
    "scaffold": {
        "start": "Scaffold running. Generating project structure.",
        "done":  "Scaffold complete. Zero placeholders.",
        "fail":  "Scaffold failed. Review spec for ambiguities.",
    },
    "security": {
        "start": "Security scan initiated.",
        "done":  "Security clear. No critical vulnerabilities.",
        "fail":  "Security blocked. Do not deploy until resolved.",
    },
    "eval": {
        "start": "Eval agent running. Checking output quality.",
        "done":  "Evaluation passed.",
        "fail":  "Evaluation failed. Output below threshold.",
    },
    "legal": {
        "start": "Legal agent running. Generating compliance documents.",
        "done":  "Legal documents generated.",
        "fail":  "Legal agent failed.",
    },
    "worker": {
        "start": "Worker loop starting. Building features.",
        "done":  "Worker loop complete. All features implemented.",
        "fail":  "Worker loop failed. Check implementation logs.",
    },
    "deploy": {
        "start": "Deploying to Render and Vercel.",
        "done":  "Product is live.",
        "fail":  "Deployment failed. Check logs.",
    },
    "pipeline": {
        "start": "ForgeOS pipeline initiated.",
        "done":  "Pipeline complete. Product is ready.",
        "fail":  "Pipeline halted. Human review required.",
    },
}

_DEFAULT_VOICE = "en-GB-RyanNeural"
_TMP_MP3 = "/tmp/forgeos_voice.mp3"


class VoiceAgent:
    """Narrates pipeline events with edge-tts + mpg123.

    Parameters
    ----------
    voice_id:
        edge-tts voice name (default path) or ElevenLabs voice ID when
        _tts_elevenlabs is the active implementation.
    silent:
        When True the agent never calls TTS or mpg123 — useful for CI and
        test environments where audio is unwanted.
    """

    def __init__(
        self,
        voice_id: str = _DEFAULT_VOICE,
        silent: bool = False,
    ) -> None:
        self.voice_id = voice_id
        self.silent = silent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def speak(self, text: str) -> None:
        """Speak *text*.  Falls back silently on any error."""
        if self.silent:
            self._fallback(text)
            return
        try:
            await self._tts_and_play(text)
        except Exception as exc:  # noqa: BLE001
            self._log(f"[VoiceAgent] TTS error ({exc!r}), using fallback")
            self._fallback(text)

    def speak_sync(self, text: str) -> None:
        """Synchronous convenience wrapper around :meth:`speak`."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already inside an event loop (e.g. Jupyter / FastAPI):
                # schedule as a fire-and-forget coroutine.
                loop.create_task(self.speak(text))
            else:
                loop.run_until_complete(self.speak(text))
        except Exception:  # noqa: BLE001
            self._fallback(text)

    def say(
        self,
        agent: str,
        event: Literal["start", "done", "fail"],
    ) -> None:
        """Look up and speak a canned voice line.

        Silently skips if *agent* or *event* is not in AGENT_VOICE_LINES.
        """
        lines = AGENT_VOICE_LINES.get(agent, {})
        text = lines.get(event, "")
        if text:
            self.speak_sync(text)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _tts_and_play(self, text: str) -> None:
        import edge_tts  # lazy import — missing package → fallback

        communicate = edge_tts.Communicate(text, self.voice_id)
        await communicate.save(_TMP_MP3)
        self._play_mp3(_TMP_MP3)

    async def _tts_elevenlabs(self, text: str) -> None:
        """ElevenLabs TTS — preserved for future swap when subscription allows.

        To activate: replace _tts_and_play body with a call to this method,
        and set voice_id to a valid ElevenLabs voice ID.
        Requires: ELEVENLABS_API_KEY env var + paid plan for library voices.
        """
        from elevenlabs import ElevenLabs  # lazy import — missing package → fallback

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set")

        client = ElevenLabs(api_key=api_key)
        audio = client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        with open(_TMP_MP3, "wb") as f:
            for chunk in audio:
                if chunk:
                    f.write(chunk)
        self._play_mp3(_TMP_MP3)

    def _play_mp3(self, path: str) -> None:
        """Launch mpg123 non-blocking.  Raises FileNotFoundError if absent."""
        subprocess.Popen(
            ["mpg123", "-q", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _fallback(self, text: str) -> None:
        print(f"🔊 [AGENT]: {text}", flush=True)

    def _log(self, msg: str) -> None:
        try:
            sys.stderr.write(msg + "\n")
            sys.stderr.flush()
        except Exception:  # noqa: BLE001
            pass


__all__ = ["VoiceAgent", "AGENT_VOICE_LINES"]
