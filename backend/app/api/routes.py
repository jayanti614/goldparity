from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.analytics.arbitrage_score import compute_arbitrage_score, compute_spread
from app.analytics.backtest import bootstrap_mean_return, run_backtest_for_symbol
from app.api.schemas import (
    ArbitrageScoreOut,
    BacktestSummaryOut,
    CarryPointOut,
    ContractSpecOut,
    LatestSnapshotOut,
    PhaseStatusOut,
    SignalHistoryPointOut,
    SignalOut,
    StatusOut,
    TradeOut,
)
from app.contracts import ALL_SYMBOLS, CONTRACTS
from app.db import CarryEstimateRecord, SignalRecord, get_session, get_signal_history_for_symbol

router = APIRouter(prefix="/api")


PHASES = [
    (1, "Data pipeline", "built"),
    (2, "Purity + unit normalization", "built"),
    (3, "Mispricing detection + decomposition", "built"),
    (4, "Walk-forward backtest + honesty check", "built"),
    (5, "Implied carry rate + delivery-risk filter", "built"),
    (6, "API layer", "built"),
    (7, "Dashboard", "built"),
    (8, "Trust ledger (signal track record)", "in_progress"),
    (9, "Deploy + polish", "in_progress"),
]


@router.get("/status", response_model=StatusOut)
def get_status() -> StatusOut:
    session = get_session()
    try:
        latest = session.execute(
            select(SignalRecord.trade_date).order_by(SignalRecord.trade_date.desc()).limit(1)
        ).scalar()
        n_days = session.execute(select(SignalRecord.trade_date).distinct()).all()
        n_flagged = session.execute(
            select(SignalRecord).where(SignalRecord.is_flagged.is_(True))
        ).all()
    finally:
        session.close()

    return StatusOut(
        phases=[PhaseStatusOut(phase=p, name=n, status=s) for p, n, s in PHASES],
        latest_trade_date=latest,
        total_trading_days_loaded=len(n_days),
        total_flagged_signals=len(n_flagged),
    )


@router.get("/contracts", response_model=list[ContractSpecOut])
def get_contracts() -> list[ContractSpecOut]:
    return [
        ContractSpecOut(
            symbol=spec.symbol,
            trading_unit_g=spec.trading_unit_g,
            purity=spec.purity,
            quote_per_g=spec.quote_per_g,
            expiry_window=spec.expiry_window,
        )
        for spec in CONTRACTS.values()
    ]


def _all_signal_dates_spreads(session) -> list[float]:
    rows = session.execute(select(SignalRecord)).scalars().all()
    by_date: dict = {}
    for r in rows:
        by_date.setdefault(r.trade_date, []).append(r)
    spreads = []
    for _, sigs in by_date.items():
        result = compute_spread(sigs)
        if result:
            spreads.append(result[0])
    return spreads


@router.get("/signals/latest", response_model=LatestSnapshotOut)
def get_latest_signals() -> LatestSnapshotOut:
    session = get_session()
    try:
        latest_date = session.execute(
            select(SignalRecord.trade_date).order_by(SignalRecord.trade_date.desc()).limit(1)
        ).scalar()
        if latest_date is None:
            raise HTTPException(status_code=404, detail="No signals loaded yet. Run the pipeline first.")

        signals = list(
            session.execute(select(SignalRecord).where(SignalRecord.trade_date == latest_date))
            .scalars()
            .all()
        )
        historical_spreads = _all_signal_dates_spreads(session)
    finally:
        session.close()

    score = compute_arbitrage_score(signals, historical_spreads)
    if score is None:
        raise HTTPException(status_code=404, detail="Not enough contracts on the latest date to compute a score.")

    return LatestSnapshotOut(
        trade_date=latest_date,
        signals=[SignalOut.model_validate(s) for s in signals],
        arbitrage_score=ArbitrageScoreOut(
            trade_date=score.trade_date,
            score=score.score,
            richest_symbol=score.richest_symbol,
            cheapest_symbol=score.cheapest_symbol,
            spread_pct=score.spread_pct,
        ),
    )


@router.get("/signals/history/{symbol}", response_model=list[SignalHistoryPointOut])
def get_signal_history(symbol: str) -> list[SignalHistoryPointOut]:
    symbol = symbol.strip().upper()
    if symbol not in ALL_SYMBOLS:
        raise HTTPException(status_code=404, detail=f"Unknown symbol {symbol!r}. Valid: {ALL_SYMBOLS}")
    rows = get_signal_history_for_symbol(symbol)
    return [SignalHistoryPointOut.model_validate(r) for r in rows]


@router.get("/signals/flagged", response_model=list[SignalOut])
def get_flagged_signals() -> list[SignalOut]:
    session = get_session()
    try:
        rows = list(
            session.execute(
                select(SignalRecord)
                .where(SignalRecord.is_flagged.is_(True))
                .order_by(SignalRecord.trade_date.desc())
            )
            .scalars()
            .all()
        )
    finally:
        session.close()
    return [SignalOut.model_validate(r) for r in rows]


@router.get("/backtest", response_model=BacktestSummaryOut)
def get_backtest() -> BacktestSummaryOut:
    all_trades = []
    for symbol in ALL_SYMBOLS:
        history = get_signal_history_for_symbol(symbol)
        trades, _ = run_backtest_for_symbol(history)
        all_trades.extend(trades)

    net_returns = [t.net_return_pct for t in all_trades]
    result = bootstrap_mean_return(net_returns)

    if result is None:
        verdict = (
            f"Only {len(net_returns)} completed trade(s) in the loaded history -- "
            "too few to bootstrap meaningfully. More history is needed before claiming any edge."
        )
        return BacktestSummaryOut(
            trades=[TradeOut.model_validate(t) for t in sorted(all_trades, key=lambda x: x.entry_date)],
            n_trades=len(all_trades),
            win_rate=None,
            mean_return_pct=None,
            ci_low_pct=None,
            ci_high_pct=None,
            ci_level=None,
            verdict=verdict,
        )

    win_rate = sum(1 for r in net_returns if r > 0) / len(net_returns)
    return BacktestSummaryOut(
        trades=[TradeOut.model_validate(t) for t in sorted(all_trades, key=lambda x: x.entry_date)],
        n_trades=result.n_trades,
        win_rate=win_rate,
        mean_return_pct=result.mean_return_pct,
        ci_low_pct=result.ci_low_pct,
        ci_high_pct=result.ci_high_pct,
        ci_level=result.ci_level,
        verdict=result.verdict,
    )


@router.get("/carry/history", response_model=list[CarryPointOut])
def get_carry_history() -> list[CarryPointOut]:
    session = get_session()
    try:
        rows = list(
            session.execute(select(CarryEstimateRecord).order_by(CarryEstimateRecord.trade_date))
            .scalars()
            .all()
        )
    finally:
        session.close()
    return [CarryPointOut.model_validate(r) for r in rows]
