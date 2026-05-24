from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request

from ..config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


def _verify(signature: str, body: bytes, secret: str) -> bool:
    if not signature or not secret:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


@router.post("/webhook")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: str = Header(default=""),
) -> dict[str, str]:
    body = await request.body()
    if not _verify(x_signature, body, settings.lemonsqueezy_webhook_secret):
        raise HTTPException(status_code=401, detail="Bad signature")
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e
    event = payload.get("meta", {}).get("event_name")
    # In production, route on event and update subscription state.
    return {"status": "received", "event": event or "unknown"}
