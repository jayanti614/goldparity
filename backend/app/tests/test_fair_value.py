import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.analytics.fair_value import to_fair_value  # noqa: E402
from app.db import BhavcopyRecord  # noqa: E402


def _record(symbol: str, close: float, days_to_expiry: int = 10) -> BhavcopyRecord:
    r = BhavcopyRecord()
    r.symbol = symbol
    r.trade_date = date(2026, 1, 1)
    r.expiry_date = date(2026, 1, 1 + days_to_expiry)
    r.open = r.high = r.low = r.close = close
    r.volume = 100
    r.open_interest = 100
    return r


def test_goldpetal_999_purity_has_zero_purity_effect():
    # GOLDPETAL is already 999 purity and quoted per 1g -> no adjustment needed.
    row = to_fair_value(_record("GOLDPETAL", close=15480.0))
    assert abs(row.price_per_gram_alloy - 15480.0) < 1e-9
    assert abs(row.price_per_gram_999 - 15480.0) < 1e-9
    assert abs(row.purity_effect_pct - 0.0) < 1e-9


def test_goldm_995_purity_gets_scaled_up():
    # GOLDM is 995 purity, quoted per 10g -> price_per_gram_999 should be
    # scaled UP by exactly 999/995 (999-purity alloy is worth more per gram).
    row = to_fair_value(_record("GOLDM", close=154467.0))
    expected_per_gram_alloy = 154467.0 / 10  # quote_per_g = 10
    expected_per_gram_999 = expected_per_gram_alloy * (999 / 995)
    assert abs(row.price_per_gram_alloy - expected_per_gram_alloy) < 1e-6
    assert abs(row.price_per_gram_999 - expected_per_gram_999) < 1e-6
    expected_purity_effect = (999 / 995) - 1
    assert abs(row.purity_effect_pct - expected_purity_effect) < 1e-9


def test_goldguinea_unit_conversion():
    # GOLDGUINEA: 8g lot, quoted per 8g, 999 purity.
    row = to_fair_value(_record("GOLDGUINEA", close=8040.0))
    assert abs(row.price_per_gram_alloy - 1005.0) < 1e-9  # 8040 / 8
    assert abs(row.price_per_gram_999 - 1005.0) < 1e-9  # already 999 purity


def test_days_to_expiry_computed_correctly():
    row = to_fair_value(_record("GOLDPETAL", close=1000.0, days_to_expiry=23))
    assert row.days_to_expiry == 23


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"PASS: {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL: {t.__name__}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
