import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.analytics.delivery_risk import (  # noqa: E402
    DELIVERY_BUFFER_DAYS,
    filter_signals_by_delivery_risk,
    is_within_delivery_risk_window,
)


def test_far_from_expiry_is_safe():
    assert is_within_delivery_risk_window(days_to_expiry=30, holding_period_days=5) is False


def test_holding_period_pushes_into_risk_window():
    # 8 days to expiry, want to hold 5 days -> 3 days would remain,
    # which is inside the default 5-day buffer -> risky.
    assert is_within_delivery_risk_window(days_to_expiry=8, holding_period_days=5) is True


def test_exactly_at_buffer_boundary_is_risky():
    # days_remaining_after_hold == buffer_days -> "< buffer_days" is False,
    # so this should NOT be flagged (boundary is exclusive on the safe side... verify actual behavior)
    days_to_expiry = DELIVERY_BUFFER_DAYS + 5
    holding_period = 5
    remaining = days_to_expiry - holding_period
    assert remaining == DELIVERY_BUFFER_DAYS
    assert is_within_delivery_risk_window(days_to_expiry, holding_period) is False


def test_one_day_inside_boundary_is_risky():
    days_to_expiry = DELIVERY_BUFFER_DAYS + 4  # one less than the safe case above
    holding_period = 5
    assert is_within_delivery_risk_window(days_to_expiry, holding_period) is True


def test_zero_holding_period_uses_raw_days_to_expiry():
    assert is_within_delivery_risk_window(days_to_expiry=DELIVERY_BUFFER_DAYS - 1, holding_period_days=0) is True
    assert is_within_delivery_risk_window(days_to_expiry=DELIVERY_BUFFER_DAYS + 1, holding_period_days=0) is False


def test_filter_splits_safe_and_excluded():
    signals = [
        SimpleNamespace(symbol="GOLDM", days_to_expiry=30),
        SimpleNamespace(symbol="GOLDPETAL", days_to_expiry=3),
    ]
    safe, excluded = filter_signals_by_delivery_risk(signals, holding_period_days=5)
    assert [s.symbol for s in safe] == ["GOLDM"]
    assert [s.symbol for s in excluded] == ["GOLDPETAL"]


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
