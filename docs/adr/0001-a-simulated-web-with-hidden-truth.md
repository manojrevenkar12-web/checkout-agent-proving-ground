# 0001. Measure on a simulated web with a hidden order book, every design on the same luck

**Context.** A checkout agent's failures are rare and expensive: a wrong size, a pre-checked add-on, a second
order after an error page. Live retailers cannot be replayed, and their order books are not ours to read.

**Decision.** `cap/world` simulates retailers whose checkouts are built from varied vocabularies and change on
some days (new labels, new ids, pop-ups, cookie banners, moved and pre-checked add-ons, shifted size defaults,
split address forms, labels a model has rarely seen), defend themselves (pacing, sessions per hour, human checks,
blocks), raise prices between cart and review, run out of stock, decline payments, and sometimes place an order
while showing an error. Every order lands in an order book the platform never reads. Draws are keyed by seed,
intent, attempt and placement, so every design meets the same events.

**Consequences.** The numbers are about this simulated web. The agent sees an accessibility tree, not pixels;
the computer-use model is simulated with error rates written in `config/platform.yaml`.
