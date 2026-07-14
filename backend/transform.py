"""
Converts the raw, inconsistent yfinance field names into a stable, clean
schema that the rest of the backend (and the frontend) can rely on.
Keeping this in one place means a Yahoo field-name change only needs a
one-line fix here.
"""


def normalize(raw: dict) -> dict:
    return {
        "ticker": raw.get("ticker"),
        "name": raw.get("shortName") or raw.get("ticker"),
        "sector": raw.get("sector") or "Unknown",
        "industry": raw.get("industry"),
        "price": raw.get("currentPrice"),
        "prev_close": raw.get("previousClose"),
        "change_pct": raw.get("change_pct"),
        "market_cap": raw.get("marketCap"),
        "pe_ttm": raw.get("trailingPE"),
        "pe_fwd": raw.get("forwardPE"),
        "pb": raw.get("priceToBook"),
        "ev_ebitda": raw.get("enterpriseToEbitda"),
        "roe": _pct(raw.get("returnOnEquity")),
        "roa": _pct(raw.get("returnOnAssets")),
        "debt_to_equity": raw.get("debtToEquity"),
        "profit_margin": _pct(raw.get("profitMargins")),
        "revenue_growth": _pct(raw.get("revenueGrowth")),
        "earnings_growth": _pct(raw.get("earningsGrowth")),
        "dividend_yield": _pct(raw.get("dividendYield")),
        "beta": raw.get("beta"),
        "week52_high": raw.get("fiftyTwoWeekHigh"),
        "week52_low": raw.get("fiftyTwoWeekLow"),
        "volume": raw.get("volume"),
        "eps": raw.get("trailingEps"),
        "error": raw.get("error"),
    }


def _pct(x):
    """yfinance returns ratios like 0.146 for 14.6% — convert to a plain
    percentage number for display, leaving None untouched."""
    if x is None:
        return None
    return round(x * 100, 2)


def normalize_batch(raw_list: list[dict]) -> list[dict]:
    return [normalize(r) for r in raw_list]
