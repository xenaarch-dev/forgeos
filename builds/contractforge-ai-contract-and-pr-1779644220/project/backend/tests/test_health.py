from __future__ import annotations


def test_healthz(client) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ("ok", "healthy")
