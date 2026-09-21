"""
Loads every Bhavcopy CSV in sample_data/ (or a directory you point at)
into the database.

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --dir path/to/real/downloaded/csvs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import init_db  # noqa: E402
from app.pipeline.fetcher import fetch_from_file  # noqa: E402
from app.pipeline.loader import load_rows  # noqa: E402
from app.pipeline.parser import parse_bhavcopy_csv, validate_returned_date  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir",
        default=str(Path(__file__).resolve().parents[1] / "sample_data"),
        help="Directory of Bhavcopy CSV files to load",
    )
    args = parser.parse_args()

    init_db()

    csv_dir = Path(args.dir)
    files = sorted(csv_dir.glob("*.csv"))
    if not files:
        print(f"No CSV files found in {csv_dir}")
        return

    totals = {"inserted": 0, "updated": 0, "unchanged": 0}
    warnings: list[str] = []

    for f in files:
        csv_text = fetch_from_file(f)
        rows = parse_bhavcopy_csv(csv_text)
        if rows:
            # sanity-check every distinct trade_date found against itself —
            # catches the "MCX returned a different day than expected" case
            # even when loading from a locally saved file.
            for d in {r.trade_date for r in rows}:
                warnings += validate_returned_date(d, [r for r in rows if r.trade_date == d])
        result = load_rows(rows)
        for k in totals:
            totals[k] += result[k]

    print(f"Processed {len(files)} file(s).")
    print(f"Inserted: {totals['inserted']}, Updated: {totals['updated']}, Unchanged: {totals['unchanged']}")
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
