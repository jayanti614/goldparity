"""
Runs Phase 4 (walk-forward backtest) and Phase 5 (implied carry rate)
over everything currently in the database. Requires run_analytics.py
(Phase 2+3) to have been run first -- this reads from signal_records.

Usage:
    python scripts/run_backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analytics.backtest import bootstrap_mean_return, run_backtest_for_symbol  # noqa: E402
from app.analytics.carry import estimate_implied_carry  # noqa: E402
from app.analytics.persistence import persist_carry_estimates, persist_trades  # noqa: E402
from app.contracts import ALL_SYMBOLS  # noqa: E402
from app.db import get_all_trade_dates, get_records_for_date, get_signal_history_for_symbol, init_db  # noqa: E402


def main() -> None:
    init_db()

    # ---------- Phase 4: backtest ----------
    all_trades = []
    all_excluded = []
    for symbol in ALL_SYMBOLS:
        history = get_signal_history_for_symbol(symbol)
        trades, excluded = run_backtest_for_symbol(history)
        all_trades.extend(trades)
        all_excluded.extend(excluded)

    persist_trades(all_trades)

    print(f"Completed trades: {len(all_trades)}")
    reasons = {}
    for e in all_excluded:
        reasons[e.reason] = reasons.get(e.reason, 0) + 1
    print(f"Excluded signals: {len(all_excluded)}  {reasons if reasons else ''}")

    if all_trades:
        print("\nTrade log:")
        for t in sorted(all_trades, key=lambda x: x.entry_date):
            side = "LONG spread" if t.direction == 1 else "SHORT spread"
            print(
                f"  {t.symbol:<11} {t.entry_date} -> {t.exit_date}  {side:<12}  "
                f"entry={t.entry_residual_pct:+.4%}  exit={t.exit_residual_pct:+.4%}  "
                f"raw={t.raw_return_pct:+.4%}  net={t.net_return_pct:+.4%}"
            )

    net_returns = [t.net_return_pct for t in all_trades]
    result = bootstrap_mean_return(net_returns)
    print("\n--- Statistical honesty check (bootstrap, 95% CI) ---")
    if result is None:
        print(f"Only {len(net_returns)} completed trade(s) -- too few to bootstrap meaningfully.")
        print("This itself is an honest result: more history is needed before claiming any edge.")
    else:
        win_rate = sum(1 for r in net_returns if r > 0) / len(net_returns)
        print(f"Trades: {result.n_trades}   Win rate: {win_rate:.1%}   Mean net return/trade: {result.mean_return_pct:+.4%}")
        print(f"95% CI: [{result.ci_low_pct:+.4%}, {result.ci_high_pct:+.4%}]")
        print(f"Verdict: {result.verdict}")

    # ---------- Phase 5a: implied carry rate ----------
    print("\n--- Implied carry rate (per trade date) ---")
    estimates = []
    for trade_date in get_all_trade_dates():
        records = get_records_for_date(trade_date)
        est = estimate_implied_carry(records)
        estimates.append(est)
        if est:
            print(
                f"  {trade_date}  annualized={est.annualized_rate_pct:+.3f}%  "
                f"R²={est.r_squared:.3f}  (from {est.n_points} points, {est.n_unique_expiries} expiries)"
            )
    persist_carry_estimates(estimates)


if __name__ == "__main__":
    main()
