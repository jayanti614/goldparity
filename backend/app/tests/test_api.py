import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_root_returns_200():
    r = client.get("/")
    assert r.status_code == 200


def test_status_endpoint_lists_nine_phases():
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert len(data["phases"]) == 9
    assert data["phases"][0]["status"] == "built"


def test_contracts_endpoint_returns_all_four_gold_contracts():
    r = client.get("/api/contracts")
    assert r.status_code == 200
    symbols = {c["symbol"] for c in r.json()}
    assert symbols == {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}


def test_unknown_symbol_history_returns_404():
    r = client.get("/api/signals/history/NOTAREALCONTRACT")
    assert r.status_code == 404


def test_valid_symbol_history_returns_200_list():
    r = client.get("/api/signals/history/GOLDPETAL")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_backtest_endpoint_always_returns_a_verdict():
    r = client.get("/api/backtest")
    assert r.status_code == 200
    assert "verdict" in r.json()
    assert isinstance(r.json()["verdict"], str) and len(r.json()["verdict"]) > 0


def test_latest_signals_endpoint_shape_when_data_present():
    r = client.get("/api/signals/latest")
    if r.status_code == 404:
        print("  (skipped detailed checks -- no data loaded yet; run the pipeline scripts first)")
        return
    data = r.json()
    assert "arbitrage_score" in data
    assert 0 <= data["arbitrage_score"]["score"] <= 100
    assert len(data["signals"]) >= 1


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
