# 0005. Pace like a person, budget sessions, and hand off instead of defeating human checks

**Context.** Retailers rate-limit and challenge clients that act too fast or open too many sessions. Defeating
those checks is an arms race and a breach of the retailer's terms.

**Decision.** The platform waits a human-like interval between actions, keeps a per-retailer budget of sessions
per hour that halves after a challenge and grows slowly otherwise, opens a breaker that pages on-call when a
retailer keeps challenging us, and after repeated challenges hands the checkout to the shopper to finish in their
own browser.

**Consequences.** Some intents wait an hour or are handed off. The ablation without pacing and budgets shows the
alternative: challenges, blocks for the rest of the hour, and almost nothing bought.
