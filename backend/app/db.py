"""
SQLite storage, via SQLAlchemy.

One table for now: bhavcopy_records — the cleaned, normalized-format
daily rows for the 4 gold contracts. Everything downstream (fair-value
normalization, mispricing detection, backtesting) reads from this table,
so it doesn't matter whether a row got here via a manually downloaded
file or (later) a live fetch.
"""

from __future__ import annotations

import os
from datetime import date

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DB_PATH = os.environ.get("GOLDPARITY_DB_PATH", "goldparity.db")
_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class BhavcopyRecord(Base):
    __tablename__ = "bhavcopy_records"
    __table_args__ = (
        # A contract can only have one row per (trade_date, expiry_date) —
        # this is what makes tracking-by-expiry (not a naive continuous
        # series) safe: re-ingesting the same day is a no-op, not a duplicate.
        UniqueConstraint("symbol", "trade_date", "expiry_date", name="uq_symbol_date_expiry"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    expiry_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    open_interest: Mapped[int] = mapped_column(Integer, default=0)


class SignalRecord(Base):
    """
    One row per (symbol, trade_date): the full signal-decomposition
    breakdown from Phase 3, plus whether the detector flagged it.
    This is what Phase 4's backtest will replay, and what Phase 8's
    trust ledger will later mark as converged/not-converged.
    """

    __tablename__ = "signal_records"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_signal_symbol_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    expiry_date: Mapped[date] = mapped_column(Date)
    days_to_expiry: Mapped[int] = mapped_column(Integer)

    quoted_close: Mapped[float] = mapped_column(Float)
    price_per_gram_alloy: Mapped[float] = mapped_column(Float)
    price_per_gram_999: Mapped[float] = mapped_column(Float)
    purity_effect_pct: Mapped[float] = mapped_column(Float)

    carry_rate_daily: Mapped[float | None] = mapped_column(Float, nullable=True)
    roll_down_adjusted_price: Mapped[float] = mapped_column(Float)
    roll_down_effect_pct: Mapped[float] = mapped_column(Float)

    reference_price: Mapped[float] = mapped_column(Float)
    residual_signal_pct: Mapped[float] = mapped_column(Float)

    is_flagged: Mapped[bool] = mapped_column(default=False)
    z_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class TradeRecord(Base):
    """One completed backtested trade from Phase 4."""

    __tablename__ = "trade_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    exit_date: Mapped[date] = mapped_column(Date)
    direction: Mapped[int] = mapped_column(Integer)
    entry_residual_pct: Mapped[float] = mapped_column(Float)
    exit_residual_pct: Mapped[float] = mapped_column(Float)
    raw_return_pct: Mapped[float] = mapped_column(Float)
    cost_pct: Mapped[float] = mapped_column(Float)
    net_return_pct: Mapped[float] = mapped_column(Float)


class CarryEstimateRecord(Base):
    """One daily market-wide implied carry rate estimate from Phase 5a."""

    __tablename__ = "carry_estimate_records"
    __table_args__ = (UniqueConstraint("trade_date", name="uq_carry_trade_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    n_points: Mapped[int] = mapped_column(Integer)
    n_unique_expiries: Mapped[int] = mapped_column(Integer)
    daily_rate: Mapped[float] = mapped_column(Float)
    annualized_rate_pct: Mapped[float] = mapped_column(Float)
    r_squared: Mapped[float] = mapped_column(Float)


def init_db() -> None:
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    return SessionLocal()


def get_all_trade_dates() -> list[date]:
    session = get_session()
    try:
        rows = session.execute(
            select(BhavcopyRecord.trade_date).distinct().order_by(BhavcopyRecord.trade_date)
        ).all()
        return [r[0] for r in rows]
    finally:
        session.close()


def get_records_for_date(trade_date: date) -> list[BhavcopyRecord]:
    """All symbols, all expiries, for one trade date — sorted so that
    each symbol's own contracts come out ordered by expiry (front month
    first), which is exactly what the carry-rate estimation needs."""
    session = get_session()
    try:
        return list(
            session.execute(
                select(BhavcopyRecord)
                .where(BhavcopyRecord.trade_date == trade_date)
                .order_by(BhavcopyRecord.symbol, BhavcopyRecord.expiry_date)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def get_records_for_symbol(symbol: str) -> list[BhavcopyRecord]:
    """Full history for one symbol, across all expiries, oldest first."""
    session = get_session()
    try:
        return list(
            session.execute(
                select(BhavcopyRecord)
                .where(BhavcopyRecord.symbol == symbol)
                .order_by(BhavcopyRecord.trade_date, BhavcopyRecord.expiry_date)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def get_signal_history_for_symbol(symbol: str) -> list[SignalRecord]:
    """Full SignalRecord history for one symbol, oldest first -- what
    the backtest engine replays."""
    session = get_session()
    try:
        return list(
            session.execute(
                select(SignalRecord)
                .where(SignalRecord.symbol == symbol)
                .order_by(SignalRecord.trade_date)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()
