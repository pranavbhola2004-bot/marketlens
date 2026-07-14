import re
from pydantic import BaseModel, field_validator

TICKER_PATTERN = re.compile(r"^[A-Za-z0-9.^&=-]{1,20}$")


class WatchlistAdd(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not TICKER_PATTERN.match(v):
            raise ValueError(
                "ticker must be 1–20 chars: letters, digits, and .^&=- only"
            )
        return v


class ScreenerParams(BaseModel):
    max_pe: float | None = None
    min_roe: float | None = None
    max_de: float | None = None
    min_margin: float | None = None
    min_market_cap: float | None = None
    min_dividend_yield: float | None = None
    sector: str | None = None
    sort_by: str = "roe"
    descending: bool = True
