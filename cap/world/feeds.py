"""Product feeds as retailers publish them: four formats, four price encodings, field names that differ by retailer,
and formats that change without notice. The platform only ever sees the text.
"""

from __future__ import annotations

import csv
import io
import json

from cap.world.luck import stream
from cap.world.shops import Retailer


def in_stock(seed: int, retailer: Retailer, gtin: str, day: int) -> bool:
    return bool(stream(seed, "stock", retailer.name, gtin, day).random() > 0.08)


def encode_price(value: float, encoding: str):
    if encoding == "decimal_dot":
        return f"{value:.2f}"
    if encoding == "decimal_comma":
        return f"{value:.2f}".replace(".", ",") + " €"
    if encoding == "cents":
        return int(round(value * 100))
    return f"EUR {value:.2f}"


def rows(seed: int, retailer: Retailer, day: int) -> list[dict]:
    spec = retailer.feed[day]
    f = spec["fields"]
    out = []
    for p in retailer.products:
        stock = in_stock(seed, retailer, p.gtin, day)
        out.append({
            f["title"]: p.title,
            f["price"]: encode_price(retailer.price(p.id, day), spec["price_encoding"]),
            f["gtin"]: p.gtin,
            f["stock"]: ("InStock" if stock else "OutOfStock") if spec["format"] == "jsonld" else ("yes" if stock else "no"),
        })
    return out


def render(seed: int, retailer: Retailer, day: int) -> str:
    spec = retailer.feed[day]
    data = rows(seed, retailer, day)
    fmt = spec["format"]
    if fmt == "jsonld":
        return '<script type="application/ld+json">' + json.dumps([{"@type": "Product", **r} for r in data]) + "</script>"
    if fmt == "embedded_json":
        return "window.__DATA__ = " + json.dumps({"page": {"items": data}}) + ";"
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
        return buf.getvalue()
    head = "".join(f"<th>{k}</th>" for k in data[0])
    body = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r.values()) + "</tr>" for r in data)
    return f"<table><tr>{head}</tr>{body}</table>"


def truth(seed: int, retailer: Retailer, day: int) -> dict[str, tuple[float, bool]]:
    """GTIN -> (price, in stock) as it really is that day."""
    return {p.gtin: (retailer.price(p.id, day), in_stock(seed, retailer, p.gtin, day)) for p in retailer.products}
