from __future__ import annotations

import httpx

from .config import settings


async def create_checkout(variant_id: str, customer_email: str) -> str:
    if not settings.lemonsqueezy_api_key:
        raise RuntimeError("Lemon Squeezy is not configured")
    headers = {
        "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {"checkout_data": {"email": customer_email}},
            "relationships": {
                "variant": {"data": {"type": "variants", "id": variant_id}},
            },
        }
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["data"]["attributes"]["url"]
