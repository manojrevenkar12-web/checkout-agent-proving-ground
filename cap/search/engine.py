"""Search over a catalogue that never stops changing: BM25 over titles, query understanding that turns
"under 120 euros" and a size into filters, and prices joined at query time from the latest published catalogue
instead of from an index snapshot."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

TOKEN = re.compile(r"[a-z0-9]+")
PRICE = re.compile(r"\b(?:under|below|up to|max)\s+€?\s*(\d+(?:[.,]\d+)?)\s*(?:euros?|eur|€)?")


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


class Index:
    def __init__(self, docs: dict[str, str], k1: float = 1.2, b: float = 0.75):
        self.docs = {d: tokens(t) for d, t in docs.items()}
        self.k1, self.b = k1, b
        self.avg = sum(len(t) for t in self.docs.values()) / max(1, len(self.docs))
        self.df: Counter = Counter()
        self.post: dict[str, list[str]] = defaultdict(list)
        for d, ts in self.docs.items():
            for t in set(ts):
                self.df[t] += 1
                self.post[t].append(d)
        self.n = len(self.docs)

    def score(self, query: list[str]) -> dict[str, float]:
        out: dict[str, float] = defaultdict(float)
        for t in set(query):
            if t not in self.df:
                continue
            idf = math.log(1 + (self.n - self.df[t] + 0.5) / (self.df[t] + 0.5))
            for d in self.post[t]:
                ts = self.docs[d]
                tf = ts.count(t)
                out[d] += idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * len(ts) / self.avg))
        return out


def understand(query: str, variants_vocab: set[str]) -> tuple[str, float | None, str | None]:
    m = PRICE.search(query.lower())
    max_price = float(m.group(1).replace(",", ".")) if m else None
    rest = PRICE.sub(" ", query.lower()) if m else query.lower()
    size = None
    sm = re.search(r"\b(?:size|in)\s+([a-z0-9]+(?:\s?l)?)\b", rest)
    if sm and sm.group(1) in variants_vocab:
        size = sm.group(1)
        rest = rest.replace(sm.group(0), " ")
    return rest, max_price, size


def search(index: Index, query: str, prices: dict[str, float], variants: dict[str, set[str]], understand_query: bool, k: int = 5) -> list[str]:
    vocab = {v for vs in variants.values() for v in vs}
    text, max_price, size = understand(query, vocab) if understand_query else (query, None, None)
    scored = index.score(tokens(text))
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
    out = []
    for d, _ in ranked:
        if max_price is not None and prices.get(d, math.inf) > max_price:
            continue
        if size is not None and size not in variants.get(d, set()):
            continue
        out.append(d)
        if len(out) == k:
            break
    return out
