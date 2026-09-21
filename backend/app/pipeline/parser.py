"""
Parses raw MCX Bhavcopy CSV rows into clean, typed records.

Handles the quirks the hackathon brief explicitly warns about:
  - Symbol values may be space-padded            -> stripped
  - Date in the response is MM/DD/YYYY            -> parsed explicitly
    (note: REQUESTS to MCX use DD/MM/YYYY -- that's a fetcher-side
    concern, not a parser-side one; see fetcher.py)
  - ExpiryDate is a compact form like "04SEP2026" -> parsed with %d%b%Y
  - Column headers aren't guaranteed to match one exact casing/spacing,
    so header lookup is fuzzy (case/space/underscore-insensitive).

If you (or a teammate) upload a real Bhavcopy CSV and the columns don't
match what's expected here, `ParseError` will say exactly which column
was missing/unparseable instead of failing silently.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from app.contracts import ALL_SYMBOLS


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class BhavcopyRow:
    symbol: str
    instrument_name: str
    trade_date: date
    expiry_date: date
    open: float
    high: float
    low: float
    close: float
    previous_close: float | None
    volume: int
    open_interest: int


# Maps a normalized header key -> the canonical field name we use.
# Add aliases here as soon as a real file shows a header we didn't expect.
#
# Confirmed against a real MCX "BhavCopyDateWise" export (18 Sep 2026):
#   Date,Instrument Name,Symbol,Expiry Date,Option Type,Strike Price,
#   Open,High,Low,Close,Previous Close,Volume(Lots),Volume(In 000's),
#   Value(Lacs),Open Interest(Lots)
_HEADER_ALIASES: dict[str, str] = {
    "symbol": "symbol",
    "instrumentname": "instrument_name",
    "date": "trade_date",
    "tradedate": "trade_date",
    "expirydate": "expiry_date",
    "expiry": "expiry_date",
    "open": "open",
    "openprice": "open",
    "high": "high",
    "highprice": "high",
    "low": "low",
    "lowprice": "low",
    "close": "close",
    "closeprice": "close",
    "settlementprice": "close",
    "previousclose": "previous_close",
    "volume": "volume",
    "volumelots": "volume",
    "openinterest": "open_interest",
    "openinterestlots": "open_interest",
    "oi": "open_interest",
}

# Rows that aren't a plain futures contract (options, in MCX's export, carry
# Instrument Name "OPTFUT" and share the *same* Symbol as the future — e.g.
# GOLDM has both FUTCOM and OPTFUT rows). We only ever want FUTCOM.
FUTURES_INSTRUMENT_NAME = "FUTCOM"


def _normalize_header(raw: str) -> str:
    cleaned = raw.strip().lower().replace(" ", "").replace("_", "")
    for ch in "()'\"":
        cleaned = cleaned.replace(ch, "")
    return cleaned


def _resolve_headers(fieldnames: list[str]) -> dict[str, str]:
    """Returns {canonical_field_name: original_csv_column_name}."""
    resolved: dict[str, str] = {}
    for raw in fieldnames:
        norm = _normalize_header(raw)
        canonical = _HEADER_ALIASES.get(norm)
        if canonical:
            resolved[canonical] = raw
    required = {"symbol", "trade_date", "expiry_date", "open", "high", "low", "close"}
    missing = required - resolved.keys()
    if missing:
        raise ParseError(
            f"CSV is missing required column(s): {sorted(missing)}. "
            f"Columns found: {fieldnames}. "
            "Update _HEADER_ALIASES in parser.py once you know the real header names."
        )
    return resolved


_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _parse_month_name_date(raw: str) -> date | None:
    """
    Parses either "18 Sep 2026" (spaced, confirmed real MCX format) or
    "18SEP2026" (compact, used for ExpiryDate) without relying on the
    system locale's month names (strptime's %b is locale-dependent —
    risky on a Windows machine that might not be set to English).
    """
    s = raw.strip().upper().replace(",", "")
    s_compact = s.replace(" ", "")
    if len(s_compact) < 7:
        return None
    # day is 1-2 digits at the start
    day_str = s_compact[:2] if s_compact[1].isdigit() else s_compact[:1]
    rest = s_compact[len(day_str):]
    month_str = rest[:3]
    year_str = rest[3:]
    if month_str not in _MONTHS or not year_str.isdigit():
        return None
    try:
        return date(int(year_str), _MONTHS[month_str], int(day_str))
    except ValueError:
        return None


def _parse_trade_date(raw: str) -> date:
    raw = raw.strip()
    parsed = _parse_month_name_date(raw)
    if parsed:
        return parsed
    # Fallback formats, in case a different MCX report variant is used.
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ParseError(f"Could not parse trade date: {raw!r}")


def _parse_expiry_date(raw: str) -> date:
    raw = raw.strip()
    parsed = _parse_month_name_date(raw)
    if parsed:
        return parsed
    for fmt in ("%d/%m/%Y",):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ParseError(f"Could not parse expiry date: {raw!r}")


def _to_float(raw: str, field: str, *, fallback: float | None = None) -> float:
    text = str(raw).strip().replace(",", "")
    if text == "" and fallback is not None:
        return fallback
    try:
        return float(text)
    except ValueError:
        raise ParseError(f"Could not parse numeric field {field!r}: {raw!r}")


def _to_optional_float(raw: str | None) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(str(raw).strip().replace(",", ""))
    except ValueError:
        return None


def _to_int(raw: str | None, field: str) -> int:
    if raw is None or str(raw).strip() == "":
        return 0
    try:
        return int(float(str(raw).strip().replace(",", "")))
    except ValueError:
        raise ParseError(f"Could not parse numeric field {field!r}: {raw!r}")


def parse_bhavcopy_csv(
    csv_text: str,
    *,
    only_symbols: set[str] | None = None,
    instrument_names: set[str] | None = frozenset({FUTURES_INSTRUMENT_NAME}),
) -> list[BhavcopyRow]:
    """
    Parses the full text of a Bhavcopy CSV and returns clean rows.

    only_symbols: if given, rows for any other symbol are silently skipped
                  (a Bhavcopy file contains every MCX commodity, not just gold).

    instrument_names: if the file has an "Instrument Name" column (real MCX
                  exports do), only rows matching one of these are kept.
                  Defaults to {"FUTCOM"} — this is what excludes options rows,
                  which otherwise share the *same* Symbol as the future
                  (e.g. GOLDM has both FUTCOM and OPTFUT rows). Pass None to
                  disable this filter (e.g. for a file that has no such column).
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ParseError("CSV appears to be empty (no header row found).")
    headers = _resolve_headers(list(reader.fieldnames))

    wanted = only_symbols or set(ALL_SYMBOLS)
    rows: list[BhavcopyRow] = []

    for i, raw_row in enumerate(reader, start=2):  # start=2: header is line 1
        symbol = raw_row[headers["symbol"]].strip().upper()
        if symbol not in wanted:
            continue

        instrument_name = ""
        if "instrument_name" in headers:
            instrument_name = raw_row[headers["instrument_name"]].strip().upper()
            if instrument_names is not None and instrument_name not in instrument_names:
                continue

        try:
            close = _to_float(raw_row[headers["close"]], "close")
            rows.append(
                BhavcopyRow(
                    symbol=symbol,
                    instrument_name=instrument_name,
                    trade_date=_parse_trade_date(raw_row[headers["trade_date"]]),
                    expiry_date=_parse_expiry_date(raw_row[headers["expiry_date"]]),
                    open=_to_float(raw_row[headers["open"]], "open", fallback=close),
                    high=_to_float(raw_row[headers["high"]], "high", fallback=close),
                    low=_to_float(raw_row[headers["low"]], "low", fallback=close),
                    close=close,
                    previous_close=_to_optional_float(raw_row.get(headers.get("previous_close", ""), None)),
                    volume=_to_int(raw_row.get(headers.get("volume", ""), "0"), "volume"),
                    open_interest=_to_int(raw_row.get(headers.get("open_interest", ""), "0"), "open_interest"),
                )
            )
        except ParseError as e:
            raise ParseError(f"Row {i}: {e}") from e

    return rows


def validate_returned_date(requested: date, rows: list[BhavcopyRow]) -> list[str]:
    """
    The brief warns MCX may silently return the most recent available
    trading day instead of the one you asked for (weekends, holidays,
    bad input). Call this after parsing to get human-readable warnings
    instead of silently trusting mismatched data.
    """
    warnings: list[str] = []
    mismatched = {r.trade_date for r in rows if r.trade_date != requested}
    if mismatched:
        warnings.append(
            f"Requested {requested.isoformat()} but response contains date(s) "
            f"{sorted(d.isoformat() for d in mismatched)} — MCX likely fell back "
            "to the most recent trading day. Treat this batch's date as the "
            "returned date, not the requested one."
        )
    return warnings
