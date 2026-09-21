"""
Turns a symbol's history of decomposed residual signals into flags:
"is today's residual unusual relative to this contract's own recent
behavior" — rather than an arbitrary fixed threshold that means nothing
across contracts with very different typical noise levels.

Deliberately look-ahead-safe: day t's mean/std are computed only from
the WINDOW days strictly *before* t, never including t itself. This is
what makes it fair to reuse the exact same flags later in Phase 4's
backtest without quietly cheating with hindsight.

This is also the seed of the "statistical honesty" feature we pitched:
a symbol with too little history, or with residuals so noisy that
nothing clears the threshold, correctly produces *no* flags — the
detector doesn't force a signal to exist just because you asked it to
look.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from app.analytics.decomposition import SignalDecomposition

DEFAULT_WINDOW = 20
DEFAULT_Z_THRESHOLD = 2.0


@dataclass(frozen=True)
class FlagResult:
    symbol: str
    trade_date: date
    z_score: float | None  # None when there isn't enough trailing history yet
    is_flagged: bool


def flag_signals(
    history: list[SignalDecomposition],
    *,
    window: int = DEFAULT_WINDOW,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
) -> list[FlagResult]:
    """
    history: one symbol's decompositions, in any order — sorted internally
             by trade_date before computing rolling stats.
    """
    ordered = sorted(history, key=lambda d: d.trade_date)
    results: list[FlagResult] = []

    for i, today in enumerate(ordered):
        if i < window:
            results.append(FlagResult(today.symbol, today.trade_date, None, False))
            continue

        trailing = [ordered[j].residual_signal_pct for j in range(i - window, i)]
        mean = statistics.mean(trailing)
        stdev = statistics.pstdev(trailing)

        if stdev == 0:
            results.append(FlagResult(today.symbol, today.trade_date, None, False))
            continue

        z = (today.residual_signal_pct - mean) / stdev
        results.append(
            FlagResult(
                symbol=today.symbol,
                trade_date=today.trade_date,
                z_score=z,
                is_flagged=abs(z) >= z_threshold,
            )
        )

    return results


def flag_signals_by_symbol(
    all_history: list[SignalDecomposition],
    **kwargs,
) -> dict[str, list[FlagResult]]:
    """Same as flag_signals, but splits a mixed multi-symbol history first."""
    by_symbol: dict[str, list[SignalDecomposition]] = {}
    for d in all_history:
        by_symbol.setdefault(d.symbol, []).append(d)
    return {symbol: flag_signals(rows, **kwargs) for symbol, rows in by_symbol.items()}
