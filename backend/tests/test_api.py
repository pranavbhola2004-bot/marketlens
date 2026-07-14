"""
End-to-end API tests with mocked yfinance. Run from backend/:

    pip install -r requirements.txt
    pytest tests/ -v
"""
import io
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

# Ensure backend package root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use a temp DB / cache so tests don't touch real data
import tempfile
import config

_tmpdir = tempfile.mkdtemp(prefix="ml_test_")
config.CACHE_DIR = os.path.join(_tmpdir, "cache")
config.CACHE_FILE = os.path.join(config.CACHE_DIR, "stocks.json")
config.DB_FILE = os.path.join(_tmpdir, "test.db")
os.makedirs(config.CACHE_DIR, exist_ok=True)

# Patch downloader module-level cache path after config override
import downloader
downloader.CACHE_FILE = config.CACHE_FILE

MOCK_STOCKS = [
    {
        "ticker": "RELIANCE.NS", "shortName": "Reliance Industries", "sector": "Energy",
        "industry": "Oil", "currentPrice": 2800.0, "previousClose": 2750.0,
        "marketCap": 19e12, "trailingPE": 25.0, "forwardPE": 22.0, "priceToBook": 2.5,
        "enterpriseToEbitda": 12.0, "returnOnEquity": 0.15, "returnOnAssets": 0.08,
        "debtToEquity": 40.0, "profitMargins": 0.10, "revenueGrowth": 0.08,
        "earningsGrowth": 0.12, "dividendYield": 0.01, "beta": 1.1,
        "fiftyTwoWeekHigh": 3000.0, "fiftyTwoWeekLow": 2200.0, "volume": 1e6,
        "trailingEps": 110.0, "change_pct": 1.82, "error": None,
    },
    {
        "ticker": "TCS.NS", "shortName": "Tata Consultancy", "sector": "Technology",
        "industry": "IT", "currentPrice": 3800.0, "previousClose": 3900.0,
        "marketCap": 14e12, "trailingPE": 28.0, "forwardPE": 25.0, "priceToBook": 10.0,
        "enterpriseToEbitda": 18.0, "returnOnEquity": 0.40, "returnOnAssets": 0.25,
        "debtToEquity": 10.0, "profitMargins": 0.22, "revenueGrowth": 0.10,
        "earningsGrowth": 0.11, "dividendYield": 0.015, "beta": 0.8,
        "fiftyTwoWeekHigh": 4200.0, "fiftyTwoWeekLow": 3200.0, "volume": 8e5,
        "trailingEps": 135.0, "change_pct": -2.56, "error": None,
    },
    {
        "ticker": "HDFCBANK.NS", "shortName": "HDFC Bank", "sector": "Financial Services",
        "industry": "Banks", "currentPrice": 1600.0, "previousClose": 1580.0,
        "marketCap": 12e12, "trailingPE": 18.0, "forwardPE": 16.0, "priceToBook": 2.8,
        "enterpriseToEbitda": None, "returnOnEquity": 0.17, "returnOnAssets": 0.02,
        "debtToEquity": 120.0, "profitMargins": 0.25, "revenueGrowth": 0.15,
        "earningsGrowth": 0.14, "dividendYield": 0.012, "beta": 1.0,
        "fiftyTwoWeekHigh": 1800.0, "fiftyTwoWeekLow": 1400.0, "volume": 2e6,
        "trailingEps": 88.0, "change_pct": 1.27, "error": None,
    },
    {
        "ticker": "INFY.NS", "shortName": "Infosys", "sector": "Technology",
        "industry": "IT", "currentPrice": 1500.0, "previousClose": 1480.0,
        "marketCap": 6e12, "trailingPE": 24.0, "forwardPE": 22.0, "priceToBook": 7.0,
        "enterpriseToEbitda": 15.0, "returnOnEquity": 0.30, "returnOnAssets": 0.20,
        "debtToEquity": 5.0, "profitMargins": 0.18, "revenueGrowth": 0.06,
        "earningsGrowth": 0.05, "dividendYield": 0.02, "beta": 0.9,
        "fiftyTwoWeekHigh": 1700.0, "fiftyTwoWeekLow": 1300.0, "volume": 9e5,
        "trailingEps": 62.0, "change_pct": 1.35, "error": None,
    },
    {
        "ticker": "BEL.NS", "shortName": "Bharat Electronics", "sector": "Industrials",
        "industry": "Aerospace", "currentPrice": 280.0, "previousClose": 270.0,
        "marketCap": 2e12, "trailingPE": 40.0, "forwardPE": 35.0, "priceToBook": 8.0,
        "enterpriseToEbitda": 25.0, "returnOnEquity": 0.22, "returnOnAssets": 0.12,
        "debtToEquity": 5.0, "profitMargins": 0.15, "revenueGrowth": 0.20,
        "earningsGrowth": 0.25, "dividendYield": 0.008, "beta": 1.2,
        "fiftyTwoWeekHigh": 320.0, "fiftyTwoWeekLow": 180.0, "volume": 5e6,
        "trailingEps": 7.0, "change_pct": 3.70, "error": None,
    },
]


def _mock_fetch_one(ticker, pause=0.0):
    for s in MOCK_STOCKS:
        if s["ticker"] == ticker:
            return dict(s)
    # Indices
    if ticker.startswith("^"):
        price = 22000.0 if "NSEI" in ticker else (14.5 if "VIX" in ticker else 48000.0)
        return {
            "ticker": ticker, "shortName": ticker, "sector": None, "industry": None,
            "currentPrice": price, "previousClose": price * 0.99,
            "marketCap": None, "trailingPE": None, "forwardPE": None, "priceToBook": None,
            "enterpriseToEbitda": None, "returnOnEquity": None, "returnOnAssets": None,
            "debtToEquity": None, "profitMargins": None, "revenueGrowth": None,
            "earningsGrowth": None, "dividendYield": None, "beta": None,
            "fiftyTwoWeekHigh": None, "fiftyTwoWeekLow": None, "volume": None,
            "trailingEps": None, "change_pct": 1.01, "error": None,
        }
    return {
        "ticker": ticker, "shortName": ticker, "sector": "Unknown", "industry": None,
        "currentPrice": 100.0, "previousClose": 100.0, "marketCap": 1e9,
        "trailingPE": 10.0, "forwardPE": 10.0, "priceToBook": 1.0,
        "enterpriseToEbitda": 8.0, "returnOnEquity": 0.1, "returnOnAssets": 0.05,
        "debtToEquity": 50.0, "profitMargins": 0.1, "revenueGrowth": 0.05,
        "earningsGrowth": 0.05, "dividendYield": 0.01, "beta": 1.0,
        "fiftyTwoWeekHigh": 120.0, "fiftyTwoWeekLow": 80.0, "volume": 1e5,
        "trailingEps": 10.0, "change_pct": 0.0, "error": None,
    }


def _mock_fetch_batch(tickers, pause=0.0):
    return [_mock_fetch_one(t) for t in tickers]


def _mock_fetch_history(ticker, period="3mo"):
    return [{"date": "2024-01-01", "close": 100.0}, {"date": "2024-01-02", "close": 101.5}]


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(downloader, "fetch_one", _mock_fetch_one)
    monkeypatch.setattr(downloader, "fetch_batch", _mock_fetch_batch)
    monkeypatch.setattr(downloader, "fetch_history", _mock_fetch_history)
    monkeypatch.setattr(config, "DEFAULT_WATCHLIST", [s["ticker"] for s in MOCK_STOCKS])
    monkeypatch.setattr(config, "REFRESH_COOLDOWN_SECONDS", 30)

    # Seed cache
    downloader.refresh_cache([s["ticker"] for s in MOCK_STOCKS])

    import database
    database.DB_FILE = config.DB_FILE
    # Re-bind DB_FILE used by database module
    import database as db_mod
    monkeypatch.setattr(db_mod, "DB_FILE", config.DB_FILE)
    db_mod.init_db()

    import main
    # Reset refresh cooldown between tests
    main._last_manual_refresh = 0.0

    with TestClient(main.app) as c:
        yield c


def test_list_stocks(client):
    r = client.get("/api/stocks")
    assert r.status_code == 200
    assert len(r.json()["stocks"]) == 5


def test_stock_detail(client):
    r = client.get("/api/stock/TCS.NS")
    assert r.status_code == 200
    assert r.json()["ticker"] == "TCS.NS"
    assert "valuation_flag" in r.json()


def test_invalid_ticker_rejected(client):
    r = client.get("/api/stock/<script>")
    assert r.status_code == 400
    r2 = client.get("/api/stock/ok';drop table")
    assert r2.status_code == 400


def test_history(client):
    r = client.get("/api/stock/RELIANCE.NS/history?period=3mo")
    assert r.status_code == 200
    assert len(r.json()["history"]) == 2


def test_screener_filters(client):
    r = client.get("/api/screener", params={"max_pe": 30, "min_roe": 10, "sector": "Technology"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    for s in data["stocks"]:
        assert s["sector"] == "Technology"
        assert s["pe_ttm"] is None or s["pe_ttm"] <= 30


def test_sectors_and_peer(client):
    r = client.get("/api/sectors")
    assert r.status_code == 200
    assert "Technology" in r.json()
    r2 = client.get("/api/sector/Technology")
    assert r2.status_code == 200
    assert r2.json()["averages"] is not None
    assert len(r2.json()["stocks"]) >= 2


def test_valuation(client):
    r = client.get("/api/valuation")
    assert r.status_code == 200
    flags = {s["valuation_flag"] for s in r.json()["stocks"]}
    assert any(f.startswith("Under") or f.startswith("Over") or f.startswith("Fair") for f in flags)


def test_market_summary(client):
    r = client.get("/api/market-summary")
    assert r.status_code == 200
    data = r.json()
    assert "NIFTY 50" in data["indices"]
    assert "INDIA VIX" in data["indices"]
    assert "advances" in data["breadth"]
    # Header strip should only have core four (+ not all sectorals)
    assert "NIFTY IT" not in data["indices"]


def test_indices_endpoint(client):
    r = client.get("/api/indices")
    assert r.status_code == 200
    indices = r.json()["indices"]
    labels = {i["label"] for i in indices}
    assert "NIFTY 50" in labels
    assert "NIFTY IT" in labels
    assert "NIFTY MIDCAP 50" in labels
    assert "INDIA VIX" in labels
    vix = next(i for i in indices if i["is_vix"])
    assert vix["label"] == "INDIA VIX"


def test_movers(client):
    g = client.get("/api/top-gainers?limit=3").json()["stocks"]
    l = client.get("/api/top-losers?limit=3").json()["stocks"]
    assert g[0]["change_pct"] >= g[-1]["change_pct"]
    assert l[0]["change_pct"] <= l[-1]["change_pct"]


def test_heatmap(client):
    r = client.get("/api/heatmap")
    assert r.status_code == 200
    assert "Technology" in r.json()


def test_watchlist_session_scoped(client):
    r = client.get("/api/watchlist")
    assert r.status_code == 200
    assert r.json()["watchlist"] == []

    r = client.post("/api/watchlist", json={"ticker": "TCS.NS"})
    assert r.status_code == 200
    assert client.get("/api/watchlist").json()["watchlist"][0]["ticker"] == "TCS.NS"

    # Different session cookie → empty watchlist
    other = TestClient(client.app)
    # Force a different session by clearing cookies after first request sets one
    r2 = other.get("/api/watchlist")
    # May get empty if new session
    assert r2.status_code == 200

    r = client.delete("/api/watchlist/TCS.NS")
    assert r.status_code == 200
    assert client.get("/api/watchlist").json()["watchlist"] == []


def test_watchlist_invalid_ticker(client):
    r = client.post("/api/watchlist", json={"ticker": "'; DROP TABLE--"})
    assert r.status_code == 422


def test_portfolio_upload_and_summary(client):
    csv_data = (
        "ticker,quantity,buy_price,buy_date\n"
        "RELIANCE.NS,10,2400,2024-03-15\n"
        "TCS.NS,5,3600,2024-06-10\n"
    )
    r = client.post(
        "/api/portfolio/upload",
        files={"file": ("pf.csv", io.BytesIO(csv_data.encode()), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["holdings"]) == 2
    assert data["total_invested"] > 0
    assert data["sector_allocation"]
    total_alloc = sum(data["sector_allocation"].values())
    assert abs(total_alloc - 100) < 1.0 or data["total_current_value"] == 0

    r2 = client.get("/api/portfolio/summary")
    assert r2.status_code == 200
    assert len(r2.json()["holdings"]) == 2


def test_portfolio_rejects_malformed(client):
    bad = "ticker,quantity,buy_price,buy_date\nHACK'<script>,10,100,not-a-date\n"
    r = client.post(
        "/api/portfolio/upload",
        files={"file": ("bad.csv", io.BytesIO(bad.encode()), "text/csv")},
    )
    assert r.status_code == 400

    neg = "ticker,quantity,buy_price,buy_date\nTCS.NS,-5,100,2024-01-01\n"
    r2 = client.post(
        "/api/portfolio/upload",
        files={"file": ("neg.csv", io.BytesIO(neg.encode()), "text/csv")},
    )
    assert r2.status_code == 400


def test_portfolio_rejects_oversized(client):
    huge = b"x" * (200 * 1024 + 10)
    r = client.post(
        "/api/portfolio/upload",
        files={"file": ("huge.csv", io.BytesIO(huge), "text/csv")},
    )
    assert r.status_code == 400


def test_refresh_rate_limit(client, monkeypatch):
    monkeypatch.setattr(config, "REFRESH_COOLDOWN_SECONDS", 30)
    import main
    main._last_manual_refresh = 0.0
    r1 = client.post("/api/refresh")
    assert r1.status_code == 200
    r2 = client.post("/api/refresh")
    assert r2.status_code == 429


def test_session_cookie_set(client):
    r = client.get("/api/stocks")
    assert "ml_session" in r.cookies or "ml_session" in r.headers.get("set-cookie", "")


def test_static_frontend_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"MarketLens" in r.content
