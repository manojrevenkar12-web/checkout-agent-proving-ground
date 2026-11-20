"""Settings files. The world reads world.yaml; the platform reads platform.yaml; the gate reads gate.yaml."""

from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text())


@cache
def world() -> dict:
    return _load("world.yaml")


@cache
def platform() -> dict:
    return _load("platform.yaml")


@cache
def gate() -> dict:
    return _load("gate.yaml")


@cache
def heldout() -> dict:
    return _load("heldout.yaml")
