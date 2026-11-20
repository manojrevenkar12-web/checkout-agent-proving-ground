"""The world: deterministic, its truth hidden, its checkouts and defences behave as specified."""

from cap.world.shops import build
from cap.world.web import Action, Web


def test_same_seed_same_world(small_world, monkeypatch, small_cfg):
    again = build(7101)
    assert [i.id for i in again.intents] == [i.id for i in small_world.intents]
    assert [r.layouts for r in again.retailers.values()] == [r.layouts for r in small_world.retailers.values()]


def test_intents_carry_no_hidden_fate(small_world):
    pub = small_world.intents[0].public()
    assert "price_rise" not in pub and "stock_out" not in pub


def _walk_to(session, url):
    for _ in range(20):
        page = session.observe()
        if page.url == url:
            return page
        buttons = [e for e in page.elements if e.role == "button"]
        if page.url == "/checkout/shipping":
            for e in page.elements:
                if e.role == "textbox":
                    session.act(Action("fill", e.id, "x"), 2000)
        prefer = [b for b in buttons if b.id.startswith(("reject", "decline", "add-to", "checkout", "continue", "to-review"))]
        session.act(Action("click", (prefer or buttons)[0].id), 2000)
    raise AssertionError(f"never reached {url}")


def test_required_fields_block_the_shipping_step(small_world):
    web = Web(small_world)
    it = next(i for i in small_world.intents if not small_world.fates[i.id].stock_out)
    s = web.open(it, it.hour)
    page = _walk_to(s, "/checkout/shipping")
    cont = next(e for e in page.elements if e.role == "button")
    page = s.act(Action("click", cont.id), 2000)
    assert page.url == "/checkout/shipping" and any("Please fill in" in t for t in page.texts())


def test_every_placed_order_is_in_the_book_and_the_history(small_world):
    web = Web(small_world)
    it = next(i for i in small_world.intents if not small_world.fates[i.id].stock_out)
    s = web.open(it, it.hour)
    page = _walk_to(s, "/checkout/review")
    place = next(e for e in page.elements if e.role == "button")
    page = s.act(Action("click", place.id), 2000)
    assert page.url in ("/confirmation", "/error", "/payment-failed")
    if page.url != "/payment-failed":
        assert len(web.orders[it.id]) == 1
        hist = s.act(Action("goto", "/account/orders"), 2000)
        assert any(web.orders[it.id][0].oid in t for t in hist.texts())


def test_acting_faster_than_a_person_gets_challenged(small_world):
    web = Web(small_world)
    seen = False
    for it in small_world.intents[:40]:
        s = web.open(it, it.hour)
        for _ in range(8):
            page = s.observe()
            if page.url == "/challenge":
                seen = True
                break
            buttons = [e for e in page.elements if e.role == "button"]
            if not buttons:
                break
            s.act(Action("click", buttons[-1].id), 50)
    assert seen


def test_checkouts_change_over_time():
    w = build(7101)
    assert any(r.changes for r in w.retailers.values())
    r = next(r for r in w.retailers.values() if r.changes)
    day = r.changes[0][0]
    assert r.layouts[day] != r.layouts[day - 1]
