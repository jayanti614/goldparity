"""
Loads parsed BhavcopyRow records into the database.

Idempotent: re-loading the same file twice does not create duplicates
(upsert on the symbol + trade_date + expiry_date unique key).
"""

from __future__ import annotations

from sqlalchemy import select

from app.db import BhavcopyRecord, get_session
from app.pipeline.parser import BhavcopyRow


def load_rows(rows: list[BhavcopyRow]) -> dict[str, int]:
    """Returns {"inserted": n, "updated": n, "unchanged": n}."""
    inserted = updated = unchanged = 0
    session = get_session()
    try:
        for row in rows:
            existing = session.scalar(
                select(BhavcopyRecord).where(
                    BhavcopyRecord.symbol == row.symbol,
                    BhavcopyRecord.trade_date == row.trade_date,
                    BhavcopyRecord.expiry_date == row.expiry_date,
                )
            )
            if existing is None:
                session.add(
                    BhavcopyRecord(
                        symbol=row.symbol,
                        trade_date=row.trade_date,
                        expiry_date=row.expiry_date,
                        open=row.open,
                        high=row.high,
                        low=row.low,
                        close=row.close,
                        volume=row.volume,
                        open_interest=row.open_interest,
                    )
                )
                inserted += 1
            else:
                changed = (
                    existing.open != row.open
                    or existing.high != row.high
                    or existing.low != row.low
                    or existing.close != row.close
                    or existing.volume != row.volume
                    or existing.open_interest != row.open_interest
                )
                if changed:
                    existing.open, existing.high, existing.low, existing.close = (
                        row.open,
                        row.high,
                        row.low,
                        row.close,
                    )
                    existing.volume = row.volume
                    existing.open_interest = row.open_interest
                    updated += 1
                else:
                    unchanged += 1
        session.commit()
    finally:
        session.close()
    return {"inserted": inserted, "updated": updated, "unchanged": unchanged}
