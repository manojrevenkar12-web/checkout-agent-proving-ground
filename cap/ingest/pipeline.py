"""Product ingestion that writes, checks and watches its own parsers.

A feed arrives as text in one of several formats. The platform finds the rows (code), asks the model once per
source to propose which field is the title, price, GTIN and stock and how prices are written (one call, not one per
item), and then code decides: every row is validated (price positive and plausible against yesterday, GTIN check
digit, a known stock value), a source whose pass rate drops is re-mapped, and a source that still fails is held at
its last good data and pages on-call. A wrong price is never published to make a number look fresh.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass

import numpy as np

from cap import settings

STOCK_YES = {"instock", "yes", "true", "1", "in_stock", "available"}
STOCK_NO = {"outofstock", "no", "false", "0", "out_of_stock", "unavailable"}


def rows(text: str) -> list[dict]:
    """Finds the records in a feed, whatever its format."""
    t = text.strip()
    if t.startswith("<script"):
        return json.loads(re.sub(r"^<script[^>]*>|</script>$", "", t))
    if t.startswith("window.__DATA__"):
        blob = json.loads(t[len("window.__DATA__ = "):].rstrip(";"))
        return blob["page"]["items"]
    if t.startswith("<table"):
        heads = re.findall(r"<th>(.*?)</th>", t)
        out = []
        for tr in re.findall(r"<tr>((?:<td>.*?</td>)+)</tr>", t):
            out.append(dict(zip(heads, re.findall(r"<td>(.*?)</td>", tr), strict=False)))
        return out
    return list(csv.DictReader(io.StringIO(t)))


def gtin_ok(v) -> bool:
    s = str(v)
    if not re.fullmatch(r"\d{13}", s):
        return False
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(s[:12]))
    return (10 - total % 10) % 10 == int(s[12])


def shape(v) -> str:
    if isinstance(v, int) and not isinstance(v, bool):
        return "cents"
    s = str(v).strip()
    if s.startswith("EUR "):
        return "currency_prefix"
    if re.fullmatch(r"\d+,\d{2} €", s):
        return "decimal_comma"
    if re.fullmatch(r"\d+\.\d{2}", s):
        return "decimal_dot"
    if re.fullmatch(r"\d+", s):
        return "cents"
    return "unknown"


def decode(v, encoding: str) -> float | None:
    try:
        if encoding == "cents":
            return int(str(v)) / 100.0
        s = str(v).strip()
        if encoding == "currency_prefix":
            return float(s.removeprefix("EUR ").strip())
        if encoding == "decimal_comma":
            return float(s.removesuffix("€").strip().replace(",", "."))
        return float(s)
    except (ValueError, TypeError):
        return None


@dataclass
class Mapping:
    title: str
    price: str
    gtin: str
    stock: str
    encoding: str


def propose(sample: list[dict], rng: np.random.Generator, error: float) -> Mapping | None:
    """What the model proposes from a sample of rows. Code checks it afterwards; this can be wrong."""
    if not sample:
        return None
    keys = list(sample[0])
    gtin = next((k for k in keys if all(gtin_ok(r.get(k)) for r in sample)), None)
    stock = next((k for k in keys if all(str(r.get(k)).lower() in STOCK_YES | STOCK_NO for r in sample)), None)
    shapes = {k: {shape(r.get(k)) for r in sample} for k in keys if k not in (gtin, stock)}
    price = next((k for k, s in shapes.items() if len(s) == 1 and "unknown" not in s), None)
    title = next((k for k in keys if k not in (gtin, stock, price)), None)
    if None in (gtin, stock, price, title):
        return None
    encoding = next(iter(shapes[price]))
    if rng.random() < error:
        encoding = "cents" if encoding != "cents" else "decimal_dot"
    return Mapping(title, price, gtin, stock, encoding)


def handwritten(sample: list[dict], spec_fields: dict, encoding: str) -> Mapping:
    """What a developer writes once against the day-0 feed and leaves alone."""
    return Mapping(spec_fields["title"], spec_fields["price"], spec_fields["gtin"], spec_fields["stock"], encoding)


def lenient(v, encoding: str) -> float | None:
    """How a hand-written parser usually reads a price: keep the digits and separators, then divide if it was cents."""
    s = re.sub(r"[^0-9,.]", "", str(v)).replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        return None
    return x / 100.0 if encoding == "cents" else x


def apply(mapping: Mapping, records: list[dict], lenient_prices: bool = False) -> list[tuple[str, float | None, bool | None]]:
    out = []
    for r in records:
        g = r.get(mapping.gtin)
        read = lenient if lenient_prices else decode
        p = read(r.get(mapping.price), mapping.encoding) if mapping.price in r else None
        st = str(r.get(mapping.stock, "")).lower()
        stock = True if st in STOCK_YES else (False if st in STOCK_NO else None)
        out.append((str(g) if g is not None else "", p, stock))
    return out


def validate(parsed, yesterday: dict[str, tuple[float, bool]], max_jump: float) -> list[bool]:
    ok = []
    for g, p, s in parsed:
        good = gtin_ok(g) and p is not None and p > 0 and s is not None
        if good and g in yesterday:
            prev = yesterday[g][0]
            good = abs(p / prev - 1.0) <= max_jump
        ok.append(good)
    return ok


def settings_ingest() -> dict:
    return settings.platform()["ingest"]
