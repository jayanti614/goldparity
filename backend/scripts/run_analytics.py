"""
Runs the full Phase 2 + 3 analytics pass over everything currently in the
database (loaded there by Phase 1's run_pipeline.py) and stores the
result in signal_records.

Usage:
    python scripts/run_analytics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analytics.persistence import run_full_analytics  # noqa: E402
from app.db import init_db  # noqa: E402


def main() -> None:
    init_db()
    result = run_full_analytics()

    print(f"Decomposed {result['total_decompositions']} (symbol, date) signals.")
    print(f"Stored: {result['inserted']} inserted, {result['updated']} updated.")
    print(f"Flagged as statistically unusual: {result['flagged_count']}")

    if result["flagged"]:
        print("\nFlagged signals:")
        for d in sorted(result["flagged"], key=lambda x: (x.trade_date, x.symbol)):
            print(
                f"  {d.trade_date}  {d.symbol:<11}  "
                f"residual={d.residual_signal_pct:+.4%}  "
                f"purity_effect={d.purity_effect_pct:+.4%}  "
                f"roll_down_effect={d.roll_down_effect_pct:+.4%}"
            )


if __name__ == "__main__":
    main()
