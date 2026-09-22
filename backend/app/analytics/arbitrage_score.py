"""
The "Arbitrage Score" shown on the dashboard gauge is deliberately NOT an
arbitrary fixed scale (e.g. "1.5% spread = 100") -- it's the percentile
rank of today's cross-contract spread within this market's own historical
spread distribution. A score of 80 means "today's mispricing is wider
than 80% of days in the loaded history" -- a claim that's actually
grounded in data, not a made-up threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ArbitrageScore:
    trade_date: date
    score: int
    richest_symbol: str
    cheapest_symbol: str
    spread_pct: float


def compute_spread(signals_for_date: list) -> tuple[float, str, str] | None:
    """signals_for_date: SignalRecord-like objects (needs .symbol and
    .residual_signal_pct) for ONE trade date. Returns
    (spread_pct, richest_symbol, cheapest_symbol), or None if fewer than
    2 signals are present (no spread to measure)."""
    if len(signals_for_date) < 2:
        return None
    richest = max(signals_for_date, key=lambda s: s.residual_signal_pct)
    cheapest = min(signals_for_date, key=lambda s: s.residual_signal_pct)
    spread = richest.residual_signal_pct - cheapest.residual_signal_pct
    return spread, richest.symbol, cheapest.symbol


def compute_arbitrage_score(
    latest_signals: list,
    historical_spreads_pct: list[float],
) -> ArbitrageScore | None:
    """
    latest_signals: SignalRecord-like rows for the most recent trade date.
    historical_spreads_pct: the spread_pct value (see compute_spread) for
        every trade date in the loaded history, INCLUDING today's --
        this is what today's spread is ranked against.
    """
    result = compute_spread(latest_signals)
    if result is None:
        return None
    spread, richest_symbol, cheapest_symbol = result

    if not historical_spreads_pct:
        percentile = 50  # no history to rank against -- neutral default
    else:
        n_below_or_equal = sum(1 for s in historical_spreads_pct if s <= spread)
        percentile = round(100 * n_below_or_equal / len(historical_spreads_pct))

    return ArbitrageScore(
        trade_date=latest_signals[0].trade_date,
        score=max(0, min(100, percentile)),
        richest_symbol=richest_symbol,
        cheapest_symbol=cheapest_symbol,
        spread_pct=spread,
    )
