"""
Phase 2 — Normalization + Fair Value Engine.

Every MCX gold contract quotes its price in a different unit (per 10g,
per 8g, per 1g) and at a different purity (995 or 999). Before any two
contracts can be honestly compared, both effects have to be removed.

    price_per_gram_alloy = quoted_close / quote_per_g
    price_per_gram_999   = price_per_gram_alloy * (999 / purity)

Why multiply by (999/purity): a gram of 995-purity alloy contains less
actual gold than a gram of 999-purity alloy, so its market price per
gram is naturally *lower* by roughly that ratio — that's not mispricing,
it's chemistry. Scaling every contract up to a common "999-purity
equivalent" price-per-gram removes that effect so what's left over is
comparable across contracts of different purity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.contracts import get_contract
from app.db import BhavcopyRecord

REFERENCE_PURITY = 999


@dataclass(frozen=True)
class FairValueRow:
    symbol: str
    trade_date: date
    expiry_date: date
    days_to_expiry: int
    quoted_close: float
    price_per_gram_alloy: float
    price_per_gram_999: float
    purity_effect_pct: float  # how much of the per-gram price is pure purity math, not signal


def to_fair_value(record: BhavcopyRecord) -> FairValueRow:
    spec = get_contract(record.symbol)
    price_per_gram_alloy = record.close / spec.quote_per_g
    price_per_gram_999 = price_per_gram_alloy * (REFERENCE_PURITY / spec.purity)
    purity_effect_pct = (price_per_gram_999 / price_per_gram_alloy) - 1
    days_to_expiry = (record.expiry_date - record.trade_date).days

    return FairValueRow(
        symbol=record.symbol,
        trade_date=record.trade_date,
        expiry_date=record.expiry_date,
        days_to_expiry=days_to_expiry,
        quoted_close=record.close,
        price_per_gram_alloy=price_per_gram_alloy,
        price_per_gram_999=price_per_gram_999,
        purity_effect_pct=purity_effect_pct,
    )


def to_fair_values(records: list[BhavcopyRecord]) -> list[FairValueRow]:
    return [to_fair_value(r) for r in records]
