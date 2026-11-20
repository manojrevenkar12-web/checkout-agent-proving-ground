"""The service: place an order through the platform on the demo world, idempotently, and read the reports.

- `GET /health`
- `GET /api/results`: the development report, the held-out report (once run) and the gate on each.
- `GET /api/retailers`: the demo world's retailers and whether each changed its checkout on a given day.
- `POST /api/orders`: an intent with an idempotency key; the platform runs the checkout once and remembers it.
- `GET /api/orders/{key}`: what happened to it.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cap import settings
from cap.agent.pilot import Memory, Model, Pilot
from cap.eval import gate, report
from cap.orders.ledger import Ledger
from cap.settings import ROOT
from cap.world.luck import stream
from cap.world.shops import Intent, build
from cap.world.web import Web

app = FastAPI(title="checkout-agent-proving-ground")
DEMO_SEED = int(os.environ.get("CAP_DEMO_SEED", "7101"))


@cache
def demo():
    world = build(DEMO_SEED)
    d = {"pilot": "recipes", "guards": True, "ledger": True, "pacing": True}
    return world, Web(world), Pilot(d["pilot"], d["guards"], d["ledger"], d["pacing"], Model()), {n: Memory() for n in world.retailers}


@cache
def ledger() -> Ledger:
    return Ledger(os.environ.get("CAP_DATABASE_URL", f"sqlite+pysqlite:///{ROOT / 'orders.db'}"))


class OrderIn(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    intent_id: str = Field(description="An intent of the demo world, from GET /api/intents")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/results")
def results() -> dict:
    dev, held = report.load("dev"), report.load("heldout")
    if dev is None:
        raise HTTPException(404, "no evaluation yet: python -m cap.eval.cli evaluate")
    return {"dev": dev, "heldout": held, "gate": {"dev": gate.check(dev), "heldout": gate.check(held) if held else None}}


@app.get("/api/retailers")
def retailers(day: int = 0) -> list[dict]:
    world = demo()[0]
    return [{"name": r.name, "changed_today": any(d == day for d, _ in r.changes), "products": len(r.products)} for r in world.retailers.values()]


@app.get("/api/intents")
def intents(day: int = 0, limit: int = 20) -> list[dict]:
    world = demo()[0]
    return [i.public() for i in world.intents if i.day == day][:limit]


@app.post("/api/orders")
def place(body: OrderIn) -> dict:
    world, web, pilot, memories = demo()
    intent: Intent | None = next((i for i in world.intents if i.id == body.intent_id), None)
    if intent is None:
        raise HTTPException(404, "unknown intent")
    led = ledger()
    row = led.open(body.idempotency_key)
    if row["state"] in ("confirmed", "abstained", "declined", "unknown"):
        return {"key": body.idempotency_key, "replayed": True, **_public(led.get(body.idempotency_key))}
    pages, seconds, calls = [], 0.0, 0
    for attempt in range(settings.platform()["agent"]["max_attempts"]):
        reconcile_first = led.begin_attempt(body.idempotency_key) == "unknown"
        session = web.open(intent, intent.hour)
        res = pilot.run(session, intent, memories[intent.retailer], stream(world.seed, "api", body.idempotency_key, attempt),
                        reconcile_first, lambda: led.may_pay(body.idempotency_key))
        state = res.status if res.status in ("confirmed", "unknown", "declined", "abstained") else "failed"
        led.settle(body.idempotency_key, state, res.order_id, res.reason)
        pages.append(session.history)
        seconds += res.ms / 1000
        calls += res.model_steps
        if state != "failed" or res.status in ("challenged", "blocked"):
            break
    return {"key": body.idempotency_key, "replayed": False, **_public(led.get(body.idempotency_key)), "sessions": pages,
            "seconds": round(seconds, 1), "model_calls": calls}


@app.get("/api/orders/{key}")
def get_order(key: str) -> dict:
    try:
        return {"key": key, **_public(ledger().get(key))}
    except TypeError:
        raise HTTPException(404, "unknown key") from None


def _public(row: dict) -> dict:
    return {"state": row["state"], "order_id": row["order_id"], "reason": row["reason"], "attempts": row["attempts"]}


DIST = Path(ROOT / "web" / "dist")
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        return FileResponse(DIST / "index.html")
