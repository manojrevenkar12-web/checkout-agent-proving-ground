"""Runs the ingestion designs over every day and source of a world and grades the published catalogue."""

from __future__ import annotations

from cap import settings
from cap.ingest import pipeline as P
from cap.world import feeds
from cap.world.luck import stream
from cap.world.shops import World

DESIGNS = ["handwritten", "model_every_item", "self_checking"]


def run(world: World, design: str) -> dict:
    cfg = settings.platform()["ingest"]
    days = settings.world()["days"]
    published: dict[str, dict[str, tuple[float, bool]]] = {name: {} for name in world.retailers}
    mappings: dict[str, P.Mapping | None] = {}
    wrong = missing = held = served = 0
    model_eur = 0.0
    pages = 0
    quarantined_days = 0
    for day in range(days):
        for name, r in world.retailers.items():
            text = feeds.render(world.seed, r, day)
            records = P.rows(text)
            truth = feeds.truth(world.seed, r, day)
            rng = stream(world.seed, "ingest", design, name, day)
            prev = published[name]
            new: dict[str, tuple[float, bool]] = {}
            if design == "handwritten":
                if name not in mappings:
                    spec = r.feed[0]
                    mappings[name] = P.handwritten(records[: cfg["sample"]], spec["fields"], spec["price_encoding"])
                for g, p, s in P.apply(mappings[name], records, lenient_prices=True):
                    if g and p is not None and s is not None:
                        new[g] = (p, s)
            elif design == "model_every_item":
                for g, (price, stock) in truth.items():
                    model_eur += cfg["model_item_eur"]
                    if rng.random() < cfg["model_item_error"]:
                        price = round(price * float(rng.choice([10.0, 0.1, 1.5, 0.5])), 2)
                    new[g] = (price, stock)
            else:
                mapping = mappings.get(name)
                parsed = P.apply(mapping, records) if mapping else []
                ok = P.validate(parsed, prev, cfg["max_price_jump"]) if parsed else []
                if not parsed or sum(ok) / len(ok) < cfg["min_pass_rate"]:
                    model_eur += cfg["mapping_eur"]
                    sample = records[: cfg["sample"]]
                    mapping = P.propose(sample, rng, error=0.05)
                    mappings[name] = mapping
                    parsed = P.apply(mapping, records) if mapping else []
                    ok = P.validate(parsed, prev, cfg["max_price_jump"]) if parsed else []
                if not parsed or sum(ok) / len(ok) < cfg["min_pass_rate"]:
                    pages += 1
                    quarantined_days += 1
                    new = dict(prev)
                else:
                    for (g, p, s), good in zip(parsed, ok, strict=True):
                        if good:
                            new[g] = (p, s)
                        elif g in prev:
                            new[g] = prev[g]
                            held += 1
            published[name] = new
            for g, (price, stock) in truth.items():
                got = new.get(g)
                if got is None:
                    missing += 1
                else:
                    served += 1
                    if abs(got[0] - price) > 0.005 or got[1] != stock:
                        wrong += 1
    total = sum(len(r.products) for r in world.retailers.values()) * days
    return {
        "item_days": total,
        "wrong_share": wrong / total,
        "missing_share": missing / total,
        "held_rows": held,
        "model_eur": model_eur,
        "pages": pages,
        "quarantined_source_days": quarantined_days,
        "feed_changes": sum(1 for r in world.retailers.values() for d in range(1, days) if r.feed[d] != r.feed[d - 1]),
    }
