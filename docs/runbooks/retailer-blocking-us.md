# Runbook: a retailer is challenging or blocking our sessions

**Page.** The breaker opened for a retailer (too many challenges or blocks in the last window).

1. Check the retailer's challenge and block counts for the last hours and the session budget the platform holds
   for it. A drop or sale hour concentrates intents; the budget will have halved already.
2. Do not raise pacing speed or the session budget to get through. Leave the breaker to cool down.
3. If it keeps happening at normal volume, contact the retailer's partner team: an API or an allow-listed agent
   identity is the fix, not evasion.
4. Intents that reach their attempt limit are handed to the shopper automatically; check that the hand-off
   messages went out.
