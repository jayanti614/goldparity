"""
Phase 5b — Delivery-Risk-Aware Signal Filtering.

Verified against real MCX broker circulars (checked 2026-09-21, e.g.
Zerodha/FYERS expiry notices): GOLDM, GOLDGUINEA, GOLDPETAL and GOLDTEN
are all "staggered/compulsory delivery" contracts. The staggered
delivery tender period begins a few days before expiry (circulars cite
~3 days), and brokers require positions to be squared off before that
window opens or risk forced square-off / physical delivery.

Earlier in this project we described this as "no fresh positions on
expiry day" for 3 of the 4 contracts — that framing was wrong on two
counts (it's a several-day pre-expiry window, not just expiry day
itself, and it applies to all 4 contracts, not 3). This module uses the
corrected, source-checked version.

What this means for signal quality: a mispricing signal that looks
attractive on paper is worthless if acting on it would force you to
either exit early (eating the cost before convergence has time to play
out) or get automatically squared off / risk taking physical delivery.
This filter suppresses/flags exactly that case.
"""

from __future__ import annotations

# Conservative safety margin ahead of the ~3-day tender window cited in
# broker circulars, to account for the fact that brokers ask clients to
# square off *before* the window opens, not at its edge.
DELIVERY_BUFFER_DAYS = 5


def is_within_delivery_risk_window(
    days_to_expiry: int,
    holding_period_days: int = 0,
    buffer_days: int = DELIVERY_BUFFER_DAYS,
) -> bool:
    """
    True if a position entered today and held for holding_period_days
    would still be open once the contract enters its delivery-risk
    window (i.e. there isn't enough runway left before expiry to safely
    hold the full planned period).
    """
    days_remaining_after_hold = days_to_expiry - holding_period_days
    return days_remaining_after_hold < buffer_days


def filter_signals_by_delivery_risk(
    signals: list,  # SignalRecord-like: needs .days_to_expiry
    holding_period_days: int,
    buffer_days: int = DELIVERY_BUFFER_DAYS,
) -> tuple[list, list]:
    """Splits signals into (safe_to_trade, excluded_for_delivery_risk)."""
    safe, excluded = [], []
    for s in signals:
        if is_within_delivery_risk_window(s.days_to_expiry, holding_period_days, buffer_days):
            excluded.append(s)
        else:
            safe.append(s)
    return safe, excluded
