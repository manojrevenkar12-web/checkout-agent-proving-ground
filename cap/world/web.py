"""A browser session on a simulated retailer, as a computer-use agent sees it: an accessibility tree of elements
with roles and labels, and four actions (click, fill, select, check) plus one URL (the order history).

The session enforces the retailer's rules: required fields, its bot defence (pacing, sessions per hour, human
checks, blocks), price changes between cart and review, stock that disappears, payments that are declined, and
payments that succeed while the page says something went wrong. Every order placed is written to the world's
order book, which is the truth the evaluation grades against.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from cap import settings
from cap.world.luck import stream
from cap.world.shops import Intent, World, eid


@dataclass(frozen=True)
class Element:
    id: str
    role: str  # text, button, textbox, select, checkbox, link
    label: str
    value: str = ""
    options: tuple[str, ...] = ()
    checked: bool = False


@dataclass(frozen=True)
class Page:
    url: str
    title: str
    elements: tuple[Element, ...]

    def texts(self) -> list[str]:
        return [e.label for e in self.elements if e.role == "text"]

    def find(self, role: str, label: str) -> Element | None:
        return next((e for e in self.elements if e.role == role and e.label == label), None)


@dataclass(frozen=True)
class Action:
    kind: str  # click, fill, select, check, uncheck, goto
    target: str = ""  # element id, or a URL for goto
    value: str = ""


@dataclass
class Order:
    oid: str
    retailer: str
    intent_id: str
    day: int
    hour: int
    lines: list[tuple[str, str, int, float]]  # product id, variant, qty, unit price
    addon: float
    total: float


@dataclass
class Web:
    """One run of the world for one design: the retailers' state that sessions change, and the order book."""

    world: World
    orders: dict[str, list[Order]] = field(default_factory=lambda: defaultdict(list))
    sessions: dict[tuple, int] = field(default_factory=lambda: defaultdict(int))
    challenges: dict[tuple, int] = field(default_factory=lambda: defaultdict(int))
    attempts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    placements: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    newsletter_signups: int = 0
    next_oid: int = 1000

    def open(self, intent: Intent, hour: int) -> Session:
        key = (intent.retailer, intent.day, hour)
        self.sessions[key] += 1
        n = self.attempts[intent.id]
        self.attempts[intent.id] += 1
        return Session(self, intent, hour, n, self.sessions[key])


STEPS = ["cookie", "product", "popup", "cart", "shipping", "payment", "review"]


class Session:
    def __init__(self, web: Web, intent: Intent, hour: int, attempt: int, nth_this_hour: int):
        self.web = web
        self.world = web.world
        self.intent = intent
        self.retailer = self.world.retailers[intent.retailer]
        self.layout = self.retailer.layouts[intent.day]
        self.day = intent.day
        self.hour = hour
        self.attempt = attempt
        self.fate = self.world.fates[intent.id]
        self.rng = stream(self.world.seed, "session", intent.id, attempt)
        self.ms = 0.0
        self.last_action_ms: float | None = None
        self.suspicious = nth_this_hour > self.retailer.defence["sessions_per_hour"]
        cfg = settings.world()["defence"]
        self.challenge_p = cfg["challenge_when_suspicious"]
        self.block_after = cfg["block_after_challenges"]
        self.blocked = self.web.challenges[(intent.retailer, intent.day, hour)] >= self.block_after
        steps = [s for s in STEPS if (s != "cookie" or self.layout["cookie"]) and (s != "popup" or self.layout["popup"])]
        self.steps = steps
        self.step = 0
        self.state = "checkout"  # checkout, challenge, blocked, confirmed, error, declined, history
        p = self.retailer.by_id[intent.product_id]
        self.product = p
        self.variant = p.variants[self.layout["variant_default"] % len(p.variants)]
        self.qty = "1"
        self.cart: list[tuple[str, int]] = []
        self.addon = self.layout["addon_default"]
        self.address: dict[str, str] = {}
        self.payment = "Saved card •••• 4242"
        self.message = ""
        self.last_oid = ""
        self.history: list[str] = []
        if self.blocked:
            self.state = "blocked"

    # -- what the agent sees ---------------------------------------------------------------------------------

    def _id(self, key: str) -> str:
        return eid(self.layout["salt"], key)

    def observe(self) -> Page:
        L, T = self.layout["labels"], self.layout["titles"]
        els: list[Element] = []
        if self.state == "blocked":
            return Page("/blocked", "Too many requests", (Element(self._id("t429"), "text", "You have sent too many requests. Please try again later."),))
        if self.state == "challenge":
            return Page("/challenge", "One more step", (
                Element(self._id("tch"), "text", "Please confirm you are human to continue."),
                Element(self._id("captcha"), "checkbox", "I'm not a robot"),
            ))
        if self.state == "history":
            rows = [Element(self._id(f"o{o.oid}"), "text",
                            f"Order {o.oid} · day {o.day} {o.hour:02d}:00 · " + "; ".join(
                                f"{self.retailer.by_id[pid].title}, {v} × {q}" for pid, v, q, _ in o.lines) + f" · €{o.total:.2f}")
                    for o in self.web.orders[self.intent.id]]
            if not rows:
                rows = [Element(self._id("tnone"), "text", "You have no orders yet.")]
            return Page("/account/orders", "Your orders", tuple(rows))
        if self.state == "confirmed":
            return Page("/confirmation", "Thank you", (Element(self._id("tok"), "text", f"Thank you! Order {self.last_oid} is confirmed."),))
        if self.state == "declined":
            return Page("/payment-failed", "Payment declined", (Element(self._id("tdec"), "text", "Your payment was declined by your bank."),))
        if self.state == "error":
            return Page("/error", "Something went wrong", (
                Element(self._id("terr"), "text", "Something went wrong. Please try again."),
                Element(self._id("retry"), "button", "Try again"),
            ))
        step = self.steps[self.step]
        if self.message:
            els.append(Element(self._id("msg"), "text", self.message))
        title = ""
        if step == "cookie":
            title = "We value your privacy"
            els += [Element(self._id("tcookie"), "text", "We use cookies to improve your experience."),
                    Element(self._id("accept_cookies"), "button", L["accept_cookies"]),
                    Element(self._id("reject_cookies"), "button", L["reject_cookies"])]
        elif step == "product":
            title = self.product.title
            els += [Element(self._id("ptitle"), "text", self.product.title),
                    Element(self._id("pprice"), "text", f"€{self.retailer.price(self.product.id, self.day):.2f}"),
                    Element(self._id("variant"), "select", L["variant"], self.variant, self.product.variants),
                    Element(self._id("qty"), "textbox", L["quantity"], self.qty),
                    Element(self._id("add_to_cart"), "button", L["add_to_cart"])]
        elif step == "popup":
            title = "Get 10% off your next order"
            els += [Element(self._id("tpop"), "text", "Join our newsletter for deals and news."),
                    Element(self._id("accept_popup"), "button", L["accept_popup"]),
                    Element(self._id("decline_popup"), "button", L["decline_popup"])]
        elif step == "cart":
            title = T["cart"]
            price = self.retailer.price(self.product.id, self.day)
            for v, q in self.cart:
                els.append(Element(self._id(f"line{v}"), "text", f"{self.product.title} | {v} | qty {q} | €{price * q:.2f}"))
            if self.layout["addon_on"] == "cart":
                els.append(self._addon_box())
            els.append(Element(self._id("checkout"), "button", L["checkout"]))
        elif step == "shipping":
            title = T["shipping"]
            for i, f in enumerate(self.layout["address"]):
                els.append(Element(self._id(f"addr{i}"), "textbox", f, self.address.get(f, "")))
            els.append(Element(self._id("continue"), "button", L["continue"]))
        elif step == "payment":
            title = T["payment"]
            els += [Element(self._id("pay"), "select", "Payment method", self.payment, ("Saved card •••• 4242", "PayPal", "Invoice")),
                    Element(self._id("to_review"), "button", L["to_review"])]
        elif step == "review":
            title = T["review"]
            unit = self._review_unit()
            for v, q in self.cart:
                els.append(Element(self._id(f"rev{v}"), "text", f"Item: {self.product.title}, {v}, quantity {q}, €{unit * q:.2f}"))
            if self.addon:
                els.append(Element(self._id("revaddon"), "text", f"Add-on: {self.layout['addon_name']}, €{self.layout['addon_price']:.2f}"))
            if self.layout["addon_on"] == "review":
                els.append(self._addon_box())
            els.append(Element(self._id("revship"), "text", "Shipping: €0.00"))
            els.append(Element(self._id("revtotal"), "text", f"{self.retailer.total_label}: €{self._total():.2f}"))
            if self.fate.stock_out:
                els.append(Element(self._id("oos"), "text", f"Sorry, {self.product.title} in {self.cart[0][0] if self.cart else ''} is no longer available."))
            else:
                els.append(Element(self._id("place_order"), "button", L["place_order"]))
        return Page(f"/checkout/{step}", title, tuple(els))

    def _addon_box(self) -> Element:
        return Element(self._id("addon"), "checkbox", f"{self.layout['addon_name']} (+€{self.layout['addon_price']:.2f})", checked=self.addon)

    def _review_unit(self) -> float:
        return round(self.retailer.price(self.product.id, self.day) * (1 + self.fate.price_rise), 2)

    def _total(self) -> float:
        unit = self._review_unit()
        return round(sum(unit * q for _, q in self.cart) + (self.layout["addon_price"] if self.addon else 0.0), 2)

    # -- what the agent does ---------------------------------------------------------------------------------

    def act(self, action: Action, think_ms: float) -> Page:
        lo, hi = self.retailer.checkout["page_ms"]
        gap = think_ms
        self.ms += think_ms + float(self.rng.uniform(lo, hi))
        if gap < self.retailer.defence["min_ms"]:
            self.suspicious = True
        self.message = ""
        self.history.append(f"{action.kind} {action.target}")
        if action.kind == "goto":
            if action.target == "/account/orders":
                self.state = "history"
            return self.observe()
        page = self.observe()
        el = next((e for e in page.elements if e.id == action.target), None)
        if el is None:
            self.message = "That element is not on this page."
            return self.observe()
        before = self.state, self.step
        self._apply(el, action)
        if (self.state, self.step) != before and self.state == "checkout" and self.suspicious:
            hour_key = (self.intent.retailer, self.day, self.hour)
            if self.rng.random() < self.challenge_p:
                self.web.challenges[hour_key] += 1
                self.state = "challenge"
        return self.observe()

    def _key(self, el: Element) -> str:
        for key in ("add_to_cart", "checkout", "continue", "to_review", "place_order", "accept_popup", "decline_popup",
                    "accept_cookies", "reject_cookies", "retry", "variant", "qty", "addon", "pay", "captcha"):
            if el.id == self._id(key):
                return key
        if el.id.startswith("addr"):
            return "addr"
        return ""

    def _apply(self, el: Element, action: Action) -> None:
        key = self._key(el)
        if self.state == "error" and key == "retry":
            self.state = "checkout"
            self.step = self.steps.index("review")
            return
        if self.state != "checkout":
            return
        if action.kind == "select" and key == "variant" and action.value in el.options:
            self.variant = action.value
        elif action.kind == "select" and key == "pay" and action.value in el.options:
            self.payment = action.value
        elif action.kind == "fill" and key == "qty":
            self.qty = action.value
        elif action.kind == "fill" and key == "addr":
            self.address[el.label] = action.value
        elif action.kind in ("check", "uncheck") and key == "addon":
            self.addon = action.kind == "check"
        elif action.kind == "click":
            self._click(key)

    def _advance(self) -> None:
        self.step = min(self.step + 1, len(self.steps) - 1)

    def _click(self, key: str) -> None:
        step = self.steps[self.step]
        if step == "cookie" and key in ("accept_cookies", "reject_cookies"):
            self._advance()
        elif step == "product" and key == "add_to_cart":
            try:
                q = int(self.qty)
            except ValueError:
                self.message = "Please enter a quantity."
                return
            if q < 1:
                self.message = "Please enter a quantity."
                return
            self.cart.append((self.variant, q))
            self._advance()
        elif step == "popup" and key in ("accept_popup", "decline_popup"):
            if key == "accept_popup":
                self.web.newsletter_signups += 1
            self._advance()
        elif step == "cart" and key == "checkout":
            self._advance()
        elif step == "shipping" and key == "continue":
            missing = [f for f in self.layout["address"] if "optional" not in f and not self.address.get(f)]
            if missing:
                self.message = f"Please fill in {missing[0]}."
                return
            self._advance()
        elif step == "payment" and key == "to_review":
            self._advance()
        elif step == "review" and key == "place_order" and not self.fate.stock_out:
            self._place()

    def _place(self) -> None:
        n = self.web.placements[self.intent.id]
        self.web.placements[self.intent.id] += 1
        rng = stream(self.world.seed, "payment", self.intent.id, n)
        c = self.retailer.checkout
        if rng.random() < c["declined"]:
            self.state = "declined"
            return
        self.web.next_oid += 1
        oid = f"{self.retailer.name[:2].upper()}{self.web.next_oid}"
        unit = self._review_unit()
        order = Order(oid, self.retailer.name, self.intent.id, self.day, self.hour,
                      [(self.product.id, v, q, unit) for v, q in self.cart],
                      self.layout["addon_price"] if self.addon else 0.0, self._total())
        self.web.orders[self.intent.id].append(order)
        self.last_oid = oid
        self.state = "error" if rng.random() < c["ambiguous_payment"] else "confirmed"
