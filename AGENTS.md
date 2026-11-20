# Working on checkout-agent-proving-ground

Shopping agents that buy on the open web, and the simulated web they are measured on. Read this first.

## Fast feedback

| What | Command |
|---|---|
| Unit and service tests | `python -m pytest -q` (seconds) and `ruff check .` |
| Ledger race on PostgreSQL | `CAP_TEST_DATABASE_URL=postgresql+psycopg://… python -m pytest -q tests/test_ledger_postgres.py` |
| Full development evaluation | `python -m cap.eval.cli evaluate` (about 4 minutes; rewrites reports/ and the README block) |
| Gate | `python -m cap.eval.cli gate` |
| Service | `uvicorn cap.service.api:app --port 8080` |
| Dashboard | `cd web && pnpm build && pnpm e2e` |

## Invariants

1. **The truth stays in the world.** Product categories, fates (a price rise, a stock-out), the order book and
   feed truth live in `cap/world`. The platform sees pages through `cap.world.web.Session`, feeds as text, and
   intents through `Intent.public()`. Only `cap/eval/grade.py` reads the order book.
2. **The world does not read the platform's settings.** `cap/world` reads `config/world.yaml` only. The model's
   lexicon (`config/platform.yaml`) and the retailers' vocabulary are written separately, on purpose: some labels
   the world uses are not in the lexicon.
3. **Same luck for every design.** Every draw comes from `cap.world.luck.stream(seed, *keys)`, keyed by intent,
   attempt and placement, so every design meets the same shoppers, changes, defences and payment outcomes.
4. **The model proposes, code decides.** The model plans steps; `Guards` reads the review page and decides
   whether to pay; the ledger decides whether a payment click is allowed; pacing, budgets and the breaker decide
   whether to open a session at all.
5. **One unaccounted payment at most.** `Ledger.may_pay` moves an intent to `submitting` atomically; an error page
   after paying is reconciled against the retailer's order history before anything is retried.
6. **Respect the retailer's defences.** The platform paces like a person, budgets sessions per retailer and hour,
   backs off when challenged, and hands the checkout to the shopper instead of trying to defeat a human check.
7. **Settings in config.** Rates, prices, thresholds and the gate are in `config/`.
8. **Generated reports.** `reports/*.json`, `reports/charts/*.svg` and the README block come from `cap.eval`; CI
   re-runs the development evaluation and fails if anything differs.

## The held-out rule

`config/heldout.yaml` lists seeds that are evaluated once, with `python -m cap.eval.cli heldout`, after the gate
passes on the development seeds. The run writes `config/heldout.lock`; the command refuses to run again while it
exists. Nothing is tuned on held-out numbers.
