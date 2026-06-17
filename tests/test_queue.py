"""
Tests for BuildQueue.

Validates FIFO ordering, enqueue/pop/archive lifecycle, and
edge cases (empty queue, corrupted files, error truncation).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from daemon.queue import BuildQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def queue(tmp_path: Path) -> BuildQueue:
    return BuildQueue(root=tmp_path / "queue")


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------

class TestEnqueue:
    def test_creates_pending_file(self, queue: BuildQueue):
        job_id = queue.enqueue("Build a habit tracker")
        files = list((queue._pending).glob("*.json"))
        assert len(files) == 1
        assert files[0].stem == job_id

    def test_job_file_contains_idea(self, queue: BuildQueue):
        queue.enqueue("Build a habit tracker")
        path = sorted(queue._pending.glob("*.json"))[0]
        job = json.loads(path.read_text(encoding="utf-8"))
        assert job["idea"] == "Build a habit tracker"

    def test_job_status_is_pending(self, queue: BuildQueue):
        queue.enqueue("Build X")
        path = sorted(queue._pending.glob("*.json"))[0]
        job = json.loads(path.read_text(encoding="utf-8"))
        assert job["status"] == "pending"

    def test_source_default_is_manual(self, queue: BuildQueue):
        queue.enqueue("Build X")
        path = sorted(queue._pending.glob("*.json"))[0]
        job = json.loads(path.read_text(encoding="utf-8"))
        assert job["source"] == "manual"

    def test_source_overridable(self, queue: BuildQueue):
        queue.enqueue("Build X", source="telegram")
        path = sorted(queue._pending.glob("*.json"))[0]
        job = json.loads(path.read_text(encoding="utf-8"))
        assert job["source"] == "telegram"

    def test_returns_unique_ids(self, queue: BuildQueue):
        ids = [queue.enqueue(f"idea {i}") for i in range(5)]
        assert len(set(ids)) == 5

    def test_job_has_queued_at_timestamp(self, queue: BuildQueue):
        queue.enqueue("Build X")
        path = sorted(queue._pending.glob("*.json"))[0]
        job = json.loads(path.read_text(encoding="utf-8"))
        assert "queued_at" in job
        assert "T" in job["queued_at"]  # ISO 8601


# ---------------------------------------------------------------------------
# Pop
# ---------------------------------------------------------------------------

class TestPopNext:
    def test_returns_none_when_empty(self, queue: BuildQueue):
        assert queue.pop_next() is None

    def test_returns_job_dict(self, queue: BuildQueue):
        queue.enqueue("Build Y")
        job = queue.pop_next()
        assert job is not None
        assert job["idea"] == "Build Y"

    def test_removes_file_from_pending(self, queue: BuildQueue):
        queue.enqueue("Build Y")
        queue.pop_next()
        assert queue.pending_count() == 0

    def test_fifo_order_two_jobs(self, queue: BuildQueue):
        queue.enqueue("First idea")
        time.sleep(0.01)  # ensure distinct timestamps
        queue.enqueue("Second idea")
        first = queue.pop_next()
        assert first is not None
        assert first["idea"] == "First idea"

    def test_fifo_order_three_jobs(self, queue: BuildQueue):
        ideas = ["Alpha", "Beta", "Gamma"]
        for idea in ideas:
            queue.enqueue(idea)
            time.sleep(0.01)
        popped = [queue.pop_next()["idea"] for _ in range(3)]  # type: ignore[index]
        assert popped == ideas

    def test_returns_none_after_draining(self, queue: BuildQueue):
        queue.enqueue("Only job")
        queue.pop_next()
        assert queue.pop_next() is None

    def test_handles_corrupted_file_gracefully(self, queue: BuildQueue):
        bad = queue._pending / "20260101T000000_bad.json"
        bad.write_text("not json", encoding="utf-8")
        result = queue.pop_next()
        assert result is None
        assert not bad.exists()  # corrupted file is removed


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

class TestArchive:
    def test_writes_to_archive_dir(self, queue: BuildQueue):
        queue.enqueue("Build Z")
        job = queue.pop_next()
        assert job is not None
        queue.archive(job, status="success")
        files = list(queue._archive.glob("*.json"))
        assert len(files) == 1

    def test_archive_contains_completed_at(self, queue: BuildQueue):
        queue.enqueue("Build Z")
        job = queue.pop_next()
        assert job is not None
        queue.archive(job, status="success")
        path = sorted(queue._archive.glob("*.json"))[0]
        record = json.loads(path.read_text(encoding="utf-8"))
        assert "completed_at" in record

    def test_archive_status_success(self, queue: BuildQueue):
        queue.enqueue("Build Z")
        job = queue.pop_next()
        assert job is not None
        queue.archive(job, status="success")
        path = sorted(queue._archive.glob("*.json"))[0]
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["status"] == "success"

    def test_archive_status_failed_with_error(self, queue: BuildQueue):
        queue.enqueue("Build Z")
        job = queue.pop_next()
        assert job is not None
        queue.archive(job, status="failed", error="Gate blocked")
        path = sorted(queue._archive.glob("*.json"))[0]
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["status"] == "failed"
        assert "Gate blocked" in record["error"]

    def test_error_truncated_to_2000_chars(self, queue: BuildQueue):
        queue.enqueue("Build Z")
        job = queue.pop_next()
        assert job is not None
        long_error = "x" * 3000
        queue.archive(job, status="failed", error=long_error)
        path = sorted(queue._archive.glob("*.json"))[0]
        record = json.loads(path.read_text(encoding="utf-8"))
        assert len(record["error"]) <= 2000

    def test_pending_does_not_reappear_after_archive(self, queue: BuildQueue):
        queue.enqueue("Build Z")
        job = queue.pop_next()
        assert job is not None
        queue.archive(job, status="success")
        assert queue.pop_next() is None


# ---------------------------------------------------------------------------
# List pending / count
# ---------------------------------------------------------------------------

class TestListPending:
    def test_empty_queue(self, queue: BuildQueue):
        assert queue.list_pending() == []
        assert queue.pending_count() == 0

    def test_lists_all_pending(self, queue: BuildQueue):
        for i in range(3):
            queue.enqueue(f"Idea {i}")
        pending = queue.list_pending()
        assert len(pending) == 3

    def test_pending_count_matches_list_length(self, queue: BuildQueue):
        queue.enqueue("A")
        queue.enqueue("B")
        assert queue.pending_count() == len(queue.list_pending())

    def test_list_pending_in_fifo_order(self, queue: BuildQueue):
        for idea in ["First", "Second", "Third"]:
            queue.enqueue(idea)
            time.sleep(0.01)
        ideas = [j["idea"] for j in queue.list_pending()]
        assert ideas == ["First", "Second", "Third"]
