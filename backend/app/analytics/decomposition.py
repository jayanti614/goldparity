"""
Phase 3 — Mispricing Detection + Signal Decomposition.

After Phase 2 removes the purity effect, one more non-signal effect
remains: the 4 gold contracts don't all expire on the same day. GOLDM's
near-month contract expires in the 3rd-5th window; GOLDTEN/GOLDGUINEA/
GOLDPETAL expire in the 27th-31st window. A contract with more days left
to expiry carries a bit more (or less) cost-of-carry baked into its
price than one expiring sooner — that's normal term-structure behavior,
not mispricing, and the brief is explicit that this has to be separated
out before calling anything a "signal".

How we estimate each contract's own carry rate, with no external data:
each symbol trades multiple expiries at once (that's in the same
Bhavcopy file). Using a contract's own front-month vs next-month price,
we can back out its own implied daily carry rate — no assumptions
needed about "the" gold lease rate, just what that contract's own curve
says today.

The full waterfall this module produces, per (symbol, trade_date):

    quoted_close
      -> price_per_gram_alloy      (unit-basis normalization)
      -> price_per_gram_999        (purity-adjusted;   purity_effect_pct)
      -> roll_down_adjusted_price  (term-structure adj; roll_down_effect_pct)
      -> compared to reference_price (leave-one-out mean of the OTHER
         contracts -- a contract is never part of its own benchmark)
      -> residual_signal_pct       (what's left over -- the real, tradeable part)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from app.analytics.fair_value import FairValueRow, to_fair_values
from app.contracts import ALL_SYMBOLS
from app.db import BhavcopyRecord


@dataclass(frozen=True)
class SignalDecomposition:
    symbol: str
    trade_date: date
    expiry_date: date
    days_to_expiry: int

    quoted_close: float
    price_per_gram_alloy: float
    price_per_gram_999: float
    purity_effect_pct: float

    carry_rate_daily: float | None  # None when it couldn't be estimated (no next-month data)
    roll_down_adjusted_price: float
    roll_down_effect_pct: float

    reference_price: float
    residual_signal_pct: float  # the genuine, decomposed-out signal


def _estimate_daily_carry_rate(front: FairValueRow, next_: FairValueRow | None) -> float | None:
    """
    Backs out symbol's own implied daily carry rate from its two nearest
    expiries. Returns None if there's no next-month contract to compare
    against (can't estimate a curve from a single point).
    """
    if next_ is None:
        return None
    day_gap = next_.days_to_expiry - front.days_to_expiry
    if day_gap <= 0:
        return None
    return (next_.price_per_gram_999 / front.price_per_gram_999 - 1) / day_gap


def decompose_signals_for_date(records: list[BhavcopyRecord]) -> list[SignalDecomposition]:
    """
    Takes every record for ONE trade date (all symbols, all expiries —
    exactly what db.get_records_for_date() returns) and produces one
    decomposition per symbol, using each symbol's front-month (nearest
    expiry) contract as "the" contract being evaluated.
    """
    fair_values = to_fair_values(records)

    by_symbol: dict[str, list[FairValueRow]] = {}
    for fv in fair_values:
        by_symbol.setdefault(fv.symbol, []).append(fv)
    for symbol in by_symbol:
        by_symbol[symbol].sort(key=lambda r: r.days_to_expiry)

    # Front-month row per symbol, plus each symbol's own estimated carry rate.
    fronts: dict[str, FairValueRow] = {}
    carry_rates: dict[str, float | None] = {}
    for symbol, rows in by_symbol.items():
        front = rows[0]
        next_ = rows[1] if len(rows) > 1 else None
        fronts[symbol] = front
        carry_rates[symbol] = _estimate_daily_carry_rate(front, next_)

    if not fronts:
        return []

    # Common reference point: the SOONEST front-month expiry among the
    # symbols present today. Every contract gets carry-adjusted to this
    # one common day so they're finally comparable apples-to-apples.
    common_days_to_expiry = min(fv.days_to_expiry for fv in fronts.values())

    # Roll-down-adjust every contract to the common reference day.
    adjusted_prices: dict[str, float] = {}
    roll_down_effects: dict[str, float] = {}
    for symbol, fv in fronts.items():
        carry = carry_rates[symbol]
        extra_days = fv.days_to_expiry - common_days_to_expiry
        if carry is None or extra_days == 0:
            adjusted = fv.price_per_gram_999
        else:
            # Discount/accrete linearly back to the common day using this
            # contract's OWN observed daily carry rate.
            adjusted = fv.price_per_gram_999 / (1 + carry * extra_days)
        adjusted_prices[symbol] = adjusted
        roll_down_effects[symbol] = (adjusted / fv.price_per_gram_999) - 1

    results: list[SignalDecomposition] = []
    for symbol, fv in fronts.items():
        adjusted = adjusted_prices[symbol]

        # Leave-one-out reference: a contract's benchmark is the mean of
        # the OTHER contracts, never including itself. Including a
        # contract in its own benchmark mechanically dampens (and, with
        # only 4 contracts, meaningfully biases) its measured deviation --
        # standard relative-value practice is to always compare against
        # an external/independent basket.
        other_prices = [p for s, p in adjusted_prices.items() if s != symbol]
        if not other_prices:
            continue  # only one contract present today -- nothing to compare against
        reference_price = statistics.mean(other_prices)

        residual_pct = (adjusted / reference_price) - 1
        results.append(
            SignalDecomposition(
                symbol=symbol,
                trade_date=fv.trade_date,
                expiry_date=fv.expiry_date,
                days_to_expiry=fv.days_to_expiry,
                quoted_close=fv.quoted_close,
                price_per_gram_alloy=fv.price_per_gram_alloy,
                price_per_gram_999=fv.price_per_gram_999,
                purity_effect_pct=fv.purity_effect_pct,
                carry_rate_daily=carry_rates[symbol],
                roll_down_adjusted_price=adjusted,
                roll_down_effect_pct=roll_down_effects[symbol],
                reference_price=reference_price,
                residual_signal_pct=residual_pct,
            )
        )
    return results
