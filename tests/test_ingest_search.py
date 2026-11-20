"""Ingestion finds rows in every format, proposes a mapping, and refuses implausible prices; search filters."""

import numpy as np

from cap.ingest import pipeline as P
from cap.search.engine import Index, search, understand
from cap.world import feeds
from cap.world.shops import build


def test_every_feed_format_parses_and_maps_to_the_truth():
    w = build(7101)
    for r in w.retailers.values():
        for day in (0, len(r.feed) - 1):
            recs = P.rows(feeds.render(w.seed, r, day))
            m = P.propose(recs[:25], np.random.default_rng(0), error=0.0)
            assert m is not None
            truth = feeds.truth(w.seed, r, day)
            for g, p, s in P.apply(m, recs):
                assert abs(truth[g][0] - p) < 0.005 and truth[g][1] == s


def test_validation_holds_a_price_that_jumped_a_hundredfold():
    parsed = [("4006381333931", 4990.0, True)]
    assert P.validate(parsed, {"4006381333931": (49.9, True)}, 0.5) == [False]
    assert P.validate([("4006381333931", 52.0, True)], {"4006381333931": (49.9, True)}, 0.5) == [True]
    assert not P.gtin_ok("4006381333932")


def test_a_hand_written_parser_misreads_a_changed_encoding():
    assert P.lenient("49.90", "cents") == 0.499
    assert P.lenient(4990, "decimal_dot") == 4990.0


def test_search_understands_budget_and_size():
    text, max_price, size = understand("Vela backpack size 28 l under 90 euros", {"28 l", "20 l"})
    assert max_price == 90.0 and size == "28 l"
    idx = Index({"a": "Vela Pro backpack", "b": "Vela Air backpack", "c": "Kestrel lamp"})
    res = search(idx, "Vela backpack under 90 euros", {"a": 120.0, "b": 80.0, "c": 10.0}, {"a": {"28 l"}, "b": {"28 l"}, "c": set()}, True)
    assert res == ["b"]
