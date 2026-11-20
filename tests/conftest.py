import copy

import pytest

from cap import settings
from cap.world.shops import build


@pytest.fixture(scope="session")
def small_cfg():
    cfg = copy.deepcopy(settings.world())
    cfg.update(days=4, retailers=4, products_per_retailer=30, intents_per_retailer_per_day=12)
    return cfg


@pytest.fixture
def small_world(monkeypatch, small_cfg):
    monkeypatch.setattr(settings, "world", lambda: small_cfg)
    return build(7101)
