"""The service places an order once per idempotency key."""

from fastapi.testclient import TestClient


def test_an_order_is_placed_once_per_key(monkeypatch, tmp_path):
    monkeypatch.setenv("CAP_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'orders.db'}")
    from cap.service import api

    api.ledger.cache_clear()
    c = TestClient(api.app)
    assert c.get("/health").json() == {"status": "ok"}
    intent = c.get("/api/intents?day=2&limit=1").json()[0]
    first = c.post("/api/orders", json={"idempotency_key": "test-key-0001", "intent_id": intent["id"]}).json()
    again = c.post("/api/orders", json={"idempotency_key": "test-key-0001", "intent_id": intent["id"]}).json()
    assert first["state"] in ("confirmed", "abstained", "declined", "unknown"), first
    assert again["replayed"] is True and again["order_id"] == first["order_id"]
    assert c.post("/api/orders", json={"idempotency_key": "bad key!", "intent_id": intent["id"]}).status_code == 422
