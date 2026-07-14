"""
All contact with Yahoo Finance (via yfinance) lives here. Everything else in
the backend reads from the cache this module maintains, so a slow or rate
limited upstream API never blocks a request from the frontend.

If Yahoo rate-limits (common from residential IPs), we boot from
data/cache/stocks.seed.json so the UI is never empty, then upgrade to live
data in the background when requests succeed.
"""
import json
import threading
import time
import logging
from datetime import datetime, timezone

import yfinance as yf

from config import (
    CACHE_FILE,
    CACHE_TTL_SECONDS,
    SEED_FILE,
    ALLOW_SEED_FALLBACK,
    HEADER_INDEX_TICKERS,
    ALL_INDEX_TICKERS,
)

logger = logging.getLogger("marketlens.downloader")

# Be polite to Yahoo's unofficial endpoint — aggressive polling gets 429s.
DEFAULT_PAUSE = 1.5
MAX_RETRIES = 3
RETRY_BASE_SECONDS = 12

# One Yahoo call at a time across the whole process (stock fill + indices).
_yf_lock = threading.Lock()
_refresh_in_progress = False

FIELDS = [
    "shortName", "sector", "industry", "currentPrice", "previousClose",
    "marketCap", "trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda",
    "returnOnEquity", "returnOnAssets", "debtToEquity", "profitMargins",
    "revenueGrowth", "earningsGrowth", "dividendYield", "beta",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "volume", "trailingEps",
]


def _pct_change(price, prev_close):
    if not price or not prev_close:
        return None
    return round((price - prev_close) / prev_close * 100, 2)


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "too many requests" in msg or "expecting value" in msg


def _empty_row(ticker: str, error: str | None = None) -> dict:
    row = {f: None for f in FIELDS}
    row["ticker"] = ticker
    row["change_pct"] = None
    row["error"] = error
    return row


def fetch_one(ticker: str, pause: float = 0.0) -> dict:
    """Fetch fundamentals for a single ticker. Retries on rate-limits.
    Never raises — returns a partially-filled dict with an 'error' key."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            with _yf_lock:
                info = yf.Ticker(ticker).info or {}
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
            if price is None and not info.get("shortName"):
                raise ValueError("Empty quote response (likely rate-limited)")
            row = {f: info.get(f) for f in FIELDS}
            row["currentPrice"] = price
            row["previousClose"] = prev
            row["ticker"] = ticker
            row["change_pct"] = _pct_change(price, prev)
            row["error"] = None
            if pause:
                time.sleep(pause)
            return row
        except Exception as e:
            last_err = e
            if _is_rate_limited(e) and attempt < MAX_RETRIES - 1:
                wait = RETRY_BASE_SECONDS * (2 ** attempt)
                logger.warning(
                    "Rate-limited on %s (attempt %d/%d) — sleeping %ds",
                    ticker, attempt + 1, MAX_RETRIES, wait,
                )
                time.sleep(wait)
                continue
            logger.warning("Failed to fetch %s: %s", ticker, e)
            break

    if pause:
        time.sleep(pause)
    return _empty_row(ticker, str(last_err) if last_err else "unknown error")


def fetch_batch(tickers: list[str], pause: float = DEFAULT_PAUSE) -> list[dict]:
    """Fetch fundamentals sequentially. Keeps last-good values on failure."""
    previous = {}
    cache = load_cache()
    if cache:
        previous = {s["ticker"]: s for s in cache.get("stocks", [])}

    results = []
    for i, t in enumerate(tickers):
        logger.info("Fetching %s (%d/%d)…", t, i + 1, len(tickers))
        row = fetch_one(t, pause=pause)
        if row.get("error") and t in previous and previous[t].get("currentPrice") is not None:
            kept = dict(previous[t])
            kept["error"] = f"stale (refresh failed: {row['error']})"
            results.append(kept)
        else:
            results.append(row)
        if (i + 1) % 10 == 0:
            _checkpoint(results, tickers[i + 1:], previous)
    return results


def _checkpoint(done: list[dict], remaining: list[str], previous: dict):
    stocks = list(done)
    for t in remaining:
        if t in previous:
            stocks.append(previous[t])
    cache = load_cache() or {}
    save_cache(
        stocks,
        source=cache.get("source", "yahoo"),
        indices=cache.get("indices"),
        all_indices=cache.get("all_indices"),
    )


def fetch_history(ticker: str, period: str = "3mo") -> list[dict]:
    for attempt in range(MAX_RETRIES):
        try:
            with _yf_lock:
                hist = yf.Ticker(ticker).history(period=period)
            return [
                {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
                for idx, row in hist.iterrows()
            ]
        except Exception as e:
            if _is_rate_limited(e) and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_SECONDS * (2 ** attempt))
                continue
            logger.warning("Failed to fetch history for %s: %s", ticker, e)
            return []
    return []


# ---------------- Index quotes (cached — never hammer Yahoo on page load) ----------------
def _seed_indices_fallback() -> tuple[dict, list[dict]]:
    seed = _load_seed()
    if seed:
        return seed.get("indices") or {}, seed.get("all_indices") or []
    # Minimal hardcoded fallback
    header = {
        "NIFTY 50": {"price": 24150.0, "change_pct": 0.0, "error": None},
        "SENSEX": {"price": 79480.0, "change_pct": 0.0, "error": None},
        "BANK NIFTY": {"price": 51220.0, "change_pct": 0.0, "error": None},
        "INDIA VIX": {"price": 14.0, "change_pct": 0.0, "error": None},
    }
    all_idx = [
        {"label": k, "symbol": v, "price": header.get(k, {}).get("price"),
         "change_pct": header.get(k, {}).get("change_pct"), "error": None,
         "is_vix": k == "INDIA VIX"}
        for k, v in ALL_INDEX_TICKERS.items()
    ]
    return header, all_idx


def fetch_index_summary() -> dict:
    """Header-strip indices: prefer cache, never race a stock refresh."""
    cache = load_cache()
    if cache and cache.get("indices"):
        return cache["indices"]
    header, _ = _seed_indices_fallback()
    return header


def fetch_all_indices() -> list[dict]:
    cache = load_cache()
    if cache and cache.get("all_indices"):
        return cache["all_indices"]
    _, all_idx = _seed_indices_fallback()
    return all_idx


def refresh_indices_live() -> None:
    """Optional background update of index quotes (serialized via _yf_lock)."""
    if _refresh_in_progress:
        return
    header = {}
    all_list = []
    for label, symbol in ALL_INDEX_TICKERS.items():
        row = fetch_one(symbol, pause=DEFAULT_PAUSE)
        q = {
            "label": label,
            "symbol": symbol,
            "price": row.get("currentPrice"),
            "change_pct": row.get("change_pct"),
            "error": row.get("error"),
            "is_vix": label == "INDIA VIX",
        }
        all_list.append(q)
        if label in HEADER_INDEX_TICKERS:
            header[label] = {
                "price": q["price"],
                "change_pct": q["change_pct"],
                "error": q["error"],
            }
    # Keep prior values if live fetch failed
    cache = load_cache() or {}
    if any(v.get("price") is None for v in header.values()) and cache.get("indices"):
        for k, v in cache["indices"].items():
            if header.get(k, {}).get("price") is None:
                header[k] = v
    stocks = cache.get("stocks") or []
    save_cache(stocks, source=cache.get("source", "yahoo"), indices=header, all_indices=all_list)


# ---------------- Cache / seed ----------------
def _load_seed() -> dict | None:
    try:
        with open(SEED_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def ensure_cache_bootstrapped() -> dict:
    """Guarantee a usable cache before the API serves requests.
    Prefer existing stocks.json; else copy seed so the UI is never empty."""
    cache = load_cache()
    if cache and cache.get("stocks"):
        return cache
    seed = _load_seed()
    if seed and ALLOW_SEED_FALLBACK:
        logger.warning(
            "No live cache — booting from seed data so the UI is usable "
            "(Yahoo is likely rate-limiting). Background refresh will upgrade when possible."
        )
        save_cache(
            seed["stocks"],
            source="seed",
            indices=seed.get("indices"),
            all_indices=seed.get("all_indices"),
        )
        return load_cache()
    save_cache([], source="empty")
    return load_cache() or {"stocks": [], "source": "empty"}


def save_cache(
    stocks: list[dict],
    source: str = "yahoo",
    indices: dict | None = None,
    all_indices: list | None = None,
):
    existing = load_cache() or {}
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "stocks": stocks,
        "indices": indices if indices is not None else existing.get("indices"),
        "all_indices": all_indices if all_indices is not None else existing.get("all_indices"),
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(payload, f, indent=2, default=str)


def load_cache() -> dict | None:
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def cache_meta() -> dict:
    cache = load_cache() or {}
    stocks = cache.get("stocks") or []
    fresh = sum(1 for s in stocks if not s.get("error"))
    return {
        "source": cache.get("source", "unknown"),
        "fetched_at": cache.get("fetched_at"),
        "stock_count": len(stocks),
        "fresh_count": fresh,
        "refresh_in_progress": _refresh_in_progress,
        "is_seed": cache.get("source") == "seed",
    }


def cache_age_seconds() -> float | None:
    cache = load_cache()
    if not cache or not cache.get("fetched_at"):
        return None
    fetched_at = datetime.fromisoformat(cache["fetched_at"])
    return (datetime.now(timezone.utc) - fetched_at).total_seconds()


def is_cache_fresh() -> bool:
    age = cache_age_seconds()
    cache = load_cache()
    if not cache or cache.get("source") == "seed":
        return False  # always try to upgrade seed → live in background
    return age is not None and age < CACHE_TTL_SECONDS


def refresh_cache(tickers: list[str]) -> list[dict]:
    global _refresh_in_progress
    if _refresh_in_progress:
        logger.info("Refresh already in progress — skipping")
        cache = load_cache()
        return cache["stocks"] if cache else []
    _refresh_in_progress = True
    try:
        logger.info(
            "Refreshing cache for %d tickers (≈%.0fs with polite pacing)…",
            len(tickers), len(tickers) * DEFAULT_PAUSE,
        )
        prev = load_cache() or {}
        stocks = fetch_batch(tickers)
        fresh = sum(1 for s in stocks if not s.get("error"))
        # If Yahoo blocked everything, keep seed rather than wiping to nulls
        if fresh == 0 and prev.get("stocks"):
            logger.warning("Live refresh got 0 fresh quotes — keeping previous cache")
            return prev["stocks"]
        source = "yahoo" if fresh > 0 else prev.get("source", "yahoo")
        save_cache(
            stocks,
            source=source,
            indices=prev.get("indices"),
            all_indices=prev.get("all_indices"),
        )
        logger.info("Cache refreshed: %d fresh / %d total (source=%s)", fresh, len(tickers), source)
        return stocks
    finally:
        _refresh_in_progress = False


def get_stocks(tickers: list[str], force_refresh: bool = False) -> list[dict]:
    """Always return usable rows — never an empty screener while Yahoo is down."""
    ensure_cache_bootstrapped()
    cache = load_cache()
    if not cache:
        return []
    available = [s for s in cache["stocks"] if s["ticker"] in set(tickers)]
    if available and not force_refresh:
        return available
    if _refresh_in_progress:
        return available
    if force_refresh:
        return refresh_cache(tickers)
    return available
