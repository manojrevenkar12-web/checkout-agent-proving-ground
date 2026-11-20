# Runbook: a product feed is quarantined

**Page.** A source failed validation twice in a day (a new mapping was proposed and still failed); it keeps its
last good data and nothing new is published from it.

1. Look at a sample of the raw feed: format, field names, price encoding. Most cases are a new encoding (cents
   versus decimals) that the plausibility check refused, which is the check working.
2. If the feed is broken at the source, tell the retailer and leave the quarantine on.
3. If the feed is right and prices really moved more than `ingest.max_price_jump`, confirm a sample by hand and
   lower the check for that run only.
