# Runbook: intents stuck in `unknown`

**Signal.** Ledger rows in `unknown` older than one hour.

1. `unknown` means a payment click whose result we could not confirm. Never clear it by retrying the checkout.
2. Open the retailer's order history for the shopper's account (the agent does this on its next attempt). If the
   order is there, the next attempt confirms it.
3. If the retailer has no order history, check the card authorisation for the amount and time.
4. Only when both show no order may the state go back to `failed`, which allows one more payment.
