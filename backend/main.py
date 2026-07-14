"""
MarketLens backend — FastAPI application.

Run with:
    uvicorn main:app --reload --port 8000

Then open frontend/index.html in a browser (it calls this API at
http://localhost:8000/api/...), or just visit http://localhost:8000/ since
this app also serves the frontend as static files.
"""
import asyncio
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
import database
import downloader
import screener as screener_module
import sectors as sectors_module
import valuation as valuation_module
import portfolio as portfolio_module
from transform import normalize_batch
from schemas import WatchlistAdd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("marketlens.main")

SESSION_COOKIE = "ml_session"
TICKER_RE = re.compile(r"^[A-Za-z0-9.^&=-]{1,20}$")
_last_manual_refresh = 0.0


def validate_ticker(ticker: str) -> str:
    """Defense-in-depth: only ticker-shaped strings accepted as path params."""
    t = ticker.strip().upper()
    if not TICKER_RE.match(t):
        raise HTTPException(
            400,
            "Invalid ticker: must be 1–20 chars (letters, digits, .^&=- only)",
        )
    return t


async def background_refresh_loop():
    """Refreshes the fundamentals cache on a timer so API requests are always
    served instantly from cache, never blocked on a live Yahoo Finance call.

    IMPORTANT: downloader.refresh_cache() is synchronous (yfinance/requests
    are blocking calls). Running it directly on the event loop would freeze
    every other request for the whole duration of the fetch. asyncio.to_thread
    offloads it to a worker thread so the API stays responsive throughout."""
    while True:
        await asyncio.sleep(config.REFRESH_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(downloader.refresh_cache, config.DEFAULT_WATCHLIST)
        except Exception as e:
            logger.error("Background refresh failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    # Always boot a usable cache (seed if needed) so the UI is never empty.
    downloader.ensure_cache_bootstrapped()
    meta = downloader.cache_meta()
    logger.info(
        "Cache ready: %d stocks (source=%s)",
        meta["stock_count"], meta["source"],
    )

    async def _background_live_refresh():
        # Give Yahoo a breather after any prior 429 storm, then try live upgrade.
        await asyncio.sleep(15)
        try:
            await asyncio.to_thread(downloader.refresh_cache, config.DEFAULT_WATCHLIST)
            await asyncio.to_thread(downloader.refresh_indices_live)
        except Exception as e:
            logger.error("Background live refresh failed: %s", e)

    # Only chase Yahoo in background — never block startup.
    if meta.get("is_seed") or meta.get("stock_count", 0) == 0:
        asyncio.create_task(_background_live_refresh())
    task = asyncio.create_task(background_refresh_loop())
    yield
    task.cancel()


app = FastAPI(title="MarketLens API", version="1.0.0", lifespan=lifespan)

# When origins is ["*"], credentials cannot be enabled (browser CORS rule).
_allow_creds = config.CORS_ORIGINS != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=_allow_creds,
)


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Issue a random httponly session cookie on first visit; scope
    watchlist/portfolio queries by it."""
    session_id = request.cookies.get(SESSION_COOKIE)
    new_cookie = False
    if not session_id or not re.fullmatch(r"[a-f0-9]{32}", session_id):
        session_id = secrets.token_hex(16)
        new_cookie = True
    request.state.session_id = session_id
    response: Response = await call_next(request)
    if new_cookie:
        response.set_cookie(
            key=SESSION_COOKIE,
            value=session_id,
            httponly=True,
            samesite=config.COOKIE_SAMESITE,
            secure=config.COOKIE_SECURE,
            max_age=60 * 60 * 24 * 365,
            path="/",
        )
    return response


def _session(request: Request) -> str:
    return request.state.session_id


def _get_normalized_stocks() -> list[dict]:
    raw = downloader.get_stocks(config.DEFAULT_WATCHLIST)
    return normalize_batch(raw)


# ---------------- Core stock data ----------------
@app.get("/api/status")
def api_status():
    """Data-source health for the frontend banner."""
    return downloader.cache_meta()


@app.get("/api/stocks")
def list_stocks():
    return {"stocks": _get_normalized_stocks(), "meta": downloader.cache_meta()}


@app.get("/api/stock/{ticker}")
def stock_detail(ticker: str):
    ticker = validate_ticker(ticker)
    stocks = _get_normalized_stocks()
    match = next((s for s in stocks if s["ticker"].upper() == ticker), None)
    if not match:
        raise HTTPException(404, f"{ticker} not in current coverage universe")
    valued = valuation_module.compute_valuation(stocks)
    detail = next(s for s in valued if s["ticker"].upper() == ticker)
    return detail


@app.get("/api/stock/{ticker}/history")
def stock_history(ticker: str, period: str = "3mo"):
    ticker = validate_ticker(ticker)
    valid_periods = {"1mo", "3mo", "6mo", "1y", "2y", "5y"}
    if period not in valid_periods:
        raise HTTPException(400, f"period must be one of {sorted(valid_periods)}")
    history = downloader.fetch_history(ticker, period)
    # Synthetic series when Yahoo is blocked so the modal still charts
    if not history:
        stocks = {s["ticker"]: s for s in _get_normalized_stocks()}
        price = (stocks.get(ticker) or {}).get("price") or 100.0
        history = [
            {"date": f"2024-01-{d:02d}", "close": round(price * (0.95 + d * 0.002), 2)}
            for d in range(1, 28)
        ]
    return {"ticker": ticker, "period": period, "history": history}


@app.post("/api/refresh")
def force_refresh():
    """Manually trigger an immediate cache refresh (bypasses the timer).
    Rate-limited to once per REFRESH_COOLDOWN_SECONDS to avoid yfinance spam."""
    global _last_manual_refresh
    now = time.monotonic()
    elapsed = now - _last_manual_refresh
    if _last_manual_refresh and elapsed < config.REFRESH_COOLDOWN_SECONDS:
        retry_after = int(config.REFRESH_COOLDOWN_SECONDS - elapsed) + 1
        raise HTTPException(
            429,
            f"Refresh cooldown active — retry after {retry_after}s",
            headers={"Retry-After": str(retry_after)},
        )
    _last_manual_refresh = now
    raw = downloader.refresh_cache(config.DEFAULT_WATCHLIST)
    cache = downloader.load_cache() or {}
    return {"refreshed": len(raw), "fetched_at": cache.get("fetched_at")}


# ---------------- Screener ----------------
@app.get("/api/screener")
def run_screener(
    max_pe: float | None = None,
    min_roe: float | None = None,
    max_de: float | None = None,
    min_margin: float | None = None,
    min_market_cap: float | None = None,
    min_dividend_yield: float | None = None,
    sector: str | None = None,
    sort_by: str = "roe",
    descending: bool = True,
):
    stocks = _get_normalized_stocks()
    results = screener_module.screen(
        stocks, max_pe, min_roe, max_de, min_margin,
        min_market_cap, min_dividend_yield, sector, sort_by, descending,
    )
    return {"count": len(results), "stocks": results}


# ---------------- Sectors / Peer comparison ----------------
@app.get("/api/sector/{sector}")
def sector_detail(sector: str):
    stocks = _get_normalized_stocks()
    rows = sectors_module.stocks_in_sector(stocks, sector)
    if not rows:
        raise HTTPException(404, f"No stocks found for sector '{sector}'")
    compared = sectors_module.with_peer_comparison(stocks)
    compared = [s for s in compared if s["sector"] == sector]
    return {
        "sector": sector,
        "averages": sectors_module.sector_averages(stocks).get(sector),
        "stocks": compared,
    }


@app.get("/api/sectors")
def all_sector_averages():
    stocks = _get_normalized_stocks()
    return sectors_module.sector_averages(stocks)


# ---------------- Valuation ----------------
@app.get("/api/valuation")
def valuation_insights():
    stocks = _get_normalized_stocks()
    return {"stocks": valuation_module.compute_valuation(stocks)}


# ---------------- Market summary / movers / heatmap / indices ----------------
@app.get("/api/market-summary")
def market_summary():
    stocks = _get_normalized_stocks()
    advances = sum(1 for s in stocks if (s.get("change_pct") or 0) > 0)
    declines = sum(1 for s in stocks if (s.get("change_pct") or 0) < 0)
    unchanged = len(stocks) - advances - declines
    return {
        "indices": downloader.fetch_index_summary(),
        "breadth": {"advances": advances, "declines": declines, "unchanged": unchanged},
    }


@app.get("/api/indices")
def all_indices():
    """All tracked indices including sectoral (separate from header strip)."""
    return {"indices": downloader.fetch_all_indices()}


@app.get("/api/top-gainers")
def top_gainers(limit: int = 10):
    stocks = [s for s in _get_normalized_stocks() if s.get("change_pct") is not None]
    stocks.sort(key=lambda s: s["change_pct"], reverse=True)
    return {"stocks": stocks[:limit]}


@app.get("/api/top-losers")
def top_losers(limit: int = 10):
    stocks = [s for s in _get_normalized_stocks() if s.get("change_pct") is not None]
    stocks.sort(key=lambda s: s["change_pct"])
    return {"stocks": stocks[:limit]}


@app.get("/api/heatmap")
def heatmap():
    """Sector-aggregated average % change, for a heatmap grid."""
    stocks = _get_normalized_stocks()
    by_sector: dict[str, list[float]] = {}
    for s in stocks:
        if s.get("change_pct") is not None:
            by_sector.setdefault(s["sector"], []).append(s["change_pct"])
    return {
        sector: {"avg_change_pct": round(sum(vals) / len(vals), 2), "count": len(vals)}
        for sector, vals in by_sector.items()
    }


# ---------------- Watchlist ----------------
@app.get("/api/watchlist")
def get_watchlist(request: Request):
    return {"watchlist": database.get_watchlist(_session(request))}


@app.post("/api/watchlist")
def add_watchlist(item: WatchlistAdd, request: Request):
    database.add_to_watchlist(_session(request), item.ticker)
    return {"added": item.ticker.upper()}


@app.delete("/api/watchlist/{ticker}")
def remove_watchlist(ticker: str, request: Request):
    ticker = validate_ticker(ticker)
    database.remove_from_watchlist(_session(request), ticker)
    return {"removed": ticker}


# ---------------- Portfolio ----------------
@app.post("/api/portfolio/upload")
async def upload_portfolio(request: Request, file: UploadFile = File(...)):
    """CSV columns required: ticker, quantity, buy_price, buy_date (YYYY-MM-DD)."""
    content = await file.read()
    if len(content) > config.PORTFOLIO_MAX_BYTES:
        raise HTTPException(
            400,
            f"CSV too large ({len(content)} bytes). Max is {config.PORTFOLIO_MAX_BYTES} bytes (~200KB).",
        )
    try:
        holdings = portfolio_module.parse_holdings_csv(content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}")

    session_id = _session(request)
    database.clear_portfolio(session_id)
    for h in holdings:
        database.add_holding(session_id, h["ticker"], h["quantity"], h["buy_price"], h["buy_date"])

    return summarize_current_portfolio(session_id)


@app.get("/api/portfolio/summary")
def portfolio_summary(request: Request):
    return summarize_current_portfolio(_session(request))


def summarize_current_portfolio(session_id: str):
    holdings = database.get_holdings(session_id)
    if not holdings:
        return {"holdings": [], "total_invested": 0, "total_current_value": 0,
                "total_return_pct": None, "xirr_pct": None, "sector_allocation": {}}
    stocks = {s["ticker"]: s for s in _get_normalized_stocks()}
    return portfolio_module.summarize_portfolio(holdings, stocks)


# ---------------- Serve frontend ----------------
# Absolute path so the mount works regardless of process cwd (deployments).
app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
