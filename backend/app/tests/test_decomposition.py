import sys
from datetime import date, timedelta

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.analytics.decomposition import decompose_signals_for_date  # noqa: E402
from app.db import BhavcopyRecord  # noqa: E402

TRADE_DATE = date(2026, 1, 1)


def _record(symbol: str, days_to_expiry: int, price_per_gram_alloy: float) -> BhavcopyRecord:
    """Builds a record whose close, once divided by quote_per_g, equals
    exactly price_per_gram_alloy — lets test scenarios be specified in
    per-gram terms directly instead of hand-multiplying by quote_per_g."""
    from app.contracts import get_contract

    spec = get_contract(symbol)
    r = BhavcopyRecord()
    r.symbol = symbol
    r.trade_date = TRADE_DATE
    r.expiry_date = TRADE_DATE + timedelta(days=days_to_expiry)
    r.close = price_per_gram_alloy * spec.quote_per_g
    r.open = r.high = r.low = r.close
    r.volume = 100
    r.open_interest = 100
    return r


def test_symbol_with_no_next_month_gets_no_roll_down_adjustment():
    # GOLDGUINEA here has only a front-month row -- no carry rate can be
    # estimated, so per the "statistical honesty" rule it must NOT be
    # force-adjusted even though its expiry differs from the common day.
    records = [
        _record("GOLDM", days_to_expiry=5, price_per_gram_alloy=1000.0),  # sets common day = 5
        _record("GOLDGUINEA", days_to_expiry=15, price_per_gram_alloy=1005.0),
    ]
    results = {r.symbol: r for r in decompose_signals_for_date(records)}

    guinea = results["GOLDGUINEA"]
    assert guinea.carry_rate_daily is None
    assert guinea.roll_down_effect_pct == 0.0
    assert abs(guinea.roll_down_adjusted_price - guinea.price_per_gram_999) < 1e-9


def test_symbol_at_common_day_gets_zero_roll_down_effect():
    records = [
        _record("GOLDM", days_to_expiry=5, price_per_gram_alloy=1000.0),  # this IS the common day
        _record("GOLDGUINEA", days_to_expiry=15, price_per_gram_alloy=1005.0),
    ]
    results = {r.symbol: r for r in decompose_signals_for_date(records)}
    goldm = results["GOLDM"]
    assert goldm.days_to_expiry == 5
    assert goldm.roll_down_effect_pct == 0.0


def test_carry_rate_estimated_correctly_from_own_curve():
    # GOLDPETAL front=10 days @ per-gram 1000, next=40 days @ per-gram 1012
    # -> carry = (1012/1000 - 1) / (40-10) = 0.0004/day, exactly.
    # GOLDGUINEA is included purely as a benchmark partner -- leave-one-out
    # reference pricing needs at least one other symbol to compare against.
    records = [
        _record("GOLDPETAL", days_to_expiry=10, price_per_gram_alloy=1000.0),
        _record("GOLDPETAL", days_to_expiry=40, price_per_gram_alloy=1012.0),
        _record("GOLDGUINEA", days_to_expiry=10, price_per_gram_alloy=1005.0),
    ]
    results = {r.symbol: r for r in decompose_signals_for_date(records)}
    petal = results["GOLDPETAL"]
    assert petal.carry_rate_daily is not None
    assert abs(petal.carry_rate_daily - 0.0004) < 1e-9


def test_roll_down_adjustment_moves_price_toward_common_day():
    # GOLDTEN: front=20 days @ 1010/gram, next=50 days @ 1025.15/gram
    # -> carry = 0.015/30 = 0.0005/day exactly.
    # Common day (from GOLDM below) = 5, so GOLDTEN gets discounted back
    # 15 days: adjusted = 1010 / (1 + 0.0005*15) = 1010 / 1.0075
    records = [
        _record("GOLDM", days_to_expiry=5, price_per_gram_alloy=1000.0),
        _record("GOLDTEN", days_to_expiry=20, price_per_gram_alloy=1010.0),
        _record("GOLDTEN", days_to_expiry=50, price_per_gram_alloy=1025.15),
    ]
    results = {r.symbol: r for r in decompose_signals_for_date(records)}
    goldten_front = [r for r in decompose_signals_for_date(records) if r.symbol == "GOLDTEN"][0]

    expected_carry = 0.0005
    expected_adjusted = 1010.0 / (1 + expected_carry * 15)
    assert abs(goldten_front.carry_rate_daily - expected_carry) < 1e-9
    assert abs(goldten_front.roll_down_adjusted_price - expected_adjusted) < 1e-6


def test_reference_price_is_leave_one_out_mean_and_residuals_are_consistent():
    records = [
        _record("GOLDM", days_to_expiry=5, price_per_gram_alloy=1000.0),
        _record("GOLDGUINEA", days_to_expiry=15, price_per_gram_alloy=1005.0),
    ]
    results = {r.symbol: r for r in decompose_signals_for_date(records)}

    # With only 2 symbols, each one's leave-one-out reference is simply
    # the OTHER symbol's adjusted price -- never including its own.
    goldm, guinea = results["GOLDM"], results["GOLDGUINEA"]
    assert abs(goldm.reference_price - guinea.roll_down_adjusted_price) < 1e-9
    assert abs(guinea.reference_price - goldm.roll_down_adjusted_price) < 1e-9

    for r in results.values():
        expected_residual = (r.roll_down_adjusted_price / r.reference_price) - 1
        assert abs(r.residual_signal_pct - expected_residual) < 1e-9


def test_reference_price_excludes_self_with_three_symbols():
    # With 3 symbols, each one's reference should be the mean of the
    # OTHER TWO only -- not all three (which would include itself).
    # All three are 999-purity so price_per_gram_alloy == price_per_gram_999
    # directly, keeping the expected math simple.
    records = [
        _record("GOLDGUINEA", days_to_expiry=5, price_per_gram_alloy=1000.0),
        _record("GOLDPETAL", days_to_expiry=5, price_per_gram_alloy=1005.0),
        _record("GOLDTEN", days_to_expiry=5, price_per_gram_alloy=1010.0),
    ]
    results = {r.symbol: r for r in decompose_signals_for_date(records)}

    expected_guinea_ref = (1005.0 + 1010.0) / 2  # GOLDPETAL + GOLDTEN only
    expected_petal_ref = (1000.0 + 1010.0) / 2  # GOLDGUINEA + GOLDTEN only
    expected_ten_ref = (1000.0 + 1005.0) / 2  # GOLDGUINEA + GOLDPETAL only

    assert abs(results["GOLDGUINEA"].reference_price - expected_guinea_ref) < 1e-9
    assert abs(results["GOLDPETAL"].reference_price - expected_petal_ref) < 1e-9
    assert abs(results["GOLDTEN"].reference_price - expected_ten_ref) < 1e-9


def test_uses_front_month_only_not_far_months():
    # A symbol with 3 expiries listed should only produce ONE decomposition
    # (front month), not one per expiry. GOLDGUINEA is a benchmark partner.
    records = [
        _record("GOLDPETAL", days_to_expiry=10, price_per_gram_alloy=1000.0),
        _record("GOLDPETAL", days_to_expiry=40, price_per_gram_alloy=1012.0),
        _record("GOLDPETAL", days_to_expiry=70, price_per_gram_alloy=1024.0),
        _record("GOLDGUINEA", days_to_expiry=10, price_per_gram_alloy=1005.0),
    ]
    results = [r for r in decompose_signals_for_date(records) if r.symbol == "GOLDPETAL"]
    assert len(results) == 1
    assert results[0].days_to_expiry == 10


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
