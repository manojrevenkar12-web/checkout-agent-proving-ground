# 0003. Code reads the review page and decides whether to pay

**Context.** The model checks its own review page with measured misreads: it overlooks a pre-checked add-on about
a third of the time and does not compare the total with the budget about a third of the time.

**Decision.** Before the payment click, `Guards.check` parses the review page: exactly one item line with the
intent's title, size and quantity; no add-on line; a total within the budget; no out-of-stock notice. A checked
paid add-on is unchecked. Otherwise the agent abstains (tells the shopper why) or aborts and retries later. Any
paid checkbox on any page is unchecked by code.

**Consequences.** Wrong orders go to zero in the simulation. The parser depends on the review page carrying item
lines and a total; a retailer that hides them gets no payment until the guard learns its format.
