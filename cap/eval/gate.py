"""The release gate: thresholds from config/gate.yaml, checked on a report."""

from __future__ import annotations

from cap import settings


def check(rep: dict) -> dict:
    g = settings.gate()
    p = rep["checkout"]["platform"]
    m = rep["checkout"]["model_only"]
    checks = {
        "purchasable intents bought exactly right": p["correct_share"] >= g["min_correct_share"],
        "no more wrong orders than the bound": p["wrong_per_1000"] <= g["max_wrong_per_1000"],
        "no more duplicate orders than the bound": p["duplicate_per_1000"] <= g["max_duplicate_per_1000"],
        "shoppers are told what happened": p["silent_per_1000"] <= g["max_silent_per_1000"],
        "impossible intents are not bought": p["rightly_not_bought_share"] >= g["min_rightly_not_bought"],
        "better than the model alone (lower bound of the paired interval)": rep["comparisons"]["platform - model_only"]["ci"][0] > 0,
        "model cost per correct order under the bound": p["model_eur_per_correct"] <= g["max_model_eur_per_correct"],
        "cheaper per correct order than the model alone": p["model_eur_per_correct"] < m["model_eur_per_correct"],
        "ingestion publishes almost no wrong prices": rep["ingestion"]["self_checking"]["wrong_share"] <= g["max_wrong_price_share"],
        "search shows nothing above the shopper's budget": rep["search"]["understood_live_prices"]["over_budget_shown"] <= g["max_over_budget_shown"],
    }
    return {"passed": all(checks.values()), "checks": checks}
