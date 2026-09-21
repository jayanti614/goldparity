import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.analytics.backtest import (  # noqa: E402
    DEFAULT_COST_BPS_PER_LEG,
    LEG_EXECUTIONS_PER_TRADE,
    bootstrap_mean_return,
    run_backtest_for_symbol,
)

BASE_DATE = date(2026, 1, 1)


def _row(offset: int, residual_pct: float, is_flagged: bool, days_to_expiry: int = 60):
    return SimpleNamespace(
        symbol="GOLDPETAL",
        trade_date=BASE_DATE + timedelta(days=offset),
        residual_signal_pct=residual_pct,
        is_flagged=is_flagged,
        days_to_expiry=days_to_expiry,
    )


def test_basic_trade_construction_and_return_math():
    # Flag on day 0 (residual cheap, -0.5%). Entry = day 1. Hold 5 -> exit = day 6.
    rows = [_row(0, -0.005, is_flagged=True)]
    rows += [_row(i, -0.005 + 0.0005 * i, is_flagged=False) for i in range(1, 10)]
    # entry (day1) residual = -0.005+0.0005*1 = -0.0045
    # exit (day6) residual  = -0.005+0.0005*6 = -0.0020

    trades, excluded = run_backtest_for_symbol(rows, holding_period_days=5, cost_bps_per_leg=4)
    assert len(trades) == 1
    t = trades[0]
    assert t.direction == 1  # entry residual negative -> long the spread
    assert t.entry_date == BASE_DATE + timedelta(days=1)
    assert t.exit_date == BASE_DATE + timedelta(days=6)

    expected_entry = -0.005 + 0.0005 * 1
    expected_exit = -0.005 + 0.0005 * 6
    expected_raw = 1 * (expected_exit - expected_entry)
    expected_cost = (DEFAULT_COST_BPS_PER_LEG / 10_000) * LEG_EXECUTIONS_PER_TRADE
    assert abs(t.entry_residual_pct - expected_entry) < 1e-12
    assert abs(t.raw_return_pct - expected_raw) < 1e-12
    assert abs(t.cost_pct - expected_cost) < 1e-12
    assert abs(t.net_return_pct - (expected_raw - expected_cost)) < 1e-12


def test_short_direction_when_entry_residual_positive():
    rows = [_row(0, 0.006, is_flagged=True)]
    rows += [_row(i, 0.006 - 0.0003 * i, is_flagged=False) for i in range(1, 10)]
    trades, _ = run_backtest_for_symbol(rows, holding_period_days=5)
    assert trades[0].direction == -1


def test_delivery_risk_excludes_trade():
    # Flag today, but entry day is only 3 days from expiry -- with a
    # 5-day hold, that's deep inside the delivery-risk window.
    rows = [_row(0, -0.005, is_flagged=True, days_to_expiry=10)]
    rows += [_row(i, -0.004, is_flagged=False, days_to_expiry=10 - i) for i in range(1, 10)]
    trades, excluded = run_backtest_for_symbol(rows, holding_period_days=5)
    assert len(trades) == 0
    assert any(e.reason == "delivery_risk" for e in excluded)


def test_insufficient_future_data_at_tail_is_excluded_not_crashed():
    # Flag on the very last row -- there's no room to enter, let alone exit.
    rows = [_row(i, -0.001, is_flagged=False) for i in range(5)]
    rows.append(_row(5, -0.006, is_flagged=True))
    trades, excluded = run_backtest_for_symbol(rows, holding_period_days=5)
    assert len(trades) == 0
    assert any(e.reason == "insufficient_future_data" for e in excluded)


def test_zero_residual_entry_excluded_as_no_direction():
    rows = [_row(0, -0.004, is_flagged=True)]
    rows += [_row(i, 0.0 if i == 1 else -0.001, is_flagged=False) for i in range(1, 10)]
    trades, excluded = run_backtest_for_symbol(rows, holding_period_days=5)
    assert len(trades) == 0
    assert any(e.reason == "no_direction" for e in excluded)


def test_bootstrap_returns_none_below_minimum_sample():
    result = bootstrap_mean_return([0.01, 0.02, 0.015, -0.005])  # only 4 trades
    assert result is None


def test_bootstrap_identical_returns_collapse_to_that_value():
    returns = [0.01] * 10  # every trade returned exactly +1%
    result = bootstrap_mean_return(returns, n_resamples=500)
    assert result is not None
    assert abs(result.mean_return_pct - 0.01) < 1e-9
    assert abs(result.ci_low_pct - 0.01) < 1e-9
    assert abs(result.ci_high_pct - 0.01) < 1e-9
    assert "positive edge" in result.verdict


def test_bootstrap_noisy_mixed_returns_spans_zero_honestly():
    # Small, noisy, mean-near-zero sample -> CI should span zero -> honest "no edge" verdict.
    returns = [0.004, -0.005, 0.003, -0.002, 0.001, -0.004, 0.002]
    result = bootstrap_mean_return(returns, n_resamples=2000)
    assert result is not None
    assert result.ci_low_pct <= 0 <= result.ci_high_pct
    assert "No statistically significant edge" in result.verdict


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
