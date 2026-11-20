# Repeatable tasks

## Add a retailer behaviour to the world
Add it to `config/world.yaml` and `cap/world/web.py` (or `_drift` in `shops.py`), with a test in `tests/test_world.py`.
Run the dev evaluation: every design meets it on the same luck.

## Add a guard
Put the rule in `Guards.check` (`cap/agent/pilot.py`) with a case in `tests/test_agent.py`. A guard may fix
(uncheck), abstain (tell the shopper) or abort (retry later); it never pays when unsure.

## Add a design or ablation
Add switches under `designs` in `config/platform.yaml`, list it in `CHECKOUT` (`cap/eval/run.py`) and `ORDER`
(`cap/eval/report.py`), run `python -m cap.eval.cli evaluate`, commit `reports/` and `README.md`.

## Onboard a feed
Nothing to write: the mapping is proposed from a sample and validated. Watch `pages` in the ingestion report; a
quarantined source pages on-call and keeps its last good data (runbook: feed-quarantined).

## Run the held-out evaluation (once)
After the dev gate passes and nothing will change: `python -m cap.eval.cli heldout`, then commit
`reports/heldout.json`, `README.md` and `config/heldout.lock` together.
