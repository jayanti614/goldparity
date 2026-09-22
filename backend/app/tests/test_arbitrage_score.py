import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.analytics.arbitrage_score import compute_arbitrage_score, compute_spread  # noqa: E402


def _sig(symbol, residual, trade_date=date(2026, 1, 1)):
    return SimpleNamespace(symbol=symbol, residual_signal_pct=residual, trade_date=trade_date)


def test_compute_spread_finds_richest_and_cheapest():
    signals = [_sig("GOLDM", 0.002), _sig("GOLDPETAL", -0.004), _sig("GOLDTEN", 0.001)]
    spread, richest, cheapest = compute_spread(signals)
    assert richest == "GOLDM"
    assert cheapest == "GOLDPETAL"
    assert abs(spread - 0.006) < 1e-12


def test_compute_spread_none_with_fewer_than_two():
    assert compute_spread([_sig("GOLDM", 0.001)]) is None
    assert compute_spread([]) is None


def test_score_is_100_when_todays_spread_is_the_widest_ever():
    today = [_sig("GOLDM", 0.01), _sig("GOLDPETAL", -0.01)]  # spread = 0.02
    history = [0.001, 0.002, 0.003, 0.005, 0.02]  # today's spread included, it's the max
    result = compute_arbitrage_score(today, history)
    assert result.score == 100


def test_score_is_low_when_todays_spread_is_unusually_narrow():
    today = [_sig("GOLDM", 0.0001), _sig("GOLDPETAL", -0.0001)]  # spread = 0.0002, tiny
    history = [0.0002, 0.005, 0.006, 0.008, 0.01, 0.012]
    result = compute_arbitrage_score(today, history)
    assert result.score <= 20  # only ties itself, nothing below it


def test_neutral_score_with_no_history():
    today = [_sig("GOLDM", 0.003), _sig("GOLDPETAL", -0.001)]
    result = compute_arbitrage_score(today, [])
    assert result.score == 50


def test_none_when_fewer_than_two_signals_today():
    result = compute_arbitrage_score([_sig("GOLDM", 0.001)], [0.001, 0.002])
    assert result is None


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
