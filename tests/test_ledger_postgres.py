"""The ledger's one-payment rule under concurrency, on the database named by CAP_DATABASE_URL (PostgreSQL in CI)."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from cap.orders.ledger import Ledger

URL = os.environ.get("CAP_TEST_DATABASE_URL")


@pytest.mark.skipif(not URL, reason="set CAP_TEST_DATABASE_URL to a PostgreSQL database")
def test_twenty_workers_racing_to_pay_get_one_yes():
    led = Ledger(URL)
    key = f"race-{uuid.uuid4().hex[:12]}"
    led.open(key)
    with ThreadPoolExecutor(max_workers=20) as pool:
        answers = list(pool.map(lambda _: led.may_pay(key), range(20)))
    assert answers.count(True) == 1
    assert led.get(key)["placements"] == 1
