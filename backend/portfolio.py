"""
Portfolio analytics: current value, absolute/percent return, sector
allocation, and XIRR — computed from user-uploaded holdings plus live prices
from the stock cache.

XIRR is implemented with plain Newton-Raphson (no scipy dependency) since
it's a small, well-conditioned root-find for this use case.
"""
import csv
import io
import re
from datetime import datetime

from config import PORTFOLIO_MAX_ROWS

TICKER_RE = re.compile(r"^[A-Za-z0-9.^&=-]{1,20}$")
REQUIRED_COLS = {"ticker", "quantity", "buy_price", "buy_date"}


def parse_holdings_csv(file_bytes: bytes) -> list[dict]:
    """Expects columns: ticker, quantity, buy_price, buy_date (YYYY-MM-DD).

    Raises ValueError with a clear message on any validation failure.
    """
    if not file_bytes:
        raise ValueError("CSV file is empty")

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError(f"CSV must be UTF-8 encoded: {e}") from e

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing = REQUIRED_COLS - headers
    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing))}. "
            "Expected: ticker, quantity, buy_price, buy_date"
        )

    holdings = []
    for i, row in enumerate(reader, start=2):  # row 1 is header
        if i - 1 > PORTFOLIO_MAX_ROWS:
            raise ValueError(f"Too many rows (max {PORTFOLIO_MAX_ROWS})")

        # Normalize keys to lowercase
        normalized = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        if not any(normalized.values()):
            continue  # skip blank lines

        ticker = normalized.get("ticker", "").upper()
        if not ticker or not TICKER_RE.match(ticker):
            raise ValueError(
                f"Row {i}: invalid ticker '{normalized.get('ticker', '')}' "
                "(1–20 chars, letters/digits/./^/&/=/- only)"
            )

        try:
            quantity = float(normalized["quantity"])
            buy_price = float(normalized["buy_price"])
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"Row {i}: quantity and buy_price must be numbers"
            ) from e

        if quantity <= 0:
            raise ValueError(f"Row {i}: quantity must be positive")
        if buy_price <= 0:
            raise ValueError(f"Row {i}: buy_price must be positive")

        buy_date = normalized.get("buy_date", "")
        try:
            datetime.strptime(buy_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Row {i}: buy_date must be YYYY-MM-DD, got '{buy_date}'"
            ) from e

        holdings.append({
            "ticker": ticker,
            "quantity": quantity,
            "buy_price": buy_price,
            "buy_date": buy_date,
        })

    if not holdings:
        raise ValueError("CSV contains no valid holdings rows")
    if len(holdings) > PORTFOLIO_MAX_ROWS:
        raise ValueError(f"Too many rows (max {PORTFOLIO_MAX_ROWS})")

    return holdings


def _xnpv(rate: float, cashflows: list[tuple[datetime, float]]) -> float:
    t0 = cashflows[0][0]
    return sum(cf / (1 + rate) ** ((t - t0).days / 365.0) for t, cf in cashflows)


def xirr(cashflows: list[tuple[datetime, float]], guess: float = 0.15) -> float | None:
    """Newton-Raphson root-find for the rate that zeroes the XNPV.
    Returns None if it fails to converge (e.g. all cashflows same sign)."""
    rate = guess
    for _ in range(100):
        npv = _xnpv(rate, cashflows)
        d_rate = 1e-6
        npv_d = _xnpv(rate + d_rate, cashflows)
        derivative = (npv_d - npv) / d_rate
        if derivative == 0:
            return None
        new_rate = rate - npv / derivative
        if abs(new_rate - rate) < 1e-6:
            return round(new_rate * 100, 2)
        rate = new_rate
    return None


def summarize_portfolio(holdings: list[dict], live_prices: dict[str, dict]) -> dict:
    """
    holdings: [{ticker, quantity, buy_price, buy_date}]
    live_prices: {ticker: {price, sector, ...}} from the normalized stock cache
    """
    rows = []
    cashflows = []
    total_invested = 0.0
    total_current = 0.0
    sector_alloc: dict[str, float] = {}

    for h in holdings:
        info = live_prices.get(h["ticker"], {})
        cur_price = info.get("price")
        invested = h["quantity"] * h["buy_price"]
        current_value = h["quantity"] * cur_price if cur_price else None

        total_invested += invested
        if current_value is not None:
            total_current += current_value

        sector = info.get("sector", "Unknown")
        sector_alloc[sector] = sector_alloc.get(sector, 0) + (current_value or invested)

        cashflows.append((datetime.strptime(h["buy_date"], "%Y-%m-%d"), -invested))

        rows.append({
            **h,
            "current_price": cur_price,
            "invested_value": round(invested, 2),
            "current_value": round(current_value, 2) if current_value is not None else None,
            "return_pct": round((current_value - invested) / invested * 100, 2)
                if current_value is not None else None,
            "sector": sector,
        })

    if total_current > 0:
        cashflows.append((datetime.now(), total_current))

    irr = xirr(cashflows) if len(cashflows) >= 2 else None

    sector_alloc_pct = {
        s: round(v / total_current * 100, 2) if total_current else 0
        for s, v in sector_alloc.items()
    }

    return {
        "holdings": rows,
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current, 2),
        "total_return_pct": round((total_current - total_invested) / total_invested * 100, 2)
            if total_invested else None,
        "xirr_pct": irr,
        "sector_allocation": sector_alloc_pct,
    }
