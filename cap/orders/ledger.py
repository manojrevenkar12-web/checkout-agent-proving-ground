"""The order ledger: one row per shopper intent, and a rule that the platform clicks "pay" for an intent only
while no earlier click is unaccounted for. SQLAlchemy Core, so the same code runs on SQLite (tests, simulation)
and PostgreSQL (CI and production)."""

from __future__ import annotations

import os

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert, select, update
from sqlalchemy.engine import Engine

meta = MetaData()
intents = Table(
    "intents",
    meta,
    Column("intent_id", String, primary_key=True),
    Column("state", String, nullable=False),  # pending, submitting, unknown, confirmed, abstained, handoff, failed
    Column("attempts", Integer, nullable=False, default=0),
    Column("placements", Integer, nullable=False, default=0),
    Column("order_id", String, nullable=False, default=""),
    Column("reason", String, nullable=False, default=""),
)

FINAL = {"confirmed", "abstained", "handoff"}


class Ledger:
    def __init__(self, url: str | None = None):
        self.engine: Engine = create_engine(url or os.environ.get("CAP_DATABASE_URL", "sqlite+pysqlite:///:memory:"), future=True)
        meta.create_all(self.engine)

    def open(self, intent_id: str) -> dict:
        with self.engine.begin() as c:
            row = c.execute(select(intents).where(intents.c.intent_id == intent_id)).mappings().first()
            if row is None:
                c.execute(insert(intents).values(intent_id=intent_id, state="pending", attempts=0, placements=0, order_id="", reason=""))
                row = c.execute(select(intents).where(intents.c.intent_id == intent_id)).mappings().first()
            return dict(row)

    def begin_attempt(self, intent_id: str) -> str:
        """Returns the state the attempt starts from; 'unknown' means: reconcile before paying."""
        with self.engine.begin() as c:
            row = c.execute(select(intents.c.state, intents.c.attempts).where(intents.c.intent_id == intent_id)).first()
            c.execute(update(intents).where(intents.c.intent_id == intent_id).values(attempts=row.attempts + 1))
            return row.state

    def may_pay(self, intent_id: str) -> bool:
        """Atomically moves pending -> submitting. False if another click is unaccounted for or the intent is done."""
        with self.engine.begin() as c:
            r = c.execute(
                update(intents)
                .where(intents.c.intent_id == intent_id, intents.c.state.in_(["pending", "failed"]))
                .values(state="submitting", placements=intents.c.placements + 1)
            )
            return r.rowcount == 1

    def settle(self, intent_id: str, state: str, order_id: str = "", reason: str = "") -> None:
        with self.engine.begin() as c:
            c.execute(update(intents).where(intents.c.intent_id == intent_id).values(state=state, order_id=order_id, reason=reason))

    def get(self, intent_id: str) -> dict:
        with self.engine.begin() as c:
            return dict(c.execute(select(intents).where(intents.c.intent_id == intent_id)).mappings().first())

    def counts(self) -> dict[str, int]:
        with self.engine.begin() as c:
            out: dict[str, int] = {}
            for (state,) in c.execute(select(intents.c.state)):
                out[state] = out.get(state, 0) + 1
            return out
