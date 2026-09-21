"""
Gets a day's raw Bhavcopy CSV text, from one of two sources:

  - fetch_from_file(path)   -> WORKING NOW. Reads a CSV already saved
                                to disk (e.g. one you downloaded by hand
                                from mcxindia.com/market-data/bhavcopy).

  - fetch_live(trade_date)  -> STUB. Once we've seen one real response
                                from MCX (headers + request shape), wire
                                the actual HTTP call in here. Until then
                                it raises NotImplementedError on purpose,
                                so a silent wrong-URL guess never gets
                                mistaken for working code.

Why it's split this way: the parser/normalizer/backtester don't care
where the CSV text came from. Once fetch_live() is real, nothing else
in the pipeline needs to change.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path


def fetch_from_file(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No Bhavcopy file at {p}")
    return p.read_text(encoding="utf-8-sig")  # -sig: MCX exports often carry a BOM


def fetch_live(trade_date: date) -> str:
    """
    TODO: implement once we have a verified real request.

    What we know from the brief (not yet verified against a live response):
      - Requests to MCX use DD/MM/YYYY for the date.
      - No API key is required — it's a public page.
      - Indian-exchange sites (NSE, at least) commonly require a session/
        cookie "warm-up" GET before the actual data request succeeds, and
        block requests that look like they're missing browser headers.
        MCX may or may not need the same — unverified.

    To finish this function:
      1. Open https://www.mcxindia.com/market-data/bhavcopy in a browser.
      2. Open DevTools -> Network tab, then trigger a Bhavcopy download.
      3. Find the actual request: its URL, method, query params, and
         request headers (right-click -> Copy -> Copy as cURL is easiest).
      4. Paste that here (or send it to Claude) and this function gets
         filled in to match exactly.
    """
    raise NotImplementedError(
        "Live MCX fetch isn't wired up yet — see the TODO above. "
        "Use fetch_from_file() with a manually downloaded CSV for now."
    )
