from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/ml", tags=["ml"])


class InferRequest(BaseModel):
    features: list[float]


class InferResponse(BaseModel):
    score: float


@router.post("/predict", response_model=InferResponse)
async def predict(payload: InferRequest) -> InferResponse:
    # Placeholder model — replace with a real loaded artifact.
    score = sum(payload.features) / max(1, len(payload.features))
    return InferResponse(score=score)
