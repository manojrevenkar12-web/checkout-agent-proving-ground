"""Drives one checkout session: what to do on each page, and when to stop.

Three pilots share one loop:
- "script": steps recorded by element id on day 0, never repaired (the status quo).
- "model": the computer-use model plans every page (it reads labels, so it survives most changes, but every
  page costs a model call, and it checks its own work with the misreads measured for it).
- "recipes": steps recorded by role and label on pages the agent has seen before, replayed without the model;
  the model is called only for a page whose fingerprint is new or whose recipe no longer matches, and the
  repaired steps become the new recipe.

The model proposes; code decides. With guards on, code unchecks paid add-ons nobody asked for, and before the one
irreversible click it reads the review page and refuses to pay for the wrong item, the wrong size or quantity,
an add-on, or a total above the shopper's budget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from cap import settings
from cap.world.web import Action, Element, Page

BUTTON_PRIORITY = ["decline_popup", "reject_cookies", "retry", "place_order", "to_review", "checkout", "continue", "add_to_cart"]
SAFE_UNKNOWN_AVOID = {"accept_popup", "accept_cookies"}
TERMINAL = {"/confirmation", "/error", "/payment-failed", "/challenge", "/blocked", "/account/orders"}


@dataclass(frozen=True)
class Step:
    kind: str  # select, fill, check, uncheck, click
    role: str
    label: str
    param: str = ""  # variant, quantity, name, street, postcode, city, or "" for clicks
    element_id: str = ""  # scripts replay by id


@dataclass
class Result:
    status: str  # confirmed, unknown, declined, abstained, challenged, blocked, failed
    reason: str = ""
    order_id: str = ""
    model_steps: int = 0
    ms: float = 0.0
    placed: bool = False


@dataclass
class Memory:
    """What a pilot carries between sessions for one retailer."""

    recipes: dict[tuple, list[Step]] = field(default_factory=dict)
    script: dict[str, list[Step]] = field(default_factory=dict)  # url -> steps, recorded on day 0
    misses: int = 0
    replays: int = 0


def norm(s: str) -> str:
    return " ".join(s.lower().split())


class Model:
    """The computer-use model as the platform uses it: it reads a page and proposes steps."""

    def __init__(self) -> None:
        cfg = settings.platform()["model"]
        self.cfg = cfg
        self.intent_of = {norm(w): k for k, words in cfg["lexicon"].items() for w in words}
        self.field_of = {norm(w): k for k, words in cfg["fields"].items() for w in words}

    def button_intent(self, label: str) -> str | None:
        return self.intent_of.get(norm(label))

    def plan(self, page: Page, intent, rng: np.random.Generator, careful: bool) -> list[Step]:
        """Steps for this page, ending in one click. `careful` is the model checking its own review page."""
        c = self.cfg
        steps: list[Step] = []
        for e in page.elements:
            if e.role == "select" and intent.variant in e.options:
                if e.value != intent.variant and rng.random() >= c["misread_variant"]:
                    steps.append(Step("select", e.role, e.label, "variant"))
            elif e.role == "textbox":
                f = self.field_of.get(norm(e.label))
                if f is not None:
                    steps.append(Step("fill", e.role, e.label, f))
            elif e.role == "checkbox" and "€" in e.label and e.checked and rng.random() >= c["misread_addon"]:
                steps.append(Step("uncheck", e.role, e.label))
        buttons = [e for e in page.elements if e.role == "button"]
        if not buttons:
            return steps
        known = {b.id: self.button_intent(b.label) for b in buttons}
        ranked = sorted((b for b in buttons if known[b.id] in BUTTON_PRIORITY), key=lambda b: BUTTON_PRIORITY.index(known[b.id]))
        unknown = [b for b in buttons if known[b.id] is None]
        if ranked and known[ranked[0].id] == "place_order" and careful and self.would_refuse(page, intent, rng):
            return steps + [Step("refuse", "", "")]
        if ranked:
            choice = ranked[0]
            if rng.random() < c["error_known"] and len(buttons) > 1:
                choice = buttons[int(rng.integers(len(buttons)))]
        elif unknown:
            if rng.random() < c["error_unknown"]:
                return steps + [Step("stall", "", "")]
            choice = unknown[0]
        else:
            choice = buttons[int(rng.integers(len(buttons)))]
        return steps + [Step("click", "button", choice.label)]

    def would_refuse(self, page: Page, intent, rng: np.random.Generator) -> bool:
        """The model's own check before paying, with its measured misreads."""
        texts = page.texts()
        if any(t.startswith("Add-on:") for t in texts) and rng.random() >= self.cfg["misread_addon"]:
            return True
        total = Guards.total(texts)
        return total is not None and total > intent.max_total + 1e-9 and rng.random() >= self.cfg["misread_budget"]


class Guards:
    """Code that reads the review page and decides whether to pay. It never relies on the model."""

    _money = re.compile(r"€\s?(-?\d+(?:\.\d{1,2})?)")
    _item = re.compile(r"^Item: (?P<title>.+), (?P<variant>[^,]+), quantity (?P<qty>\d+), €(?P<amount>\d+(?:\.\d{1,2})?)$")

    @staticmethod
    def total(texts: list[str]) -> float | None:
        labels = settings.platform()["guards"]["total_labels"]
        for t in texts:
            head, _, tail = t.partition(":")
            if norm(head) in labels:
                m = Guards._money.search(tail)
                if m:
                    return float(m.group(1))
        return None

    @staticmethod
    def check(page: Page, intent) -> tuple[str, str]:
        """('pay' | 'fix' | 'abstain' | 'abort', reason)."""
        g = settings.platform()["guards"]
        texts = page.texts()
        if any(any(w in t.lower() for w in g["stock_out_words"]) for t in texts):
            return "abstain", "out of stock at checkout"
        box = next((e for e in page.elements if e.role == "checkbox" and "€" in e.label and e.checked), None)
        if box is not None:
            return "fix", "paid add-on was checked"
        items = [Guards._item.match(t) for t in texts if t.startswith(g["item_prefix"])]
        if len(items) != 1 or items[0] is None:
            return "abort", f"expected one item line, found {len(items)}"
        m = items[0]
        if m["title"] != intent.title or m["variant"] != intent.variant or int(m["qty"]) != intent.qty:
            return "abort", f"cart holds {m['title']} {m['variant']} x{m['qty']}"
        if any(t.startswith(g["addon_prefix"]) for t in texts):
            return "abort", "an add-on is in the order"
        total = Guards.total(texts)
        if total is None:
            return "abort", "no total on the review page"
        if total > intent.max_total + 1e-9:
            return "abstain", f"total €{total:.2f} is above the budget €{intent.max_total:.2f}"
        return "pay", ""


def complete(page: Page, steps: list[Step]) -> list[Step]:
    """Recorded steps always set the size and the quantity, whatever the page started with."""
    out = list(steps)
    sel = next((e for e in page.elements if e.role == "select" and e.label != "Payment method"), None)
    if sel is not None and not any(s.kind == "select" for s in out):
        out.insert(0, Step("select", sel.role, sel.label, "variant", sel.id))
    return out


def fingerprint(page: Page) -> tuple:
    return (page.url, tuple(sorted((e.role, e.label) for e in page.elements if e.role != "text")))


def values(intent) -> dict[str, str]:
    name, street, postcode, city = intent.address
    return {"variant": intent.variant, "quantity": str(intent.qty), "name": name, "street": street, "postcode": postcode, "city": city}


def find(page: Page, step: Step, by_id: bool) -> Element | None:
    if by_id:
        return next((e for e in page.elements if e.id == step.element_id), None)
    return page.find(step.role, step.label)


class Pilot:
    def __init__(self, kind: str, guards: bool, ledger: bool, pacing: bool, model: Model):
        self.kind = kind
        self.guards = guards
        self.ledger = ledger
        self.pacing = pacing
        self.model = model
        a = settings.platform()["agent"]
        self.think = tuple(a["think_ms"])
        self.fast = a["fast_think_ms"]
        self.max_steps = a["max_steps"]

    def _think(self, rng: np.random.Generator) -> float:
        if self.kind == "model":
            return float(self.model.cfg["latency_ms"])  # a computer-use model looks again before every action
        return float(rng.uniform(*self.think)) if self.pacing else float(self.fast)

    def _do(self, session, page: Page, step: Step, intent, rng, by_id: bool) -> Page | None:
        el = find(page, step, by_id)
        if el is None:
            return None
        v = values(intent)
        if step.kind == "click":
            return session.act(Action("click", el.id), self._think(rng))
        if step.kind == "select":
            return session.act(Action("select", el.id, v[step.param]), self._think(rng))
        if step.kind == "fill":
            return session.act(Action("fill", el.id, v[step.param]), self._think(rng))
        if step.kind in ("check", "uncheck"):
            return session.act(Action(step.kind, el.id), self._think(rng))
        return page

    def run(self, session, intent, memory: Memory, rng: np.random.Generator, reconcile_first: bool = False, before_pay=None) -> Result:
        res = Result("failed")
        page = session.observe()
        if reconcile_first:
            found = self.reconcile(session, intent, rng)
            res.ms = session.ms
            if found:
                return Result("confirmed", "found in order history", found, 0, session.ms)
            session.state = "checkout"
            page = session.observe()
        for _ in range(self.max_steps):
            res.ms = session.ms
            path = page.url
            if path == "/confirmation":
                m = re.search(r"Order (\S+) is confirmed", " ".join(page.texts()))
                res.status, res.order_id, res.placed = "confirmed", m.group(1) if m else "", True
                break
            if path == "/payment-failed":
                res.status, res.reason, res.placed = "declined", "payment declined", True
                break
            if path == "/challenge":
                res.status, res.reason = "challenged", "the retailer asked for a human check"
                break
            if path == "/blocked":
                res.status, res.reason = "blocked", "the retailer is rate-limiting us"
                break
            if path == "/error":
                res.placed = True
                if self.ledger:
                    found = self.reconcile(session, intent, rng)
                    res.ms = session.ms
                    if found:
                        res.status, res.order_id, res.reason = "confirmed", found, "reconciled after an error page"
                    else:
                        res.status, res.reason = "unknown", "error page and no order in the history"
                    break
            if self.guards and path == "/checkout/review":
                verdict, why = Guards.check(page, intent)
                if verdict == "fix":
                    box = next(e for e in page.elements if e.role == "checkbox" and e.checked and "€" in e.label)
                    page = session.act(Action("uncheck", box.id), self._think(rng))
                    continue
                if verdict in ("abstain", "abort"):
                    res.status, res.reason = ("abstained" if verdict == "abstain" else "failed"), why
                    break
            if self.guards:
                box = next((e for e in page.elements if e.role == "checkbox" and "€" in e.label and e.checked), None)
                if box is not None:
                    page = session.act(Action("uncheck", box.id), self._think(rng))
                    continue
            steps, by_id = self._steps(page, intent, memory, rng, res)
            if steps is None:
                res.status, res.reason = "failed", "no way forward on " + path
                break
            if steps and steps[-1].kind == "refuse":
                res.status, res.reason = "abstained", "the model declined to pay"
                break
            if before_pay is not None and path == "/checkout/review" and any(st.kind == "click" for st in steps) and not before_pay():
                res.status, res.reason = "failed", "the ledger holds an unaccounted payment for this intent"
                break
            new = page
            ok = True
            for st in steps:
                if st.kind == "stall":
                    ok = False
                    break
                nxt = self._do(session, new, st, intent, rng, by_id)
                if nxt is None:
                    ok = False
                    break
                new = nxt
            if ok and self.kind == "recipes" and new.url != page.url and page.url.startswith("/checkout/"):
                memory.recipes[fingerprint(page)] = complete(page, [s for s in steps if s.kind != "stall" and (s.kind != "uncheck" or not self.guards)])
            if not ok and self.kind == "recipes":
                memory.recipes.pop(fingerprint(page), None)
            page = new
        res.ms = session.ms
        return res

    def _steps(self, page: Page, intent, memory: Memory, rng, res: Result) -> tuple[list[Step] | None, bool]:
        if self.kind == "script":
            steps = memory.script.get(page.url)
            if steps is None:
                return None, True
            if any(find(page, s, True) is None for s in steps):
                return None, True
            return steps, True
        if self.kind == "recipes":
            recipe = memory.recipes.get(fingerprint(page))
            if recipe is not None and all(find(page, s, False) is not None for s in recipe):
                memory.replays += 1
                return recipe, False
            memory.misses += 1
        steps = self.model.plan(page, intent, rng, careful=not self.guards)
        res.model_steps += max(1, len(steps))  # one model call per action it takes
        return steps, False

    def reconcile(self, session, intent, rng) -> str:
        """Opens the order history and looks for this intent's order. Returns its id, or ''."""
        page = session.act(Action("goto", "/account/orders"), self._think(rng))
        want = f"{intent.title}, {intent.variant} × {intent.qty}"
        for t in page.texts():
            if want in t and f"day {intent.day} " in t:
                m = re.match(r"Order (\S+)", t)
                if m:
                    return m.group(1)
        return ""


def record_script(web_factory, retailer: str, intent, model: Model) -> dict[str, list[Step]]:
    """A developer records a script on day 0 by walking the checkout carefully once; steps keep element ids."""
    web = web_factory()
    session = web.open(intent, 0)
    script: dict[str, list[Step]] = {}
    perfect = np.random.default_rng(0)
    cfg = dict(model.cfg)
    model.cfg = {**cfg, "error_known": 0.0, "error_unknown": 0.0, "misread_addon": 0.0, "misread_variant": 0.0, "misread_budget": 1.0}
    try:
        page = session.observe()
        for _ in range(30):
            if not page.url.startswith("/checkout/"):
                break
            box = next((e for e in page.elements if e.role == "checkbox" and "€" in e.label and e.checked), None)
            steps = model.plan(page, intent, perfect, careful=False)
            if box is not None:
                steps = [Step("uncheck", box.role, box.label)] + [s for s in steps if s.kind != "uncheck"]
            steps = complete(page, [Step(s.kind, s.role, s.label, s.param, (page.find(s.role, s.label) or Element("", "", "")).id) for s in steps])
            script[page.url] = steps
            pilot = Pilot("script", False, False, True, model)
            new = page
            for s in steps:
                nxt = pilot._do(session, new, s, intent, perfect, True)
                if nxt is None:
                    break
                new = nxt
            if new.url == page.url:
                break
            page = new
    finally:
        model.cfg = cfg
    return script
