"""
Tests for daemon/drainer.py.

Covers:
  - drain_once: empty queue, successful build, failed build
  - _tg_poll: no-ops without credentials, enqueues from Telegram messages,
    respects chat_id filter, advances offset
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from daemon.queue import BuildQueue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _queue(tmp_path: Path) -> BuildQueue:
    return BuildQueue(root=tmp_path / "queue")


def _fake_tg_response(updates: list[dict]) -> bytes:
    return json.dumps({"ok": True, "result": updates}).encode("utf-8")


# ---------------------------------------------------------------------------
# drain_once
# ---------------------------------------------------------------------------

class TestDrainOnce:
    def test_returns_false_on_empty_queue(self, tmp_path):
        from daemon.drainer import drain_once
        q = _queue(tmp_path)
        assert drain_once(q) is False

    def test_returns_true_when_job_processed(self, tmp_path):
        from daemon.drainer import drain_once
        q = _queue(tmp_path)
        q.enqueue("Build a test app")

        mock_ctx = MagicMock()
        mock_ctx.project_id = "proj_test"

        with patch("daemon.drainer.HermesOrchestrator") as mock_hermes:
            mock_hermes.return_value.run.return_value = mock_ctx
            result = drain_once(q)

        assert result is True

    def test_archives_job_as_success(self, tmp_path):
        from daemon.drainer import drain_once
        q = _queue(tmp_path)
        q.enqueue("Build a test app")

        mock_ctx = MagicMock()
        mock_ctx.project_id = "proj_test"

        with patch("daemon.drainer.HermesOrchestrator") as mock_hermes:
            mock_hermes.return_value.run.return_value = mock_ctx
            drain_once(q)

        archive_files = list(q._archive.glob("*.json"))
        assert len(archive_files) == 1
        record = json.loads(archive_files[0].read_text(encoding="utf-8"))
        assert record["status"] == "success"

    def test_archives_job_as_failed_on_exception(self, tmp_path):
        from daemon.drainer import drain_once
        q = _queue(tmp_path)
        q.enqueue("Build a doomed app")

        with patch("daemon.drainer.HermesOrchestrator") as mock_hermes:
            mock_hermes.return_value.run.side_effect = RuntimeError("Gate blocked: office_hours")
            with pytest.raises(RuntimeError, match="Gate blocked"):
                drain_once(q)

        archive_files = list(q._archive.glob("*.json"))
        assert len(archive_files) == 1
        record = json.loads(archive_files[0].read_text(encoding="utf-8"))
        assert record["status"] == "failed"
        assert "Gate blocked" in record["error"]

    def test_pending_is_empty_after_drain(self, tmp_path):
        from daemon.drainer import drain_once
        q = _queue(tmp_path)
        q.enqueue("Build something")

        with patch("daemon.drainer.HermesOrchestrator") as mock_hermes:
            mock_hermes.return_value.run.return_value = MagicMock(project_id="p1")
            drain_once(q)

        assert q.pending_count() == 0

    def test_passes_idea_to_orchestrator(self, tmp_path):
        from daemon.drainer import drain_once
        q = _queue(tmp_path)
        q.enqueue("Build a recipe app")

        captured_ideas: list[str] = []

        def fake_hermes(idea: str):
            captured_ideas.append(idea)
            m = MagicMock()
            m.run.return_value = MagicMock(project_id="p1")
            return m

        with patch("daemon.drainer.HermesOrchestrator", side_effect=fake_hermes):
            drain_once(q)

        assert captured_ideas == ["Build a recipe app"]

    def test_only_one_job_processed_per_call(self, tmp_path):
        from daemon.drainer import drain_once
        q = _queue(tmp_path)
        q.enqueue("Job 1")
        q.enqueue("Job 2")

        with patch("daemon.drainer.HermesOrchestrator") as mock_hermes:
            mock_hermes.return_value.run.return_value = MagicMock(project_id="p1")
            drain_once(q)

        assert q.pending_count() == 1


# ---------------------------------------------------------------------------
# _tg_poll — no credentials
# ---------------------------------------------------------------------------

class TestTgPollNoCreds:
    def test_returns_zero_without_token(self, tmp_path, monkeypatch):
        from daemon.drainer import _tg_poll
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        q = _queue(tmp_path)
        assert _tg_poll(q) == 0

    def test_returns_zero_without_chat_id(self, tmp_path, monkeypatch):
        from daemon.drainer import _tg_poll
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        q = _queue(tmp_path)
        assert _tg_poll(q) == 0

    def test_no_queue_entries_without_creds(self, tmp_path, monkeypatch):
        from daemon.drainer import _tg_poll
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        q = _queue(tmp_path)
        _tg_poll(q)
        assert q.pending_count() == 0


# ---------------------------------------------------------------------------
# _tg_poll — with credentials (HTTP mocked)
# ---------------------------------------------------------------------------

class TestTgPollWithCreds:
    def _setup_env(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token-123")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "99999")

    def _make_update(self, update_id: int, text: str, chat_id: int = 99999) -> dict:
        return {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "chat": {"id": chat_id, "type": "private"},
                "text": text,
            },
        }

    def test_enqueues_message_as_build_idea(self, tmp_path, monkeypatch):
        from daemon import drainer
        self._setup_env(monkeypatch)
        monkeypatch.setattr(drainer, "_STATE_DIR", tmp_path / "state")
        monkeypatch.setattr(drainer, "_TG_OFFSET_FILE", tmp_path / "state" / "offset.txt")

        updates = [self._make_update(1, "Build a habit tracker")]
        q = _queue(tmp_path)

        with patch("daemon.drainer._fetch_updates", return_value=updates):
            count = drainer._tg_poll(q)

        assert count == 1
        assert q.pending_count() == 1
        job = q.pop_next()
        assert job is not None
        assert job["idea"] == "Build a habit tracker"
        assert job["source"] == "telegram"

    def test_enqueues_multiple_messages(self, tmp_path, monkeypatch):
        from daemon import drainer
        self._setup_env(monkeypatch)
        monkeypatch.setattr(drainer, "_STATE_DIR", tmp_path / "state")
        monkeypatch.setattr(drainer, "_TG_OFFSET_FILE", tmp_path / "state" / "offset.txt")

        updates = [
            self._make_update(1, "Build a SaaS"),
            self._make_update(2, "Build a game"),
        ]
        q = _queue(tmp_path)

        with patch("daemon.drainer._fetch_updates", return_value=updates):
            count = drainer._tg_poll(q)

        assert count == 2
        assert q.pending_count() == 2

    def test_ignores_messages_from_other_chats(self, tmp_path, monkeypatch):
        from daemon import drainer
        self._setup_env(monkeypatch)
        monkeypatch.setattr(drainer, "_STATE_DIR", tmp_path / "state")
        monkeypatch.setattr(drainer, "_TG_OFFSET_FILE", tmp_path / "state" / "offset.txt")

        updates = [self._make_update(1, "Build X", chat_id=11111)]  # wrong chat
        q = _queue(tmp_path)

        with patch("daemon.drainer._fetch_updates", return_value=updates):
            count = drainer._tg_poll(q)

        assert count == 0
        assert q.pending_count() == 0

    def test_ignores_empty_text_messages(self, tmp_path, monkeypatch):
        from daemon import drainer
        self._setup_env(monkeypatch)
        monkeypatch.setattr(drainer, "_STATE_DIR", tmp_path / "state")
        monkeypatch.setattr(drainer, "_TG_OFFSET_FILE", tmp_path / "state" / "offset.txt")

        updates = [self._make_update(1, "")]  # empty text
        q = _queue(tmp_path)

        with patch("daemon.drainer._fetch_updates", return_value=updates):
            count = drainer._tg_poll(q)

        assert count == 0

    def test_advances_offset_after_poll(self, tmp_path, monkeypatch):
        from daemon import drainer
        offset_file = tmp_path / "state" / "offset.txt"
        monkeypatch.setattr(drainer, "_STATE_DIR", tmp_path / "state")
        monkeypatch.setattr(drainer, "_TG_OFFSET_FILE", offset_file)
        self._setup_env(monkeypatch)

        updates = [self._make_update(42, "Build something")]
        q = _queue(tmp_path)

        with patch("daemon.drainer._fetch_updates", return_value=updates):
            drainer._tg_poll(q)

        assert offset_file.exists()
        assert int(offset_file.read_text(encoding="utf-8").strip()) == 43  # update_id + 1

    def test_returns_zero_on_network_failure(self, tmp_path, monkeypatch):
        from daemon import drainer
        self._setup_env(monkeypatch)
        monkeypatch.setattr(drainer, "_STATE_DIR", tmp_path / "state")
        monkeypatch.setattr(drainer, "_TG_OFFSET_FILE", tmp_path / "state" / "offset.txt")

        q = _queue(tmp_path)
        with patch("daemon.drainer._fetch_updates", return_value=None):
            count = drainer._tg_poll(q)

        assert count == 0
        assert q.pending_count() == 0
