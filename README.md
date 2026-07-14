# MarketLens

Live equity research terminal: stock screening, peer comparison, relative
valuation, movers/heatmap, NSE indices (incl. India VIX), watchlist, and
portfolio tracking — FastAPI + yfinance backend, vanilla JS frontend with a
classic finance-terminal aesthetic.

```
Yahoo Finance (yfinance)
        │
        ▼
FastAPI backend (Python)
  ├── downloader.py     live fetch + JSON cache (5 min TTL)
  ├── transform.py      normalizes yfinance field names
  ├── sectors.py        sector averages / peer comparison
  ├── valuation.py      relative-valuation flags
  ├── screener.py       multi-criteria filtering
  ├── portfolio.py      CSV upload → value, return %, XIRR, allocation
  └── database.py       SQLite, scoped by session cookie
        │
        ▼
REST API (JSON) — /api/*
        │
        ▼
Frontend (terminal UI + Chart.js) — /  or Vercel static
```

## Quick start (local)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** — the backend serves the frontend. First run
fetches the default 50-stock universe (~20–30s), then serves from a 5-minute
cache. API docs: **http://localhost:8000/docs**

### Tests

```bash
# Backend (mocked yfinance)
cd backend && pytest tests/ -v

# Frontend (jsdom, mocked API)
cd frontend && npm install && npm test
```

## Features

| Feature | Endpoint(s) |
|---|---|
| Coverage universe | `GET /api/stocks` |
| Company detail | `GET /api/stock/{ticker}` |
| Price history | `GET /api/stock/{ticker}/history` |
| Screener | `GET /api/screener` |
| Sector / peers | `GET /api/sectors`, `GET /api/sector/{sector}` |
| Valuation flags | `GET /api/valuation` |
| Header strip (Nifty/Sensex/Bank Nifty/VIX + breadth) | `GET /api/market-summary` |
| All indices (core + sectoral) | `GET /api/indices` |
| Movers / heatmap | `GET /api/top-gainers`, `/api/top-losers`, `/api/heatmap` |
| Watchlist (session-scoped) | `GET/POST /api/watchlist`, `DELETE /api/watchlist/{ticker}` |
| Portfolio CSV | `POST /api/portfolio/upload`, `GET /api/portfolio/summary` |
| Manual refresh (30s cooldown) | `POST /api/refresh` |

Try portfolio upload with `sample_portfolio.csv`.

### Indices tab

`GET /api/indices` returns Nifty 50, Sensex, Bank Nifty, India VIX, plus
sectorals: Nifty IT / Auto / Pharma / FMCG / Metal / Energy / Realty and
Nifty Midcap 50. India VIX is styled as a volatility gauge (calm / elevated /
high), not a price index.

## Security hardening

| Issue | Fix |
|---|---|
| XSS via `innerHTML` | `escapeHtml()` on every dynamic string before insertion |
| DOM XSS via inline `onclick='...${ticker}'` | Replaced with `data-ticker` + delegated click listeners |
| Static path depended on cwd | `StaticFiles` uses absolute `config.FRONTEND_DIR` |
| Shared watchlist/portfolio | `ml_session` httponly cookie; all DB rows scoped by `session_id` |
| CORS `*` | `CORS_ORIGINS` env var (comma-separated); credentials enabled when not `*` |
| Ticker path params unvalidated | Regex `^[A-Za-z0-9.^&=-]{1,20}$` before lookup |
| `/api/refresh` spam | 30s cooldown → HTTP 429 |
| Portfolio CSV unbounded | Max 200KB / 500 rows; field validation with clear 400s |
| Event-loop blocking | Background loop uses `asyncio.to_thread()` around yfinance |

## Deployment (recommended: split)

Vercel serverless cannot host the long-running uvicorn process, background
refresh loop, or durable local SQLite. Deploy like this:

### 1. Backend → Railway (or Render / Fly.io)

**Railway**

1. Create a new project from this repo; set root directory to `backend/`.
2. `backend/Procfile` / `backend/railway.json` start `uvicorn main:app`.
3. Set env vars:
   - `CORS_ORIGINS=https://your-app.vercel.app` (no trailing slash)
   - `COOKIE_SAMESITE=none`
   - `COOKIE_SECURE=true`
4. Attach a persistent volume if you want SQLite/cache to survive restarts
   (or accept ephemeral disk for a demo).

**Render** — see root `render.yaml` (set `CORS_ORIGINS` in the dashboard).

**Fly.io** (example):

```bash
cd backend
fly launch --name marketlens-api --no-deploy
fly secrets set CORS_ORIGINS=https://your-app.vercel.app COOKIE_SAMESITE=none COOKIE_SECURE=true
fly deploy
```

### 2. Frontend → Vercel

1. Import the repo; set **Root Directory** to `frontend/`.
2. Framework Preset: Other. Build uses `frontend/vercel.json`.
3. Set env var `MARKETLENS_API_BASE` to your backend URL, e.g.
   `https://marketlens-api.up.railway.app` (no trailing slash).
4. Deploy. The build injects that URL into `js/config.js`.

Local same-origin serving still works with an empty `MARKETLENS_API_BASE`.

### Vercel-only (not recommended)

If you must stay on Vercel alone, you would need to: drop the background
loop; refresh on demand / via Cron; move cache to Vercel KV and
watchlist/portfolio to Postgres; and stay under the free-tier 10s limit
(parallelize or shrink the universe). Prefer the split path above.

## Project structure

```
MarketLens/
├── backend/
│   ├── main.py             routes, session middleware, rate limit
│   ├── config.py           watchlist, indices, CORS, paths
│   ├── downloader.py       yfinance + cache
│   ├── database.py         session-scoped SQLite
│   ├── portfolio.py        CSV validation + XIRR
│   ├── Procfile / railway.json
│   ├── requirements.txt
│   └── tests/test_api.py
├── frontend/
│   ├── index.html
│   ├── vercel.json
│   ├── css/style.css       terminal theme
│   ├── js/                 utils, api, panels, indices
│   ├── package.json
│   └── tests/dom.test.js
├── render.yaml
├── sample_portfolio.csv
└── README.md
```

## Intentionally not built

News/AI summaries/PDF export, Screener.in scraping, full candlestick/RSI/MACD
kits, and a 5,000-stock NSE universe — each is a separate project. See earlier
notes: `yfinance` is unofficial and best-effort; treat nulls as normal.
