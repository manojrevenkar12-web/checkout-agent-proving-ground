# 0004. One unaccounted payment per intent, reconciled against the order history

**Context.** About 1-4% of payments succeed while the page says "Something went wrong. Please try again." A
retry places a second order; giving up tells the shopper nothing was bought when it was.

**Decision.** The ledger (SQLAlchemy Core; SQLite in tests and simulation, PostgreSQL in CI and production) moves
an intent from `pending` to `submitting` atomically before the click. After an error page the agent opens the
retailer's order history in the same session and confirms the order if it is there; otherwise the intent stays
`unknown` and the next attempt reconciles before it may pay. The API is idempotent on a client key.

**Consequences.** Duplicates go to zero and shoppers are told what happened. A retailer without an order history
page needs another source of truth (an e-mail confirmation, the card authorisation) before retries are allowed.
