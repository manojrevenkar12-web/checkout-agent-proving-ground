"""The generated README block and the gate, on the committed reports."""

from cap.eval import gate, report


def test_readme_block_matches_the_reports():
    dev = report.load("dev")
    if dev is None:
        return
    held = report.load("heldout")
    block = report.block(dev, held, gate.check(dev), gate.check(held) if held else None)
    assert block in report.README.read_text()
    assert gate.check(dev)["passed"]


def test_charts_render():
    dev = report.load("dev")
    if dev is None:
        return
    assert "<svg" in report.chart_days(dev) and "<svg" in report.chart_designs(dev)
