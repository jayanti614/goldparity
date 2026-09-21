"""
Phase 4 — Walk-Forward Backtest Engine.

Replays every flagged signal from Phase 3 as a hypothetical relative-
value trade and asks the only question that matters: after realistic
costs, did this actually make money, or was it noise?

How a trade is modeled:
  - A flagged signal on day T is acted on at T+1 (next trading day) --
    never at T itself, since the flag is computed FROM day T's own
    closing data, so day T's close was not tradeable information yet.
  - Direction: if the contract was cheap (residual < 0), go long the
    spread (long the contract, short the reference basket), expecting
    the residual to rise back toward 0. If rich, go short the spread.
  - Exit: a fixed holding period later (default 5 trading days), at
    that day's residual. Fixed-horizon exits are simple and avoid the
    lookahead bias that a "wait for convergence" rule would introduce.
  - Return is measured directly in residual-percentage terms: going
    from -0.6% to 0.0% is a +0.6% gain to a long-the-cheap-side position.
    This is a clean proxy for the P&L of the long/short spread without
    needing to assume specific lot sizes or margin.
  - Delivery risk (Phase 5b) is checked BEFORE a trade is taken: if
    holding the position for the full planned period would carry it
    into the contract's staggered-delivery tender window, the trade is
    excluded rather than force-fit.
  - Costs: a configurable per-leg cost in basis points, applied across
    all 4 leg-executions of a spread trade (long+short, entry+exit).

Then the statistical honesty check: bootstrap-resample the completed
trades' net returns to get a confidence interval on the average trade
return. If that interval straddles zero, the honest answer is "no
edge survives costs at this sample size" -- and this module will say
exactly that rather than dress up a small, noisy sample as a strategy.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from datetime import date

from app.analytics.delivery_risk import DELIVERY_BUFFER_DAYS, is_within_delivery_risk_window

DEFAULT_HOLDING_PERIOD_DAYS = 5
DEFAULT_COST_BPS_PER_LEG = 4  # 0.04% per leg execution -- illustrative, configurable
LEG_EXECUTIONS_PER_TRADE = 4  # long+short, entry+exit


@dataclass(frozen=True)
class TradeResult:
    symbol: str
    entry_date: date
    exit_date: date
    direction: int  # +1 = long the spread (contract was cheap), -1 = short (rich)
    entry_residual_pct: float
    exit_residual_pct: float
    raw_return_pct: float
    cost_pct: float
    net_return_pct: float


@dataclass(frozen=True)
class ExcludedSignal:
    symbol: str
    flagged_date: date
    reason: str  # "delivery_risk" | "insufficient_future_data" | "no_direction"


def run_backtest_for_symbol(
    rows: list,  # SignalRecord rows for ONE symbol, sorted by trade_date ascending
    *,
    holding_period_days: int = DEFAULT_HOLDING_PERIOD_DAYS,
    cost_bps_per_leg: float = DEFAULT_COST_BPS_PER_LEG,
    delivery_buffer_days: int = DELIVERY_BUFFER_DAYS,
) -> tuple[list[TradeResult], list[ExcludedSignal]]:
    trades: list[TradeResult] = []
    excluded: list[ExcludedSignal] = []
    cost_pct = (cost_bps_per_leg / 10_000) * LEG_EXECUTIONS_PER_TRADE

    for i, flagged_row in enumerate(rows):
        if not flagged_row.is_flagged:
            continue

        entry_index = i + 1
        if entry_index >= len(rows):
            excluded.append(ExcludedSignal(flagged_row.symbol, flagged_row.trade_date, "insufficient_future_data"))
            continue
        entry_row = rows[entry_index]

        if is_within_delivery_risk_window(entry_row.days_to_expiry, holding_period_days, delivery_buffer_days):
            excluded.append(ExcludedSignal(flagged_row.symbol, flagged_row.trade_date, "delivery_risk"))
            continue

        exit_index = entry_index + holding_period_days
        if exit_index >= len(rows):
            excluded.append(ExcludedSignal(flagged_row.symbol, flagged_row.trade_date, "insufficient_future_data"))
            continue
        exit_row = rows[exit_index]

        entry_residual = entry_row.residual_signal_pct
        if entry_residual == 0:
            excluded.append(ExcludedSignal(flagged_row.symbol, flagged_row.trade_date, "no_direction"))
            continue

        direction = -1 if entry_residual > 0 else 1
        exit_residual = exit_row.residual_signal_pct
        raw_return = direction * (exit_residual - entry_residual)
        net_return = raw_return - cost_pct

        trades.append(
            TradeResult(
                symbol=flagged_row.symbol,
                entry_date=entry_row.trade_date,
                exit_date=exit_row.trade_date,
                direction=direction,
                entry_residual_pct=entry_residual,
                exit_residual_pct=exit_residual,
                raw_return_pct=raw_return,
                cost_pct=cost_pct,
                net_return_pct=net_return,
            )
        )

    return trades, excluded


@dataclass(frozen=True)
class BootstrapResult:
    n_trades: int
    mean_return_pct: float
    ci_low_pct: float
    ci_high_pct: float
    ci_level: float
    verdict: str


def bootstrap_mean_return(
    net_returns_pct: list[float],
    *,
    n_resamples: int = 5000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> BootstrapResult | None:
    """
    Bootstrap confidence interval on the mean per-trade net return.
    Returns None if there are too few trades to say anything meaningful
    (fewer than 5) -- reporting a "significant" result off a handful of
    trades would itself be a statistical-honesty violation.
    """
    n = len(net_returns_pct)
    if n < 5:
        return None

    rng = random.Random(seed)
    resample_means = []
    for _ in range(n_resamples):
        sample = [net_returns_pct[rng.randrange(n)] for _ in range(n)]
        resample_means.append(statistics.mean(sample))
    resample_means.sort()

    lo_idx = int((1 - ci_level) / 2 * n_resamples)
    hi_idx = int((1 - (1 - ci_level) / 2) * n_resamples) - 1
    ci_low = resample_means[lo_idx]
    ci_high = resample_means[hi_idx]
    mean_return = statistics.mean(net_returns_pct)

    if ci_low > 0:
        verdict = f"Statistically significant positive edge survives costs ({ci_level:.0%} CI entirely above zero)."
    elif ci_high < 0:
        verdict = f"Statistically significant negative edge ({ci_level:.0%} CI entirely below zero) — direction may need review."
    else:
        verdict = (
            f"No statistically significant edge survives costs at this sample size "
            f"({ci_level:.0%} CI spans zero: [{ci_low:+.4%}, {ci_high:+.4%}]). "
            "This is a valid, honest outcome, not a failure of the method."
        )

    return BootstrapResult(
        n_trades=n,
        mean_return_pct=mean_return,
        ci_low_pct=ci_low,
        ci_high_pct=ci_high,
        ci_level=ci_level,
        verdict=verdict,
    )
