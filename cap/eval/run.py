"""Every design on every world of a seed set, on the same luck; the summary that reports and the gate read."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from cap import settings
from cap.eval.grade import outcome, summarise
from cap.sim import discovery, ingestion
from cap.sim.engine import run as run_checkout
from cap.world.luck import stream
from cap.world.shops import build

CHECKOUT = ["scripted", "model_only", "platform", "platform_no_guards", "platform_no_ledger", "platform_no_pacing", "platform_no_recipes"]


def evaluate(seeds: list[int]) -> dict:
    per = {d: [] for d in CHECKOUT}
    pairs = defaultdict(list)  # design -> per-intent correct flags, in the same order for every design
    daily = {d: defaultdict(list) for d in ("scripted", "model_only", "platform")}
    drift_days = {d: [] for d in ("scripted", "model_only", "platform")}
    calm_days = {d: [] for d in ("scripted", "model_only", "platform")}
    ingest = {d: [] for d in ingestion.DESIGNS}
    search = {d: [] for d in discovery.DESIGNS}
    worlds = []
    for seed in seeds:
        world = build(seed)
        worlds.append({"seed": seed, "intents": len(world.intents), "retailers": len(world.retailers),
                       "checkout_changes": sum(len(r.changes) for r in world.retailers.values()),
                       "feed_changes": sum(1 for r in world.retailers.values() for x in range(1, len(r.feed)) if r.feed[x] != r.feed[x - 1])})
        changed = {(r.name, day) for r in world.retailers.values() for day, _ in r.changes}
        for d in CHECKOUT:
            run = run_checkout(world, d)
            per[d].append(summarise(world, run))
            outs = [outcome(world, run, i) for i in world.intents]
            possible = [world.possible(i) for i in world.intents]
            pairs[d].extend(o == "correct" for o, p in zip(outs, possible, strict=True) if p)
            if d in daily:
                cell = defaultdict(lambda: [0, 0])
                for i, o, p in zip(world.intents, outs, possible, strict=True):
                    if p:
                        cell[(i.retailer, i.day)][0] += o == "correct"
                        cell[(i.retailer, i.day)][1] += 1
                for (rname, day), (c, n) in cell.items():
                    daily[d][day].append(c / n)
                    (drift_days if (rname, day) in changed else calm_days)[d].append(c / n)
        for d in ingestion.DESIGNS:
            ingest[d].append(ingestion.run(world, d))
        for d in discovery.DESIGNS:
            search[d].append(discovery.run(world, d))

    def mean(rows: list[dict]) -> dict:
        keys = [k for k, v in rows[0].items() if isinstance(v, int | float)]
        out = {k: float(np.mean([r[k] for r in rows])) for k in keys}
        if "correct_share" in rows[0]:
            out["range"] = {k: [float(min(r[k] for r in rows)), float(max(r[k] for r in rows))] for k in ("correct_share", "wrong_per_1000")}
        if "outcomes" in rows[0]:
            tot = defaultdict(int)
            for r in rows:
                for k, v in r["outcomes"].items():
                    tot[k] += v
            out["outcomes"] = dict(tot)
        return out

    def paired(a: str, b: str) -> dict:
        x = np.array(pairs[a], dtype=float) - np.array(pairs[b], dtype=float)
        rng = stream(seeds[0], "bootstrap", a, b)
        idx = rng.integers(0, len(x), size=(1000, len(x)))
        means = x[idx].mean(axis=1)
        return {"mean": float(x.mean()), "ci": [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))], "n": len(x)}

    days = settings.world()["days"]
    return {
        "seeds": seeds,
        "worlds": worlds,
        "checkout": {d: mean(v) for d, v in per.items()},
        "comparisons": {f"platform - {b}": paired("platform", b) for b in CHECKOUT if b != "platform"},
        "by_day": {d: [float(np.mean(daily[d][x])) if daily[d][x] else 0.0 for x in range(days)] for d in daily},
        "change_days": {d: {"changed": float(np.mean(drift_days[d])) if drift_days[d] else 0.0,
                            "unchanged": float(np.mean(calm_days[d])) if calm_days[d] else 0.0,
                            "changed_cells": len(drift_days[d])} for d in drift_days},
        "ingestion": {d: mean(v) for d, v in ingest.items()},
        "search": {d: mean(v) for d, v in search.items()},
    }
