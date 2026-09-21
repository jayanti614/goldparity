"""
Generates synthetic Bhavcopy CSVs for the 4 gold contracts, matching the
documented real schema (Symbol, Date, ExpiryDate, Open, High, Low, Close,
Volume, OpenInterest) so the rest of the pipeline can be built and tested
before we're wired up to live (or manually downloaded) MCX data.

The synthetic prices are deliberately built with a KNOWN mispricing
injected on purpose (see INJECTED_GAP_DAY) so that Phase 3's detection
engine has something real to catch during its own testing later.

Usage:
    python scripts/generate_sample_data.py
Writes one CSV per trading day into backend/sample_data/.
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.contracts import CONTRACTS  # noqa: E402

random.seed(42)

OUT_DIR = Path(__file__).resolve().parents[1] / "sample_data"
N_DAYS = 60
START_DATE = date(2026, 6, 1)
BASE_SPOT_PER_G_999 = 8200.0  # illustrative INR/gram at 999 purity
INJECTED_GAP_DAY = 40  # on this trading day, GOLDPETAL is deliberately mispriced


def trading_days(start: date, n: int) -> list[date]:
    days = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:  # skip weekends; holidays not modeled here
            days.append(d)
        d += timedelta(days=1)
    return days


def expiry_for(symbol: str, trade_date: date, months_ahead: int = 0) -> date:
    spec = CONTRACTS[symbol]
    lo, hi = spec.expiry_window
    month = trade_date.month + 1 + months_ahead
    year = trade_date.year
    while month > 12:
        month -= 12
        year += 1
    day = min(hi, 28)
    return date(year, month, day)


MONTHLY_CARRY = 0.004  # ~0.4%/month illustrative cost-of-carry between expiries


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    days = trading_days(START_DATE, N_DAYS)

    # Simulate a slowly drifting spot price with daily noise.
    spot_999 = BASE_SPOT_PER_G_999
    spot_path: list[float] = []
    for _ in days:
        spot_999 *= 1 + random.uniform(-0.006, 0.006)
        spot_path.append(spot_999)

    rows_by_day: dict[date, list[dict]] = {d: [] for d in days}

    for i, trade_date in enumerate(days):
        spot = spot_path[i]
        for symbol, spec in CONTRACTS.items():
            if spec.listed_from and trade_date.isoformat() < spec.listed_from:
                continue  # GOLDTEN doesn't exist yet on early sample days

            # Front month (months_ahead=0) AND next month (months_ahead=1) —
            # this is what lets the pipeline actually estimate each
            # contract's own carry rate and exercise roll-down adjustment,
            # not just purity adjustment.
            for months_ahead in (0, 1):
                # Fair value per contract's own quote unit, purity-adjusted,
                # plus a month-ahead carry markup for the further expiry.
                fair_per_quote_unit = (
                    spot * (spec.purity / 999.0) * spec.quote_per_g * (1 + MONTHLY_CARRY) ** months_ahead
                )

                # Tiny natural noise (bid/ask friction, thin-day liquidity).
                noise = random.uniform(-0.0015, 0.0015)
                close = fair_per_quote_unit * (1 + noise)

                # Deliberately injected, sizeable mispricing on one
                # contract/day (front month only), for the detection
                # engine to find later.
                if i == INJECTED_GAP_DAY and symbol == "GOLDPETAL" and months_ahead == 0:
                    close *= 0.994  # 0.6% artificially cheap

                open_ = close * (1 + random.uniform(-0.001, 0.001))
                high = max(open_, close) * (1 + random.uniform(0.0005, 0.002))
                low = min(open_, close) * (1 - random.uniform(0.0005, 0.002))
                prev_close = close * (1 - random.uniform(-0.002, 0.002))
                volume = random.randint(500, 20000) if months_ahead == 0 else random.randint(50, 3000)
                oi = random.randint(1000, 50000)

                # Column set + date format matches a real confirmed MCX
                # "BhavCopyDateWise" export exactly (verified against a real
                # sample file on 2026-09-20).
                rows_by_day[trade_date].append(
                    {
                        "Date": trade_date.strftime("%d %b %Y"),
                        "Instrument Name": "FUTCOM",
                        "Symbol": f"{symbol:<12} ",  # real exports pad with trailing spaces
                        "Expiry Date": expiry_for(symbol, trade_date, months_ahead).strftime("%d%b%Y").upper(),
                        "Option Type": "-",
                        "Strike Price": "0",
                        "Open": round(open_, 2),
                        "High": round(high, 2),
                        "Low": round(low, 2),
                        "Close": round(close, 2),
                        "Previous Close": round(prev_close, 2),
                        "Volume(Lots)": volume,
                        "Volume(In 000's)": f"{volume / 1000:.3f} GRMS ",
                        "Value(Lacs)": round(volume * close / 100000, 2),
                        "Open Interest(Lots)": oi,
                    }
                )

    fieldnames = [
        "Date", "Instrument Name", "Symbol", "Expiry Date", "Option Type", "Strike Price",
        "Open", "High", "Low", "Close", "Previous Close",
        "Volume(Lots)", "Volume(In 000's)", "Value(Lacs)", "Open Interest(Lots)",
    ]
    for trade_date, rows in rows_by_day.items():
        fname = OUT_DIR / f"bhavcopy_{trade_date.isoformat()}.csv"
        with open(fname, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Wrote {len(days)} sample Bhavcopy CSVs (front + next month per contract) to {OUT_DIR}")
    print(f"Injected mispricing: GOLDPETAL front-month on {days[INJECTED_GAP_DAY].isoformat()} (~0.6% cheap)")


if __name__ == "__main__":
    main()
