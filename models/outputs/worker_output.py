"""Pydantic output model for mission WorkerLoopAgent structured outputs."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorkerOutput(BaseModel):
    """Validated output from WorkerLoopAgent (mission/worker.py).

    WorkerAgent has the highest LLM call volume in ForgeOS — it runs
    one LLM session per coder task. Structured output validates that
    completion data is trustworthy before downstream gates use it.
    """

    model_config = ConfigDict(extra="ignore")

    features_completed: int = Field(..., ge=0, description="Number of coder tasks completed successfully")
    features_total: int = Field(..., ge=0, description="Total coder tasks attempted")
    completion_rate: float = Field(..., ge=0.0, le=1.0, description="features_completed / features_total, or 1.0 if no tasks")
    handoffs: List[Dict[str, Any]] = Field(default_factory=list, description="Handoff records from each completed task")
    all_tasks_completed: bool = Field(..., description="True when features_completed == features_total and features_total > 0")

    @model_validator(mode="after")
    def validate_completion_rate_consistency(self) -> "WorkerOutput":
        if self.features_total > 0:
            expected = round(self.features_completed / self.features_total, 4)
            actual = round(self.completion_rate, 4)
            if abs(expected - actual) > 0.01:
                raise ValueError(
                    f"completion_rate {self.completion_rate} inconsistent with "
                    f"{self.features_completed}/{self.features_total}"
                )
        return self
