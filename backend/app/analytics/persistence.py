"""
Runs Phase 2 + Phase 3 across the full stored history and persists the
result: one SignalRecord per (symbol, trade_date), fully decomposed and
flagged.
"""

from __future__ import annotations

from sqlalchemy import select

from app.analytics.decomposition import SignalDecomposition, decompose_signals_for_date
from app.analytics.detection import FlagResult, flag_signals_by_symbol
from app.db import SignalRecord, get_all_trade_dates, get_records_for_date, get_session


def compute_all_decompositions() -> list[SignalDecomposition]:
    all_decompositions: list[SignalDecomposition] = []
    for trade_date in get_all_trade_dates():
        records = get_records_for_date(trade_date)
        all_decompositions.extend(decompose_signals_for_date(records))
    return all_decompositions


def persist_signals(
    decompositions: list[SignalDecomposition],
    flags_by_symbol: dict[str, list[FlagResult]],
) -> dict[str, int]:
    flag_lookup: dict[tuple[str, object], FlagResult] = {}
    for symbol, flags in flags_by_symbol.items():
        for f in flags:
            flag_lookup[(symbol, f.trade_date)] = f

    inserted = updated = 0
    session = get_session()
    try:
        for d in decompositions:
            flag = flag_lookup.get((d.symbol, d.trade_date))
            existing = session.scalar(
                select(SignalRecord).where(
                    SignalRecord.symbol == d.symbol,
                    SignalRecord.trade_date == d.trade_date,
                )
            )
            values = dict(
                expiry_date=d.expiry_date,
                days_to_expiry=d.days_to_expiry,
                quoted_close=d.quoted_close,
                price_per_gram_alloy=d.price_per_gram_alloy,
                price_per_gram_999=d.price_per_gram_999,
                purity_effect_pct=d.purity_effect_pct,
                carry_rate_daily=d.carry_rate_daily,
                roll_down_adjusted_price=d.roll_down_adjusted_price,
                roll_down_effect_pct=d.roll_down_effect_pct,
                reference_price=d.reference_price,
                residual_signal_pct=d.residual_signal_pct,
                is_flagged=bool(flag and flag.is_flagged),
                z_score=flag.z_score if flag else None,
            )
            if existing is None:
                session.add(SignalRecord(symbol=d.symbol, trade_date=d.trade_date, **values))
                inserted += 1
            else:
                for k, v in values.items():
                    setattr(existing, k, v)
                updated += 1
        session.commit()
    finally:
        session.close()
    return {"inserted": inserted, "updated": updated}


def persist_trades(trades: list) -> int:
    """Wipes and rewrites trade_records for the given symbols each run --
    trades are cheap to recompute and simpler to keep in sync this way
    than trying to upsert a backtest replay."""
    from app.db import TradeRecord

    session = get_session()
    try:
        symbols = {t.symbol for t in trades}
        if symbols:
            session.query(TradeRecord).filter(TradeRecord.symbol.in_(symbols)).delete(
                synchronize_session=False
            )
        for t in trades:
            session.add(
                TradeRecord(
                    symbol=t.symbol,
                    entry_date=t.entry_date,
                    exit_date=t.exit_date,
                    direction=t.direction,
                    entry_residual_pct=t.entry_residual_pct,
                    exit_residual_pct=t.exit_residual_pct,
                    raw_return_pct=t.raw_return_pct,
                    cost_pct=t.cost_pct,
                    net_return_pct=t.net_return_pct,
                )
            )
        session.commit()
    finally:
        session.close()
    return len(trades)


def persist_carry_estimates(estimates: list) -> int:
    from app.db import CarryEstimateRecord

    session = get_session()
    try:
        count = 0
        for e in estimates:
            if e is None:
                continue
            existing = session.scalar(
                select(CarryEstimateRecord).where(CarryEstimateRecord.trade_date == e.trade_date)
            )
            values = dict(
                n_points=e.n_points,
                n_unique_expiries=e.n_unique_expiries,
                daily_rate=e.daily_rate,
                annualized_rate_pct=e.annualized_rate_pct,
                r_squared=e.r_squared,
            )
            if existing is None:
                session.add(CarryEstimateRecord(trade_date=e.trade_date, **values))
            else:
                for k, v in values.items():
                    setattr(existing, k, v)
            count += 1
        session.commit()
    finally:
        session.close()
    return count


def run_full_analytics() -> dict:
    decompositions = compute_all_decompositions()
    flags_by_symbol = flag_signals_by_symbol(decompositions)
    counts = persist_signals(decompositions, flags_by_symbol)
    flagged = [
        d
        for d in decompositions
        if flags_by_symbol.get(d.symbol)
        and any(f.trade_date == d.trade_date and f.is_flagged for f in flags_by_symbol[d.symbol])
    ]
    return {
        "total_decompositions": len(decompositions),
        "flagged_count": len(flagged),
        "flagged": flagged,
        **counts,
    }
