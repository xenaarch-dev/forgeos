"""TDD: DatasetCollector — run logging for fine-tuning flywheel."""

from __future__ import annotations

import json
import uuid

import pytest

from dataset.collector import DatasetCollector


@pytest.fixture
def collector(tmp_path):
    return DatasetCollector(base_dir=tmp_path / "dataset")


class TestDatasetCollector:
    def test_record_run_creates_json_file(self, collector, tmp_path):
        run_id = collector.record_run({"idea": "Test idea", "success": True, "eval_score": 90})
        run_path = tmp_path / "dataset" / "runs" / f"{run_id}.json"
        assert run_path.exists()

    def test_record_run_returns_run_id_string(self, collector):
        run_id = collector.record_run({"idea": "Test"})
        assert isinstance(run_id, str)
        assert len(run_id) > 0

    def test_record_run_uses_provided_run_id(self, collector):
        custom_id = str(uuid.uuid4())
        result = collector.record_run({"run_id": custom_id, "idea": "Test"})
        assert result == custom_id

    def test_record_run_generates_run_id_when_absent(self, collector):
        run_id = collector.record_run({"idea": "No ID provided"})
        assert run_id  # non-empty string

    def test_get_run_returns_correct_data(self, collector):
        run_id = collector.record_run({"idea": "AI test", "eval_score": 85})
        data = collector.get_run(run_id)
        assert data["idea"] == "AI test"
        assert data["eval_score"] == 85

    def test_get_run_includes_run_id(self, collector):
        run_id = collector.record_run({"idea": "Test"})
        data = collector.get_run(run_id)
        assert data["run_id"] == run_id

    def test_get_run_raises_for_unknown_id(self, collector):
        with pytest.raises(FileNotFoundError):
            collector.get_run("does-not-exist")

    def test_list_runs_empty_initially(self, collector):
        assert collector.list_runs() == []

    def test_list_runs_grows_with_each_record(self, collector):
        collector.record_run({"idea": "idea 1"})
        collector.record_run({"idea": "idea 2"})
        assert len(collector.list_runs()) == 2

    def test_list_runs_contains_index_fields(self, collector):
        run_id = collector.record_run({"idea": "Test", "eval_score": 80, "success": True})
        runs = collector.list_runs()
        entry = runs[0]
        assert entry["run_id"] == run_id
        assert entry["idea"] == "Test"
        assert entry["eval_score"] == 80
        assert entry["success"] is True

    def test_get_stats_empty(self, collector):
        stats = collector.get_stats()
        assert stats["total_runs"] == 0
        assert stats["avg_score"] == 0.0
        assert stats["success_rate"] == 0.0
        assert stats["top_ideas"] == []

    def test_get_stats_total_runs(self, collector):
        for i in range(3):
            collector.record_run({"idea": f"idea {i}", "success": True, "eval_score": 80})
        assert collector.get_stats()["total_runs"] == 3

    def test_get_stats_avg_score(self, collector):
        collector.record_run({"idea": "a", "eval_score": 80, "success": True})
        collector.record_run({"idea": "b", "eval_score": 90, "success": True})
        collector.record_run({"idea": "c", "eval_score": 70, "success": False})
        stats = collector.get_stats()
        assert stats["avg_score"] == 80.0

    def test_get_stats_success_rate(self, collector):
        collector.record_run({"idea": "a", "eval_score": 80, "success": True})
        collector.record_run({"idea": "b", "eval_score": 90, "success": True})
        collector.record_run({"idea": "c", "eval_score": 70, "success": False})
        stats = collector.get_stats()
        assert round(stats["success_rate"], 2) == 0.67

    def test_get_stats_top_ideas_ordered_by_score(self, collector):
        collector.record_run({"idea": "low", "eval_score": 60, "success": True})
        collector.record_run({"idea": "high", "eval_score": 95, "success": True})
        collector.record_run({"idea": "mid", "eval_score": 80, "success": True})
        stats = collector.get_stats()
        assert stats["top_ideas"][0] == "high"

    def test_run_data_has_timestamp_added(self, collector):
        run_id = collector.record_run({"idea": "test"})
        data = collector.get_run(run_id)
        assert "timestamp" in data
        assert data["timestamp"]

    def test_record_run_preserves_provided_timestamp(self, collector):
        ts = "2026-06-02T00:00:00+00:00"
        run_id = collector.record_run({"idea": "test", "timestamp": ts})
        data = collector.get_run(run_id)
        assert data["timestamp"] == ts

    def test_index_file_is_valid_json(self, collector, tmp_path):
        collector.record_run({"idea": "test"})
        index_path = tmp_path / "dataset" / "runs_index.json"
        data = json.loads(index_path.read_text())
        assert isinstance(data, list)
        assert len(data) == 1

    def test_multiple_records_persisted_independently(self, collector):
        ids = [collector.record_run({"idea": f"idea {i}", "eval_score": i * 10}) for i in range(5)]
        for i, run_id in enumerate(ids):
            data = collector.get_run(run_id)
            assert data["eval_score"] == i * 10
