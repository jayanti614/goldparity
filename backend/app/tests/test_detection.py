import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.analytics.decomposition import SignalDecomposition  # noqa: E402
from app.analytics.detection import flag_signals  # noqa: E402


def _decomp(day_offset: int, residual_pct: float) -> SignalDecomposition:
    return SignalDecomposition(
        symbol="GOLDPETAL",
        trade_date=date(2026, 1, 1) + timedelta(days=day_offset),
        expiry_date=date(2026, 3, 1),
        days_to_expiry=59 - day_offset,
        quoted_close=1000.0,
        price_per_gram_alloy=1000.0,
        price_per_gram_999=1000.0,
        purity_effect_pct=0.0,
        carry_rate_daily=None,
        roll_down_adjusted_price=1000.0 * (1 + residual_pct),
        roll_down_effect_pct=0.0,
        reference_price=1000.0,
        residual_signal_pct=residual_pct,
    )


def test_no_flag_before_enough_history():
    # window=20: the first 20 days simply can't have a trailing window yet.
    history = [_decomp(i, 0.001) for i in range(15)]
    results = flag_signals(history, window=20)
    assert all(r.z_score is None and not r.is_flagged for r in results)


def test_flat_history_then_a_real_outlier_gets_flagged():
    # 20 quiet days at ~0% residual (tiny alternating noise so stdev isn't
    # exactly zero), then one day with a huge, obvious outlier.
    quiet = [_decomp(i, 0.0001 if i % 2 == 0 else -0.0001) for i in range(20)]
    outlier = _decomp(20, 0.01)  # 1% residual -- way outside the quiet noise band
    results = flag_signals(quiet + [outlier], window=20)

    outlier_result = results[-1]
    assert outlier_result.z_score is not None
    assert outlier_result.is_flagged is True


def test_zero_variance_history_does_not_crash_or_falsely_flag():
    # Every trailing day has IDENTICAL residual -> stdev is exactly 0.
    # Must not divide by zero, and must not flag.
    flat = [_decomp(i, 0.002) for i in range(21)]
    results = flag_signals(flat, window=20)
    last = results[-1]
    assert last.z_score is None
    assert last.is_flagged is False


def test_results_sorted_by_date_regardless_of_input_order():
    history = [_decomp(i, 0.001) for i in reversed(range(25))]  # shuffled/reverse input
    results = flag_signals(history, window=20)
    dates = [r.trade_date for r in results]
    assert dates == sorted(dates)


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
