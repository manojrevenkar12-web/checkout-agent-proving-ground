"""Pilots, guards, recipes and the ledger."""

from cap.agent.pilot import Guards, Memory, Model, Pilot
from cap.orders.ledger import Ledger
from cap.world.shops import Intent
from cap.world.web import Element, Page, Web

INTENT = Intent("i1", "Shop", "p1", "Vela Pro backpack", "28 L", 1, 100.0, ("A", "B", "C", "D"), 0, 0)


def review(*texts, box=False):
    els = [Element(f"t{i}", "text", t) for i, t in enumerate(texts)]
    if box:
        els.append(Element("addon-1", "checkbox", "Gift wrap (+€4.99)", checked=True))
    els.append(Element("place", "button", "Place order"))
    return Page("/checkout/review", "Review", tuple(els))


def test_guards_pay_only_for_exactly_what_was_asked():
    ok = review("Item: Vela Pro backpack, 28 L, quantity 1, €80.00", "Shipping: €0.00", "Total: €80.00")
    assert Guards.check(ok, INTENT)[0] == "pay"
    assert Guards.check(review("Item: Vela Pro backpack, 20 L, quantity 1, €80.00", "Total: €80.00"), INTENT)[0] == "abort"
    assert Guards.check(review("Item: Vela Pro backpack, 28 L, quantity 1, €80.00", "Add-on: Gift wrap, €4.99", "Total: €84.99"), INTENT)[0] == "abort"
    assert Guards.check(review("Item: Vela Pro backpack, 28 L, quantity 1, €80.00", "Total: €80.00", box=True), INTENT)[0] == "fix"
    assert Guards.check(review("Item: Vela Pro backpack, 28 L, quantity 1, €120.00", "Order total: €120.00"), INTENT)[0] == "abstain"
    assert Guards.check(review("Item: Vela Pro backpack, 28 L, quantity 1, €80.00", "Total: €80.00",
                               "Sorry, Vela Pro backpack in 28 L is no longer available."), INTENT)[0] == "abstain"


def test_the_model_knows_most_labels_but_not_rare_ones():
    m = Model()
    assert m.button_intent("Add to bag") == "add_to_cart"
    assert m.button_intent("Order with obligation to pay") == "place_order"
    assert m.button_intent("Seal the deal") is None


def test_recipes_replay_by_label_after_ids_change(small_world):
    model = Model()
    pilot = Pilot("recipes", True, True, True, model)
    web = Web(small_world)
    mem = {n: Memory() for n in small_world.retailers}
    import numpy as np

    done = 0
    for it in small_world.intents[:60]:
        s = web.open(it, it.hour)
        res = pilot.run(s, it, mem[it.retailer], np.random.default_rng(1))
        done += res.status == "confirmed"
    assert done > 30
    assert sum(m.replays for m in mem.values()) > sum(m.misses for m in mem.values())


def test_the_ledger_allows_one_unaccounted_payment():
    led = Ledger("sqlite+pysqlite:///:memory:")
    led.open("k1")
    assert led.begin_attempt("k1") == "pending"
    assert led.may_pay("k1") is True
    assert led.may_pay("k1") is False  # the first click is not accounted for yet
    led.settle("k1", "unknown")
    assert led.begin_attempt("k1") == "unknown"  # the next attempt must reconcile first
    assert led.may_pay("k1") is False
    led.settle("k1", "confirmed", "AB1001")
    assert led.get("k1")["order_id"] == "AB1001"
