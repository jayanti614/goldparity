import math
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.analytics.carry import estimate_implied_carry  # noqa: E402
from app.db import BhavcopyRecord  # noqa: E402

TRADE_DATE = date(2026, 1, 1)


def _record(days_to_expiry: int, price_per_gram: float) -> BhavcopyRecord:
    # GOLDPETAL: purity 999 (no purity adjustment), quote_per_g=1 (close == price/gram directly)
    r = BhavcopyRecord()
    r.symbol = "GOLDPETAL"
    r.trade_date = TRADE_DATE
    r.expiry_date = TRADE_DATE + timedelta(days=days_to_expiry)
    r.close = price_per_gram
    r.open = r.high = r.low = price_per_gram
    r.volume = 100
    r.open_interest = 100
    return r


def test_returns_none_with_fewer_than_two_unique_expiries():
    records = [_record(10, 1000.0), _record(10, 1000.5)]  # same days_to_expiry twice
    assert estimate_implied_carry(records) is None


def test_returns_none_with_empty_input():
    assert estimate_implied_carry([]) is None


def test_recovers_known_daily_rate_from_a_perfect_curve():
    # Construct points that lie EXACTLY on log(price) = log(1000) + 0.0005*days
    # -> the fit should recover daily_rate = 0.0005 almost exactly, R^2 ~ 1.0.
    known_daily_rate = 0.0005
    base_price = 1000.0
    days_list = [5, 10, 15, 20]
    records = [
        _record(d, base_price * math.exp(known_daily_rate * d)) for d in days_list
    ]

    est = estimate_implied_carry(records)
    assert est is not None
    assert abs(est.daily_rate - known_daily_rate) < 1e-9
    assert est.r_squared > 0.999
    expected_annualized = (math.exp(known_daily_rate * 365) - 1) * 100
    assert abs(est.annualized_rate_pct - expected_annualized) < 1e-6
    assert est.n_points == 4
    assert est.n_unique_expiries == 4


def test_flat_curve_has_near_zero_carry_rate():
    # All points at the same price regardless of days-to-expiry -> ~0 carry.
    records = [_record(d, 1000.0) for d in (5, 10, 15, 20)]
    est = estimate_implied_carry(records)
    assert est is not None
    assert abs(est.daily_rate) < 1e-9
    assert abs(est.annualized_rate_pct) < 1e-6


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
