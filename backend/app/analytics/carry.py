"""
Phase 5a — Implied Carry Rate.

Backs out a single, market-wide "cost of carry" for gold on MCX for one
trade date, using nothing but that day's own contract curve — no external
gold-lease-rate data needed.

How: pool EVERY (symbol, expiry) fair-value point available that day
(front month + next month, across all 4 contracts = up to 8 points) and
fit a straight line of log(price_per_gram_999) against days_to_expiry.
The slope of that line is the market's implied daily carry rate; fitting
across every available point (rather than averaging each contract's own
2-point estimate, as decomposition.py does per-contract) is the more
statistically grounded version institutional desks use — and the R²
tells you honestly how well the curve actually fits a single carry rate,
rather than presenting a number with false confidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from app.analytics.fair_value import to_fair_values
from app.db import BhavcopyRecord


@dataclass(frozen=True)
class CarryEstimate:
    trade_date: date
    n_points: int
    n_unique_expiries: int
    daily_rate: float
    annualized_rate_pct: float
    r_squared: float


def _ols_slope_intercept(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n
    ss_xy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    ss_xx = sum((x - x_bar) ** 2 for x in xs)
    slope = ss_xy / ss_xx
    intercept = y_bar - slope * x_bar
    return slope, intercept


def _r_squared(xs: list[float], ys: list[float], slope: float, intercept: float) -> float:
    y_bar = sum(ys) / len(ys)
    ss_tot = sum((y - y_bar) ** 2 for y in ys)
    if ss_tot == 0:
        return 1.0  # all points identical -- a flat line fits perfectly
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    return 1 - ss_res / ss_tot


def estimate_implied_carry(records_for_date: list[BhavcopyRecord]) -> CarryEstimate | None:
    """
    records_for_date: every symbol/expiry row for ONE trade date (i.e.
    exactly what db.get_records_for_date() returns).

    Returns None if there isn't enough curve to fit (need at least 2
    distinct days_to_expiry values across the pooled points).
    """
    fair_values = to_fair_values(records_for_date)
    if not fair_values:
        return None

    xs = [fv.days_to_expiry for fv in fair_values]
    ys = [math.log(fv.price_per_gram_999) for fv in fair_values]

    if len(set(xs)) < 2:
        return None  # every point at the same days-to-expiry -- no curve to fit

    slope, intercept = _ols_slope_intercept(xs, ys)
    r2 = _r_squared(xs, ys, slope, intercept)
    annualized_pct = (math.exp(slope * 365) - 1) * 100

    return CarryEstimate(
        trade_date=fair_values[0].trade_date,
        n_points=len(fair_values),
        n_unique_expiries=len(set(xs)),
        daily_rate=slope,
        annualized_rate_pct=annualized_pct,
        r_squared=r2,
    )
