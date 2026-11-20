"""Shoppers' product searches over every retailer's catalogue, graded against the world."""

from __future__ import annotations

from cap.search.engine import Index, search
from cap.world.luck import stream
from cap.world.shops import World

DESIGNS = ["keywords_weekly_prices", "keywords_live_prices", "understood_live_prices"]


def queries(world: World, n_per_day: int = 60):
    rng = stream(world.seed, "search-queries")
    by_day: dict[int, list] = {}
    for i in world.intents:
        by_day.setdefault(i.day, []).append(i)
    out = []
    for day, its in sorted(by_day.items()):
        for _ in range(n_per_day):
            it = its[int(rng.integers(len(its)))]
            r = world.retailers[it.retailer]
            p = r.by_id[it.product_id]
            budget = int(it.max_total / it.qty) + 1
            if rng.random() < 0.5:
                text = f"{p.title} size {it.variant.lower()} under {budget} euros"
            else:
                brand, _model, *cat = p.title.split()
                text = f"{brand} {' '.join(cat)} size {it.variant.lower()} under {budget} euros"
            out.append((day, it, text, budget))
    return out


def run(world: World, design: str) -> dict:
    docs, variants = {}, {}
    for r in world.retailers.values():
        for p in r.products:
            docs[p.id] = p.title
            variants[p.id] = {v.lower() for v in p.variants}
    index = Index(docs)
    owner = {p.id: r for r in world.retailers.values() for p in r.products}
    hits = shown = over = stale = 0
    qs = queries(world)
    for day, it, text, budget in qs:
        price_day = (day // 7) * 7 if design == "keywords_weekly_prices" else day
        prices = {d: r.price(d, price_day) for d, r in owner.items()}
        understand = design == "understood_live_prices"
        res = search(index, text, prices, variants, understand)
        hits += it.product_id in res
        for d in res:
            shown += 1
            true_price = owner[d].price(d, day)
            over += true_price > budget
            stale += abs(prices[d] - true_price) > 0.005
    n = len(qs)
    return {"queries": n, "hit_at_5": hits / n, "over_budget_shown": over / max(1, shown), "stale_price_shown": stale / max(1, shown)}
