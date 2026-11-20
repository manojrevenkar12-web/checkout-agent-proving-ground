"""python -m cap.eval.cli evaluate | heldout | gate | readme"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys

from cap import settings
from cap.eval import gate, report
from cap.eval.run import evaluate
from cap.settings import CONFIG

LOCK = CONFIG / "heldout.lock"


def _write(name: str, rep: dict) -> None:
    report.REPORTS.mkdir(parents=True, exist_ok=True)
    (report.REPORTS / f"{name}.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")


def _sha() -> str:
    h = hashlib.sha256()
    for n in ("world.yaml", "platform.yaml", "gate.yaml"):
        h.update((CONFIG / n).read_bytes())
    return h.hexdigest()[:16]


def readme(check: bool) -> int:
    dev = report.load("dev")
    if dev is None:
        print("no reports/dev.json yet")
        return 0
    held = report.load("heldout")
    new_block = report.block(dev, held, gate.check(dev), gate.check(held) if held else None)
    text = report.README.read_text()
    new = report.render_readme(text, new_block)
    if check:
        if new != text:
            print("README results block is out of date: python -m cap.eval.cli readme")
            return 1
        return 0
    report.README.write_text(new)
    report.write_charts(dev)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("evaluate")
    sub.add_parser("heldout")
    g = sub.add_parser("gate")
    g.add_argument("--heldout", action="store_true")
    r = sub.add_parser("readme")
    r.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "evaluate":
        rep = evaluate(settings.world()["seeds"])
        _write("dev", rep)
        readme(False)
        print(json.dumps(gate.check(rep), indent=2))
        return 0
    if a.cmd == "heldout":
        if LOCK.exists():
            print(f"the held-out worlds were already evaluated: {LOCK.read_text().strip()}")
            return 1
        seeds = settings.heldout()["seeds"]
        LOCK.write_text(json.dumps({"ran_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "config_sha": _sha(), "seeds": seeds}) + "\n")
        rep = evaluate(seeds)
        _write("heldout", rep)
        readme(False)
        print(json.dumps(gate.check(rep), indent=2))
        return 0
    if a.cmd == "gate":
        rep = report.load("heldout" if a.heldout else "dev")
        if rep is None:
            print("no report")
            return 1
        res = gate.check(rep)
        for k, ok in res["checks"].items():
            print(("PASS " if ok else "FAIL ") + k)
        return 0 if res["passed"] else 1
    if a.cmd == "readme":
        return readme(a.check)
    return 2


if __name__ == "__main__":
    sys.exit(main())
