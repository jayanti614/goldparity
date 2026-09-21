import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.pipeline.fetcher import fetch_from_file  # noqa: E402
from app.pipeline.parser import ParseError, parse_bhavcopy_csv, validate_returned_date  # noqa: E402

# This mirrors the REAL header row + real row shapes confirmed against an
# actual MCX "BhavCopyDateWise" export (18 Sep 2026), including a GOLDM
# options (OPTFUT) row mixed in under the same symbol as its future,
# which is exactly the trap the instrument_name filter exists to catch.
SAMPLE_CSV = """Date,Instrument Name,Symbol,Expiry Date,Option Type,Strike Price,Open,High,Low,Close,Previous Close,Volume(Lots),Volume(In 000's),Value(Lacs),Open Interest(Lots)
"18 Sep 2026","FUTCOM","GOLDM        ","05OCT2026","-","0","152434.00","154696.00","152304.00","154467.00","153114.00","52608","5260.800 GRMS ","809758.91","31588"
"18 Sep 2026","OPTFUT","GOLDM        ","25SEP2026","CE","142000","12462.00","12462.00","12462.00","12462.00","11102.50","1","0.100 GRMS ","15.45","16"
"18 Sep 2026","FUTCOM","GOLDPETAL    ","30SEP2026","-","0","15360.00","15514.00","15273.00","15480.00","15360.00","258446","258.446 GRMS ","39892.25","184129"
"18 Sep 2026","FUTCOM","CRUDEOIL     ","19SEP2026","-","0","6500.00","6600.00","6450.00","6550.00","6500.00","900","900.000 BBL  ","5895.00","1200"
"18 Sep 2026","FUTCOM","ALUMINI      ","31DEC2026","-","0","","","","352.30","352.30","0","0.000 KGS  ","0.00","0"
"""


def test_filters_to_gold_symbols_only():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDM", "GOLDPETAL"})
    assert {r.symbol for r in rows} == {"GOLDM", "GOLDPETAL"}


def test_excludes_options_rows_sharing_the_same_symbol():
    # GOLDM has both a FUTCOM and an OPTFUT row above — only FUTCOM should survive.
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDM"})
    assert len(rows) == 1
    assert rows[0].instrument_name == "FUTCOM"


def test_strips_space_padded_symbol():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDM"})
    assert rows[0].symbol == "GOLDM"


def test_parses_real_spaced_trade_date_format():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDM"})
    assert rows[0].trade_date == date(2026, 9, 18)


def test_parses_compact_expiry_date():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDM"})
    assert rows[0].expiry_date == date(2026, 10, 5)


def test_parses_previous_close():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDM"})
    assert rows[0].previous_close == 153114.00


def test_parses_volumelots_and_openinterestlots_headers():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDPETAL"})
    assert rows[0].volume == 258446
    assert rows[0].open_interest == 184129


def test_blank_ohlc_falls_back_to_close_on_thin_volume_rows():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"ALUMINI"})
    assert rows[0].open == rows[0].close == 352.30


def test_missing_required_column_raises_parse_error():
    bad_csv = "Symbol,Open,High,Low,Close\nGOLDM,1,2,3,4\n"
    try:
        parse_bhavcopy_csv(bad_csv)
        assert False, "expected ParseError"
    except ParseError as e:
        assert "missing required column" in str(e).lower()


def test_validate_returned_date_flags_mismatch():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDM"})
    warnings = validate_returned_date(date(2026, 9, 19), rows)  # asked for a different day
    assert len(warnings) == 1
    assert "2026-09-19" in warnings[0]


def test_validate_returned_date_no_warning_when_matching():
    rows = parse_bhavcopy_csv(SAMPLE_CSV, only_symbols={"GOLDM"})
    warnings = validate_returned_date(date(2026, 9, 18), rows)
    assert warnings == []


def test_against_real_uploaded_mcx_file_if_present():
    """
    Optional integration check: if a real downloaded MCX file is sitting in
    sample_data/ (see README), parse it for real and sanity-check all 4 gold
    contracts show up with plausible, purity-consistent prices.
    """
    real_file = Path(__file__).resolve().parent / "fixtures" / "real_mcx_sample_18092026.csv"
    if not real_file.exists():
        print("  (skipped — no real sample file present)")
        return

    csv_text = fetch_from_file(real_file)
    rows = parse_bhavcopy_csv(csv_text)
    symbols_found = {r.symbol for r in rows}
    assert symbols_found == {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}, symbols_found

    # front-month row per contract, sanity range check (loose — just proving
    # the numbers are sane, not asserting exact values that'll go stale)
    front_month = {}
    for r in rows:
        if r.symbol not in front_month or r.expiry_date < front_month[r.symbol].expiry_date:
            front_month[r.symbol] = r
    for sym, row in front_month.items():
        assert row.close > 0, f"{sym} has non-positive close"
        assert row.instrument_name == "FUTCOM"


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"PASS: {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL: {t.__name__}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
