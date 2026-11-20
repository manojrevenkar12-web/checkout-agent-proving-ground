"""Grades a run against the world's order book: what the shoppers actually got, and what they were told."""

from __future__ import annotations

from collections import Counter

from cap import settings
from cap.sim.engine import Run
from cap.world.shops import World
from cap.world.web import Order


def correct(order: Order, intent) -> bool:
    if len(order.lines) != 1 or order.addon > 0:
        return False
    pid, variant, qty, _unit = order.lines[0]
    return pid == intent.product_id and variant == intent.variant and qty == intent.qty and order.total <= intent.max_total + 1e-9


def outcome(world: World, run: Run, intent) -> str:
    orders = run.web.orders.get(intent.id, [])
    book = run.books[intent.id]
    if len(orders) >= 2:
        return "duplicate"
    if len(orders) == 1:
        return "correct" if correct(orders[0], intent) else "wrong"
    if not world.possible(intent):
        return "rightly_not_bought"
    if book.status == "declined":
        return "declined"
    if book.status == "handoff":
        return "handoff"
    if book.status == "abstained":
        return "wrongly_refused"
    return "missed"


def told_the_truth(run: Run, intent) -> bool:
    has = bool(run.web.orders.get(intent.id))
    return (run.books[intent.id].status == "confirmed") == has


def summarise(world: World, run: Run) -> dict:
    eco = settings.platform()["economics"]
    eur = settings.platform()["model"]["eur_per_step"]
    hours = settings.world()["hours_per_day"]
    out = Counter()
    minutes = []
    value = 0.0
    for i in world.intents:
        o = outcome(world, run, i)
        out[o] += 1
        if o == "correct":
            order = run.web.orders[i.id][0]
            value += eco["commission"] * order.total
            b = run.books[i.id]
            if b.done_hour >= 0:
                minutes.append(max(0, b.done_hour - (i.day * hours + i.hour)) * 60 + b.session_ms / 60000.0)
    n = len(world.intents)
    possible = sum(1 for i in world.intents if world.possible(i))
    silent = sum(1 for i in world.intents if not told_the_truth(run, i))
    model_eur = sum(b.model_steps for b in run.books.values()) * eur
    mistakes = eco["wrong_order_eur"] * out["wrong"] + eco["duplicate_order_eur"] * out["duplicate"]
    cost = model_eur + mistakes + eco["handoff_eur"] * out["handoff"] + eco["page_eur"] * run.pages
    minutes.sort()
    return {
        "intents": n,
        "possible": possible,
        "outcomes": dict(out),
        "correct_share": out["correct"] / possible if possible else 0.0,
        "wrong_per_1000": 1000 * out["wrong"] / n,
        "duplicate_per_1000": 1000 * out["duplicate"] / n,
        "silent_per_1000": 1000 * silent / n,
        "rightly_not_bought_share": out["rightly_not_bought"] / max(1, n - possible),
        "handoff_share": out["handoff"] / n,
        "model_eur": model_eur,
        "model_eur_per_correct": model_eur / max(1, out["correct"]),
        "median_minutes": minutes[len(minutes) // 2] if minutes else 0.0,
        "challenges": sum(run.web.challenges.values()),
        "newsletter_signups": run.web.newsletter_signups,
        "pages": run.pages,
        "contribution_eur": value - cost,
        "recipe_replays": run.replays,
        "model_repairs": run.misses,
    }
