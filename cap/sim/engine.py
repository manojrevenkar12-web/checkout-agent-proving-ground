"""Runs one design over one world: every intent, hour by hour, with retries, pacing, breakers and the ledger."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from cap import settings
from cap.agent.pilot import Memory, Model, Pilot, record_script
from cap.orders.ledger import Ledger
from cap.world.luck import stream
from cap.world.shops import World
from cap.world.web import Web


@dataclass
class Book:
    """What the platform recorded and told the shopper about one intent."""

    status: str = "pending"  # confirmed, abstained, declined, handoff, failed, expired
    order_id: str = ""
    reason: str = ""
    attempts: int = 0
    model_steps: int = 0
    session_ms: float = 0.0
    done_hour: int = -1
    challenges: int = 0


@dataclass
class Run:
    design: str
    web: Web
    books: dict[str, Book]
    pages: int = 0
    breaker_hours: int = 0
    deferred: int = 0
    replays: int = 0
    misses: int = 0
    daily: dict[tuple, list[str]] = field(default_factory=lambda: defaultdict(list))


def run(world: World, design: str) -> Run:
    d = settings.platform()["designs"][design]
    a = settings.platform()["agent"]
    b = settings.platform()["breaker"]
    model = Model()
    pilot = Pilot(d["pilot"], d["guards"], d["ledger"], d["pacing"], model)
    web = Web(world)
    ledger = Ledger("sqlite+pysqlite:///:memory:") if d["ledger"] else None
    memories = {name: Memory() for name in world.retailers}
    if d["pilot"] == "script":
        for name in world.retailers:
            first = next(i for i in world.intents if i.retailer == name and i.day == 0 and not world.fates[i.id].stock_out)
            memories[name].script = record_script(lambda: Web(world), name, first, model)
    books = {i.id: Book() for i in world.intents}
    out = Run(design, web, books)
    budget = {name: a["session_budget_start"] for name in world.retailers}
    window = {name: deque(maxlen=b["window"]) for name in world.retailers}
    open_until = {name: -1 for name in world.retailers}
    hours = settings.world()["hours_per_day"]
    by_day: dict[int, list] = defaultdict(list)
    for i in world.intents:
        by_day[i.day].append(i)

    for day in sorted(by_day):
        queue = {i.id: (i.hour, i) for i in by_day[day]}
        for hour in range(hours):
            clock = day * hours + hour
            opened = defaultdict(int)
            challenged = defaultdict(int)
            for iid, (due, intent) in sorted(queue.items(), key=lambda kv: (kv[1][0], kv[0])):
                if due > hour:
                    continue
                r = intent.retailer
                book = books[iid]
                if d["breaker"] and open_until[r] > clock:
                    out.deferred += 1
                    continue
                if d["budget"] and opened[r] >= budget[r]:
                    out.deferred += 1
                    continue
                opened[r] += 1
                book.attempts += 1
                reconcile_first = False
                before_pay = None
                if ledger is not None:
                    ledger.open(iid)
                    reconcile_first = ledger.begin_attempt(iid) == "unknown"
                    def before_pay(iid=iid, ledger=ledger):
                        return ledger.may_pay(iid)

                session = web.open(intent, hour)
                rng = stream(world.seed, "pilot", design, iid, book.attempts)
                res = pilot.run(session, intent, memories[r], rng, reconcile_first, before_pay)
                book.model_steps += res.model_steps
                book.session_ms += res.ms
                st = res.status
                if ledger is not None and st in ("confirmed", "unknown", "declined", "abstained"):
                    ledger.settle(iid, st, res.order_id, res.reason)
                elif ledger is not None and st == "failed" and ledger.get(iid)["state"] == "submitting":
                    ledger.settle(iid, "unknown", "", res.reason)
                finished = st in ("confirmed", "abstained", "declined")
                if st == "challenged":
                    book.challenges += 1
                    challenged[r] += 1
                if d["breaker"]:
                    window[r].append(st not in ("challenged", "blocked"))
                    w = window[r]
                    if len(w) == w.maxlen and sum(w) / len(w) < b["min_success"]:
                        open_until[r] = clock + b["cooldown_hours"]
                        out.pages += 1
                        w.clear()
                out.daily[(r, day)].append(st)
                if finished:
                    book.status, book.order_id, book.reason, book.done_hour = st, res.order_id, res.reason, clock
                    del queue[iid]
                elif book.attempts >= a["max_attempts"]:
                    if st in ("challenged", "blocked") and d["breaker"]:
                        book.status, book.reason = "handoff", "handed to the shopper to finish in their own browser"
                    else:
                        book.status, book.reason = "failed", res.reason
                    book.done_hour = clock
                    del queue[iid]
                else:
                    book.status, book.reason = st, res.reason
                    queue[iid] = (hour + 1, intent)
            if d["budget"]:
                for r in world.retailers:
                    if challenged[r]:
                        budget[r] = max(a["session_budget_floor"], budget[r] // 2)
                    elif opened[r]:
                        budget[r] = min(a["session_budget_ceiling"], budget[r] + 2)
        for iid in list(queue):
            book = books[iid]
            if book.status not in ("confirmed", "abstained", "declined", "handoff", "failed") or book.status == "failed" and book.done_hour < 0:
                book.status = "expired"
    out.replays = sum(m.replays for m in memories.values())
    out.misses = sum(m.misses for m in memories.values())
    return out
