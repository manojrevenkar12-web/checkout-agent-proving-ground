"""The README's results block and the charts, generated from reports/*.json. Nothing here is typed by hand."""

from __future__ import annotations

import json

from cap.settings import ROOT

REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
README = ROOT / "README.md"
START, END = "<!-- results:start -->", "<!-- results:end -->"

LABELS = {
    "scripted": "Scripts recorded on day 0",
    "model_only": "Computer-use model alone",
    "platform": "Proving-ground platform",
    "platform_no_guards": "Platform without code guards",
    "platform_no_ledger": "Platform without the order ledger",
    "platform_no_pacing": "Platform without pacing or session budgets",
    "platform_no_recipes": "Platform without recipes (model every step)",
}
INGEST = {"handwritten": "Hand-written parsers", "model_every_item": "Model reads every item", "self_checking": "Self-checking mappings"}
SEARCH = {"keywords_weekly_prices": "Keywords, prices from a weekly index", "keywords_live_prices": "Keywords, live prices",
          "understood_live_prices": "Query understanding, live prices"}
ORDER = ["platform", "model_only", "scripted", "platform_no_guards", "platform_no_ledger", "platform_no_recipes", "platform_no_pacing"]
# validated categorical slots 1-3: blue, orange, aqua
COLOURS = {"platform": "#2a78d6", "scripted": "#eb6834", "model_only": "#1baf7a"}
INK, MUTED, GRID, SURFACE = "#1b1f24", "#5b626b", "#e3e6ea", "#fcfcfb"


def load(name: str) -> dict | None:
    p = REPORTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _svg(w: int, h: int, title: str, sub: str, body: list[str]) -> str:
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="Inter, Segoe UI, sans-serif">',
        f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
        f'<text x="20" y="28" font-size="15" font-weight="600" fill="{INK}">{title}</text>',
        f'<text x="20" y="47" font-size="12" fill="{MUTED}">{sub}</text>', *body, "</svg>"]) + "\n"


def chart_days(rep: dict) -> str:
    w, h, left, right, top, bottom = 760, 330, 60, 170, 70, 40
    short = {"platform": "Platform", "model_only": "Model alone", "scripted": "Day-0 scripts"}
    series = rep["by_day"]
    n = len(next(iter(series.values())))

    def X(i: int) -> float:
        return left + i * (w - left - right) / max(1, n - 1)

    def Y(v: float) -> float:
        return top + (1 - v) * (h - top - bottom)

    body = []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        body.append(f'<line x1="{left}" y1="{Y(t):.1f}" x2="{w - right}" y2="{Y(t):.1f}" stroke="{GRID}"/>')
        body.append(f'<text x="{left - 8}" y="{Y(t) + 4:.1f}" font-size="11" text-anchor="end" fill="{MUTED}">{int(t * 100)}%</text>')
    for i in range(0, n, 5):
        body.append(f'<text x="{X(i):.1f}" y="{h - 18}" font-size="11" text-anchor="middle" fill="{MUTED}">day {i}</text>')
    for d in ("scripted", "model_only", "platform"):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(series[d]))
        body.append(f'<polyline points="{pts}" fill="none" stroke="{COLOURS[d]}" stroke-width="2" stroke-linejoin="round"/>')
        last = series[d][-1]
        body.append(f'<circle cx="{X(n - 1):.1f}" cy="{Y(last):.1f}" r="4" fill="{COLOURS[d]}" stroke="{SURFACE}" stroke-width="2"/>')
        body.append(f'<text x="{X(n - 1) + 10:.1f}" y="{Y(last) + 4:.1f}" font-size="12" fill="{INK}">{short[d]} {last * 100:.0f}%</text>')
    return _svg(w, h, "Orders placed exactly right, day by day", "Share of purchasable intents; retailers change their checkouts on some days", body)


def chart_designs(rep: dict) -> str:
    rows = [(d, rep["checkout"][d]) for d in ORDER if d in rep["checkout"]]
    w, left, right, top = 760, 300, 70, 64
    h = top + len(rows) * 30 + 20
    body = []
    for i, (d, v) in enumerate(rows):
        y = top + i * 30
        x1 = left + v["correct_share"] * (w - left - right)
        colour = COLOURS.get(d, "#a3a9a6")
        body.append(f'<text x="{left - 10}" y="{y + 15}" font-size="12" text-anchor="end" fill="{INK}">{LABELS[d]}</text>')
        body.append(f'<rect x="{left}" y="{y + 4}" width="{max(1, x1 - left):.1f}" height="16" rx="3" fill="{colour}"/>')
        body.append(f'<text x="{x1 + 6:.1f}" y="{y + 16}" font-size="11" font-weight="600" fill="{INK}">{v["correct_share"] * 100:.1f}%</text>')
    return _svg(w, h, "Orders placed exactly right, by design", "Same worlds, same shoppers, same retailer changes and defences", body)


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _headline(rep: dict, title: str) -> list[str]:
    c = rep["checkout"]
    cols = ["platform", "model_only", "scripted"]
    lines = [f"| {title} | " + " | ".join(LABELS[x] for x in cols) + " |", "|---|" + "---:|" * len(cols)]

    def row(name, f):
        cells = [f(c[x]) for x in cols]
        cells[0] = f"**{cells[0]}**"
        lines.append(f"| {name} | " + " | ".join(cells) + " |")

    row("Purchasable intents bought exactly right", lambda x: _pct(x["correct_share"]))
    row("Wrong orders (item, size, quantity, add-on or over budget), per 1,000 intents", lambda x: f"{x['wrong_per_1000']:.1f}")
    row("Duplicate orders, per 1,000 intents", lambda x: f"{x['duplicate_per_1000']:.1f}")
    row("Shopper told something different from what happened, per 1,000", lambda x: f"{x['silent_per_1000']:.1f}")
    row("Impossible intents correctly not bought (out of stock, over budget)", lambda x: _pct(x["rightly_not_bought_share"]))
    row("Handed to the shopper after a human check", lambda x: _pct(x["handoff_share"]))
    row("Model cost per correct order", lambda x: f"€{x['model_eur_per_correct']:.4f}")
    row("Human checks the retailers asked for", lambda x: f"{x['challenges']:.0f}")
    row("On-call pages (only the platform has alerting)", lambda x: f"{x['pages']:.0f}")
    row("Contribution per world (commission minus model, mistakes and pages)", lambda x: f"€{x['contribution_eur']:,.0f}")
    return lines


def _designs(rep: dict) -> list[str]:
    lines = ["| Design | Exactly right | Wrong / 1,000 | Duplicates / 1,000 | Told wrong / 1,000 | Model € / correct | Pages |", "|---|---:|---:|---:|---:|---:|---:|"]
    for d in ORDER:
        x = rep["checkout"][d]
        name = f"**{LABELS[d]}**" if d == "platform" else LABELS[d]
        lines.append(f"| {name} | {_pct(x['correct_share'])} | {x['wrong_per_1000']:.1f} | {x['duplicate_per_1000']:.1f} | {x['silent_per_1000']:.1f} | €{x['model_eur_per_correct']:.4f} | {x['pages']:.0f} |")
    lines += ["", "| Platform minus | Exactly-right difference (95% interval, paired by intent) |", "|---|---:|"]
    for other in ORDER:
        if other == "platform":
            continue
        v = rep["comparisons"][f"platform - {other}"]
        lines.append(f"| {LABELS[other]} | {v['mean'] * 100:+.1f} points ({v['ci'][0] * 100:+.1f} to {v['ci'][1] * 100:+.1f}) |")
    return lines


def _changes(rep: dict) -> list[str]:
    lines = ["| On the day a retailer changed its checkout | Exactly right that day | On other days |", "|---|---:|---:|"]
    for d in ("platform", "model_only", "scripted"):
        x = rep["change_days"][d]
        lines.append(f"| {LABELS[d]} | {_pct(x['changed'])} | {_pct(x['unchanged'])} |")
    return lines


def _ingest(rep: dict) -> list[str]:
    lines = ["| Ingestion | Wrong prices or stock published | Products missing | Model € per world | Pages |", "|---|---:|---:|---:|---:|"]
    for d in INGEST:
        x = rep["ingestion"][d]
        name = f"**{INGEST[d]}**" if d == "self_checking" else INGEST[d]
        lines.append(f"| {name} | {x['wrong_share'] * 100:.2f}% | {x['missing_share'] * 100:.2f}% | €{x['model_eur']:.2f} | {x['pages']:.0f} |")
    lines += ["", "| Search | Wanted product in the top 5 | Results above the shopper's budget | Stale prices shown |", "|---|---:|---:|---:|"]
    for d in SEARCH:
        x = rep["search"][d]
        name = f"**{SEARCH[d]}**" if d == "understood_live_prices" else SEARCH[d]
        lines.append(f"| {name} | {_pct(x['hit_at_5'])} | {_pct(x['over_budget_shown'])} | {_pct(x['stale_price_shown'])} |")
    return lines


def block(dev: dict, held: dict | None, gate_dev: dict | None, gate_held: dict | None) -> str:
    w = dev["worlds"]
    lines = [START, "", "### Dashboard (development worlds)", "", *_headline(dev, "Development"), "",
             f"{len(w)} simulated worlds; each has {w[0]['retailers']} retailers, {w[0]['intents']:,} purchase intents over "
             f"{len(dev['by_day']['platform'])} days, {sum(x['checkout_changes'] for x in w) / len(w):.0f} checkout changes and "
             f"{sum(x['feed_changes'] for x in w) / len(w):.0f} feed changes.", "",
             "![Exactly right, day by day](reports/charts/days.svg)", "", "### Every design on the same luck", "", *_designs(dev), "",
             "![By design](reports/charts/designs.svg)", "", "### When a retailer changes its checkout", "", *_changes(dev), "",
             "### Ingestion and search", "", *_ingest(dev)]
    if gate_dev:
        lines += ["", f"Gate (`config/gate.yaml`) on the development worlds: **{'passed' if gate_dev['passed'] else 'failed'}**."]
    if held:
        lines += ["", "### Held-out worlds (run once)", "", *_headline(held, "Held-out"), "", *_changes(held)]
        if gate_held:
            lines += ["", f"Gate on the held-out worlds: **{'passed' if gate_held['passed'] else 'failed'}**."]
    lines += ["", END]
    return "\n".join(lines)


def write_charts(dev: dict) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    (CHARTS / "days.svg").write_text(chart_days(dev))
    (CHARTS / "designs.svg").write_text(chart_designs(dev))


def render_readme(text: str, new: str) -> str:
    a, b = text.index(START), text.index(END) + len(END)
    return text[:a] + new + text[b:]
