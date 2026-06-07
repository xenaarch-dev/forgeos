"""Pydantic output model for PMAgent — Stage 0 demand validation."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompetitorInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1)
    weakness: str = Field(..., min_length=1)
    opportunity: str = Field(..., min_length=1)


class PMOutput(BaseModel):
    """Validated demand research output. build_recommendation gates the pipeline."""

    model_config = ConfigDict(extra="ignore")

    product_name: str = Field(..., min_length=1)
    top_3_competitors: List[CompetitorInfo] = Field(..., min_length=3, max_length=3)
    target_user_persona: str = Field(..., min_length=100)
    demand_signals: List[str] = Field(..., min_length=3)
    recommended_price_inr: int = Field(..., gt=0)
    recommended_price_usd: int = Field(..., gt=0)
    build_recommendation: Literal["build", "dont_build", "pivot"]
    reasoning: str = Field(..., min_length=200)
    spec_additions: List[str] = Field(..., min_length=2)
    market_size_estimate: str = Field(..., min_length=1)
    biggest_risk: str = Field(..., min_length=1)

    @field_validator("top_3_competitors")
    @classmethod
    def exactly_three_competitors(cls, v: List[CompetitorInfo]) -> List[CompetitorInfo]:
        if len(v) != 3:
            raise ValueError(f"exactly 3 competitors required, got {len(v)}")
        return v


__all__ = ["CompetitorInfo", "PMOutput"]
