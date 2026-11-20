"""The simulated open web: retailers, their catalogues and checkouts, how those change, and what shoppers want.

Everything here is the world's truth. The platform never imports this module's private state: it sees pages
through a session (cap.world.web), product feeds as text (cap.world.feeds), and the intents it is given.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from functools import cached_property

import numpy as np

from cap import settings
from cap.world.luck import stream

CATEGORIES = {
    "trail shoes": (["40", "41", "42", "43", "44", "45"], (70, 190)),
    "rain jacket": (["XS", "S", "M", "L", "XL"], (80, 320)),
    "headphones": (["Black", "White", "Blue"], (40, 380)),
    "coffee grinder": (["Black", "Steel"], (60, 420)),
    "backpack": (["20 L", "28 L", "35 L"], (40, 220)),
    "office chair": (["Grey", "Black"], (140, 650)),
    "running tights": (["XS", "S", "M", "L"], (30, 110)),
    "desk lamp": (["Brass", "White", "Black"], (25, 160)),
}
BRANDS = ["Nordkamm", "Vela", "Kestrel", "Lumo", "Haldor", "Arvo", "Tundra", "Precisa", "Softnest", "Riviera"]
MODELS = ["One", "Pro", "Air", "Max", "Lite", "Trail", "Studio", "Classic", "Edge", "Flow", "Prime", "Core"]
NAMES = ["Alpenhaus", "Brightcart", "Cobalt Goods", "Dovetail", "Elmstreet", "Fernway", "Gridline", "Harbor & Co",
         "Ironleaf", "Junebug", "Kiln", "Larkspur", "Meridian", "Northwind", "Oakmoss", "Pinecrest"]
TOTAL_LABELS = ["Total", "Order total", "Amount due"]


def gtin13(n: int) -> str:
    body = f"{n:012d}"[-12:]
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(body))
    return body + str((10 - s % 10) % 10)


def eid(salt: str, key: str) -> str:
    return f"{key.replace('_', '-')}-{hashlib.blake2b(f'{salt}:{key}'.encode(), digest_size=3).hexdigest()}"


@dataclass(frozen=True)
class Product:
    id: str
    retailer: str
    title: str
    brand: str
    category: str
    variants: tuple[str, ...]
    gtin: str
    base_price: float


@dataclass
class Retailer:
    name: str
    products: list[Product]
    layouts: list[dict]  # one per day: the checkout as it looks that day
    changes: list[tuple[int, list[str]]]  # (day, ops) drift events, truth for the recovery metrics
    defence: dict
    checkout: dict
    total_label: str
    feed: list[dict]  # one per day: the feed format that day
    prices: dict[str, list[float]]  # product id -> price per day

    @cached_property
    def by_id(self) -> dict[str, Product]:
        return {p.id: p for p in self.products}

    def price(self, product_id: str, day: int) -> float:
        return self.prices[product_id][day]


@dataclass(frozen=True)
class Intent:
    """What a shopper asked the agent to buy. The platform receives exactly these fields."""

    id: str
    retailer: str
    product_id: str
    title: str
    variant: str
    qty: int
    max_total: float
    address: tuple[str, str, str, str]
    day: int
    hour: int

    def public(self) -> dict:
        return {
            "id": self.id,
            "retailer": self.retailer,
            "product_id": self.product_id,
            "title": self.title,
            "variant": self.variant,
            "qty": self.qty,
            "max_total": self.max_total,
            "address": list(self.address),
            "day": self.day,
            "hour": self.hour,
        }


@dataclass(frozen=True)
class Fate:
    """What will happen to an intent at the retailer, whoever tries to buy it. Hidden from the platform."""

    price_rise: float  # 0.0, or the fraction the price rises by between cart and review
    stock_out: bool


@dataclass
class World:
    seed: int
    retailers: dict[str, Retailer]
    intents: list[Intent]
    fates: dict[str, Fate] = field(default_factory=dict)

    def possible(self, intent: Intent) -> bool:
        """Could a careful agent have bought exactly this within budget?"""
        f = self.fates[intent.id]
        if f.stock_out:
            return False
        r = self.retailers[intent.retailer]
        total = round(r.price(intent.product_id, intent.day) * (1 + f.price_rise), 2) * intent.qty
        return total <= intent.max_total + 1e-9


def _pick(rng: np.random.Generator, items):
    items = list(items)
    return items[int(rng.integers(len(items)))]


def _layout(rng: np.random.Generator, voc: dict, cfg: dict) -> dict:
    labels = {k: _pick(rng, voc[k]) for k in
              ("add_to_cart", "checkout", "continue", "to_review", "place_order", "decline_popup", "accept_popup",
               "reject_cookies", "accept_cookies", "variant", "quantity")}
    return {
        "labels": labels,
        "titles": {k: _pick(rng, v) for k, v in voc["titles"].items()},
        "address": list(_pick(rng, voc["address_fields"])),
        "salt": f"s{int(rng.integers(1_000_000))}",
        "popup": bool(rng.random() < 0.3),
        "cookie": bool(rng.random() < 0.5),
        "addon_on": "cart",
        "addon_default": bool(rng.random() < cfg["checkout"]["addon_trap"]),
        "addon_name": _pick(rng, voc["addon"]),
        "addon_price": float(_pick(rng, [2.99, 4.99, 6.5, 9.99])),
        "variant_default": int(rng.integers(1, 3)) if rng.random() < cfg["checkout"]["variant_trap"] else 0,
    }


def _drift(layout: dict, ops: list[str], rng: np.random.Generator, voc: dict) -> dict:
    new = copy.deepcopy(layout)
    for op in ops:
        if op == "relabel":
            key = _pick(rng, ["add_to_cart", "checkout", "continue", "to_review", "place_order", "decline_popup", "variant"])
            new["labels"][key] = _pick(rng, [v for v in voc[key] if v != new["labels"][key]])
            tkey = _pick(rng, list(voc["titles"]))
            new["titles"][tkey] = _pick(rng, voc["titles"][tkey])
        elif op == "new_ids":
            new["salt"] = f"s{int(rng.integers(1_000_000))}"
        elif op == "popup":
            new["popup"] = True
        elif op == "cookie_banner":
            new["cookie"] = True
        elif op == "addon_moves":
            new["addon_on"] = "review" if new["addon_on"] == "cart" else "cart"
        elif op == "addon_default_on":
            new["addon_default"] = True
        elif op == "variant_default_shift":
            new["variant_default"] = int(rng.integers(1, 3))
        elif op == "split_address":
            if len(new["address"]) == 4:
                new["address"] = [new["address"][0], new["address"][1], "Address line 2 (optional)", new["address"][2], new["address"][3]]
        elif op == "rare_label":
            key = _pick(rng, list(voc["rare_labels"]))
            new["labels"][key] = _pick(rng, voc["rare_labels"][key])
    return new


def _feed_spec(rng: np.random.Generator, cfg: dict) -> dict:
    f = cfg["feeds"]
    return {
        "format": _pick(rng, f["formats"]),
        "price_encoding": _pick(rng, f["price_encodings"]),
        "fields": {k: _pick(rng, v) for k, v in f["field_names"].items()},
    }


def _feed_drift(spec: dict, rng: np.random.Generator, cfg: dict) -> dict:
    new = copy.deepcopy(spec)
    f = cfg["feeds"]
    what = _pick(rng, ["encoding", "fields", "format"])
    if what == "encoding":
        new["price_encoding"] = _pick(rng, [e for e in f["price_encodings"] if e != spec["price_encoding"]])
    elif what == "fields":
        k = _pick(rng, list(f["field_names"]))
        new["fields"][k] = _pick(rng, [n for n in f["field_names"][k] if n != spec["fields"][k]])
    else:
        new["format"] = _pick(rng, [x for x in f["formats"] if x != spec["format"]])
    return new


def build(seed: int) -> World:
    cfg = settings.world()
    voc = cfg["vocabulary"]
    days = cfg["days"]
    names_rng = stream(seed, "names")
    names = [str(x) for x in names_rng.choice(NAMES, size=cfg["retailers"], replace=False)]
    retailers: dict[str, Retailer] = {}
    gtin_counter = int(stream(seed, "gtin").integers(10**10, 10**11))
    for ri, name in enumerate(names):
        rng = stream(seed, "retailer", name)
        products = []
        for i in range(cfg["products_per_retailer"]):
            cat = _pick(rng, sorted(CATEGORIES))
            variants, (lo, hi) = CATEGORIES[cat]
            price = round(float(np.exp(rng.uniform(np.log(lo), np.log(hi)))), 2)
            gtin_counter += 1
            products.append(Product(f"{name.lower().replace(' & ', '-').replace(' ', '-')}-{i:04d}", name,
                                    f"{_pick(rng, BRANDS)} {_pick(rng, MODELS)} {cat}", "", cat, tuple(variants),
                                    gtin13(gtin_counter + ri * 1000), price))
        products = [Product(p.id, p.retailer, p.title, p.title.split()[0], p.category, p.variants, p.gtin, p.base_price) for p in products]
        layout = _layout(rng, voc, cfg)
        layouts, changes = [], []
        drift_rng = stream(seed, "drift", name)
        for d in range(days):
            if d > 0 and drift_rng.random() < cfg["drift"]["per_day"]:
                k = int(drift_rng.integers(cfg["drift"]["ops_per_change"][0], cfg["drift"]["ops_per_change"][1] + 1))
                ops = [str(o) for o in drift_rng.choice(cfg["drift"]["ops"], size=k, replace=False)]
                layout = _drift(layout, ops, drift_rng, voc)
                changes.append((d, ops))
            layouts.append(layout)
        d_cfg, c_cfg = cfg["defence"], cfg["checkout"]
        defence = {
            "min_ms": float(rng.uniform(*d_cfg["min_ms_between_actions"])),
            "sessions_per_hour": int(rng.integers(d_cfg["sessions_per_hour"][0], d_cfg["sessions_per_hour"][1] + 1)),
        }
        checkout = {k: float(rng.uniform(*c_cfg[k])) for k in ("price_change", "stock_out_at_review", "ambiguous_payment", "declined")}
        checkout["page_ms"] = tuple(c_cfg["page_ms"])
        feed_rng = stream(seed, "feed", name)
        spec = _feed_spec(feed_rng, cfg)
        feed = []
        for d in range(days):
            if d > 0 and feed_rng.random() < cfg["feeds"]["change_per_day"]:
                spec = _feed_drift(spec, feed_rng, cfg)
            feed.append(spec)
        price_rng = stream(seed, "prices", name)
        prices = {}
        for p in products:
            series, cur = [], p.base_price
            for _d in range(days):
                if price_rng.random() < cfg["feeds"]["price_moves_per_day"]:
                    cur = round(cur * float(price_rng.uniform(0.85, 1.15)), 2)
                series.append(cur)
            prices[p.id] = series
        retailers[name] = Retailer(name, products, layouts, changes, defence, checkout, _pick(rng, TOTAL_LABELS), feed, prices)

    intents, fates = [], {}
    i_cfg = cfg["intents"]
    for name, r in retailers.items():
        rng = stream(seed, "intents", name)
        for d in range(days):
            peak = int(rng.integers(0, cfg["hours_per_day"]))
            for j in range(cfg["intents_per_retailer_per_day"]):
                p = _pick(rng, r.products)
                qty = 2 if rng.random() < i_cfg["qty_two"] else 1
                price = r.price(p.id, d)
                rise = float(rng.uniform(*settings.world()["checkout"]["price_rise"])) if rng.random() < r.checkout["price_change"] else 0.0
                if rng.random() < i_cfg["tight_budget"] and rise > 0:
                    max_total = round(price * qty * (1 + rise / 2), 2)
                else:
                    max_total = round(price * qty * (1 + float(rng.uniform(*i_cfg["budget_slack"])) + rise), 2)
                hour = peak if rng.random() < cfg["peak_share"] else int(rng.integers(0, cfg["hours_per_day"]))
                iid = f"{seed}-{p.id}-d{d}-{j}"
                intents.append(Intent(iid, name, p.id, p.title, _pick(rng, p.variants), qty, max_total,
                                      ("Alex Example", "Example Street 1", "10115", "Berlin"), d, hour))
                fates[iid] = Fate(rise, bool(rng.random() < r.checkout["stock_out_at_review"]))
    intents.sort(key=lambda x: (x.day, x.hour, x.id))
    return World(seed, retailers, intents, fates)
