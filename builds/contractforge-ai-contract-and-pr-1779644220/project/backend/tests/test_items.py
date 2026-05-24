from __future__ import annotations


def test_items_requires_auth(client) -> None:
    resp = client.get("/api/items")
    assert resp.status_code == 401
