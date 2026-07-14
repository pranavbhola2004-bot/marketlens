"""
Central configuration for the MarketLens backend.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "stocks.json")
SEED_FILE = os.path.join(CACHE_DIR, "stocks.seed.json")
DB_FILE = os.path.join(BASE_DIR, "database", "stocks.db")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# When Yahoo rate-limits, serve demo/seed data instead of an empty UI.
# Background refresh still tries live updates when rate limits clear.
ALLOW_SEED_FALLBACK = os.environ.get("ALLOW_SEED_FALLBACK", "true").lower() in ("1", "true", "yes")

# How long cached fundamentals stay "fresh" before a background refresh is needed.
# NOTE: yfinance hits Yahoo's public, unofficial endpoints. Polling every 30s (as a
# Bloomberg-style terminal would) is a fast way to get rate-limited or IP-blocked.
# 5 minutes is a realistic, sustainable interval for a hobby/portfolio project.
CACHE_TTL_SECONDS = 300
REFRESH_INTERVAL_SECONDS = 300
REFRESH_COOLDOWN_SECONDS = 30

# Default coverage universe (50 NSE large-caps). Replace/extend freely —
# nothing in the code assumes exactly 50 or this exact list.
DEFAULT_WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "SBIN.NS", "LT.NS", "ITC.NS", "HINDUNILVR.NS",
    "BEL.NS", "HAL.NS", "BAJFINANCE.NS", "MARUTI.NS", "AXISBANK.NS",
    "KOTAKBANK.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "NESTLEIND.NS", "ADANIENT.NS", "ADANIPORTS.NS", "ONGC.NS", "NTPC.NS",
    "POWERGRID.NS", "TATASTEEL.NS", "TATAMOTORS.NS", "JSWSTEEL.NS", "COALINDIA.NS",
    "HCLTECH.NS", "TECHM.NS", "ASIANPAINT.NS", "DIVISLAB.NS", "DRREDDY.NS",
    "CIPLA.NS", "BAJAJFINSV.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS",
    "GRASIM.NS", "HINDALCO.NS", "BPCL.NS", "IOC.NS", "SBILIFE.NS",
    "HDFCLIFE.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "INDUSINDBK.NS", "M&M.NS",
]

# Core four used in the market-summary header strip.
HEADER_INDEX_TICKERS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "INDIA VIX": "^INDIAVIX",
}

# Full tracked index set for GET /api/indices (header + sectoral).
ALL_INDEX_TICKERS = {
    **HEADER_INDEX_TICKERS,
    "NIFTY IT": "^CNXIT",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY MIDCAP 50": "^NSEMDCP50",
}

# Back-compat alias used by older call sites.
INDEX_TICKERS = HEADER_INDEX_TICKERS

# Comma-separated origins, e.g. "https://marketlens.vercel.app,http://localhost:3000"
# Default "*" for local dev; set explicitly for public deploys.
_cors_raw = os.environ.get("CORS_ORIGINS", "*").strip()
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()] or ["*"]

# Session cookie settings. For cross-origin (Vercel → Railway) set:
#   COOKIE_SAMESITE=none  COOKIE_SECURE=true
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").lower()
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")

# Portfolio CSV upload limits
PORTFOLIO_MAX_BYTES = 200 * 1024  # 200 KB
PORTFOLIO_MAX_ROWS = 500
