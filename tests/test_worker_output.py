"""TDD: WorkerLoopAgent structured outputs."""

from __future__ import annotations

import pytest

from models.outputs.worker_output import WorkerOutput


class TestWorkerOutputModel:
    def test_valid_model_no_tasks(self):
        out = WorkerOutput(
            features_completed=0,
            features_total=0,
            completion_rate=1.0,
            handoffs=[],
            all_tasks_completed=False,
        )
        assert out.features_total == 0

    def test_valid_model_all_complete(self):
        out = WorkerOutput(
            features_completed=5,
            features_total=5,
            completion_rate=1.0,
            handoffs=[{"task": "backend crud"}] * 5,
            all_tasks_completed=True,
        )
        assert out.all_tasks_completed is True
        assert out.completion_rate == 1.0

    def test_valid_model_partial_complete(self):
        out = WorkerOutput(
            features_completed=3,
            features_total=5,
            completion_rate=0.6,
            handoffs=[{"task": "a"}, {"task": "b"}, {"task": "c"}],
            all_tasks_completed=False,
        )
        assert out.completion_rate == 0.6

    def test_negative_features_rejected(self):
        with pytest.raises(Exception):
            WorkerOutput(
                features_completed=-1,
                features_total=5,
                completion_rate=0.0,
                handoffs=[],
                all_tasks_completed=False,
            )

    def test_completion_rate_out_of_bounds(self):
        with pytest.raises(Exception):
            WorkerOutput(
                features_completed=5,
                features_total=5,
                completion_rate=1.1,  # > 1.0
                handoffs=[],
                all_tasks_completed=True,
            )

    def test_inconsistent_completion_rate_rejected(self):
        with pytest.raises(Exception):
            WorkerOutput(
                features_completed=3,
                features_total=5,
                completion_rate=0.8,  # should be 0.6
                handoffs=[],
                all_tasks_completed=False,
            )
