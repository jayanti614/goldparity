"""Response schemas for the API. Kept separate from the DB models so the
API's public shape can evolve independently of storage internals."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ContractSpecOut(BaseModel):
    symbol: str
    trading_unit_g: float
    purity: int
    quote_per_g: float
    expiry_window: tuple[int, int]


class SignalOut(BaseModel):
    symbol: str
    trade_date: date
    expiry_date: date
    days_to_expiry: int
    quoted_close: float
    price_per_gram_alloy: float
    price_per_gram_999: float
    purity_effect_pct: float
    carry_rate_daily: float | None
    roll_down_adjusted_price: float
    roll_down_effect_pct: float
    reference_price: float
    residual_signal_pct: float
    is_flagged: bool
    z_score: float | None

    model_config = {"from_attributes": True}


class ArbitrageScoreOut(BaseModel):
    trade_date: date
    score: int  # 0-100, higher = more mispriced right now
    richest_symbol: str
    cheapest_symbol: str
    spread_pct: float  # gap between richest and cheapest residual


class LatestSnapshotOut(BaseModel):
    trade_date: date
    signals: list[SignalOut]
    arbitrage_score: ArbitrageScoreOut


class SignalHistoryPointOut(BaseModel):
    trade_date: date
    residual_signal_pct: float
    is_flagged: bool
    z_score: float | None

    model_config = {"from_attributes": True}


class TradeOut(BaseModel):
    symbol: str
    entry_date: date
    exit_date: date
    direction: int
    entry_residual_pct: float
    exit_residual_pct: float
    raw_return_pct: float
    cost_pct: float
    net_return_pct: float

    model_config = {"from_attributes": True}


class BacktestSummaryOut(BaseModel):
    trades: list[TradeOut]
    n_trades: int
    win_rate: float | None
    mean_return_pct: float | None
    ci_low_pct: float | None
    ci_high_pct: float | None
    ci_level: float | None
    verdict: str


class CarryPointOut(BaseModel):
    trade_date: date
    annualized_rate_pct: float
    r_squared: float
    n_points: int

    model_config = {"from_attributes": True}


class PhaseStatusOut(BaseModel):
    phase: int
    name: str
    status: str  # "built" | "in_progress"


class StatusOut(BaseModel):
    phases: list[PhaseStatusOut]
    latest_trade_date: date | None
    total_trading_days_loaded: int
    total_flagged_signals: int
