"""
Sector-level aggregation: averages per sector, and per-stock premium/discount
vs its own sector average — the basis for both peer comparison and valuation.
"""

METRICS = ["pe_ttm", "pb", "ev_ebitda", "roe", "profit_margin"]


def sector_averages(stocks: list[dict]) -> dict:
    """Returns {sector: {metric: avg}} — None values are excluded from the
    average rather than treated as zero."""
    by_sector: dict[str, list[dict]] = {}
    for s in stocks:
        by_sector.setdefault(s["sector"], []).append(s)

    out = {}
    for sector, rows in by_sector.items():
        avgs = {}
        for m in METRICS:
            vals = [r[m] for r in rows if isinstance(r.get(m), (int, float))]
            avgs[m] = round(sum(vals) / len(vals), 2) if vals else None
        avgs["count"] = len(rows)
        out[sector] = avgs
    return out


def with_peer_comparison(stocks: list[dict]) -> list[dict]:
    """Attaches each stock's sector average and % premium/discount vs that
    average, for every metric in METRICS."""
    avgs = sector_averages(stocks)
    out = []
    for s in stocks:
        row = dict(s)
        sector_avg = avgs.get(s["sector"], {})
        for m in METRICS:
            avg = sector_avg.get(m)
            val = s.get(m)
            row[f"{m}_sector_avg"] = avg
            if isinstance(val, (int, float)) and isinstance(avg, (int, float)) and avg != 0:
                row[f"{m}_premium_vs_sector"] = round((val - avg) / avg, 4)
            else:
                row[f"{m}_premium_vs_sector"] = None
        out.append(row)
    return out


def stocks_in_sector(stocks: list[dict], sector: str) -> list[dict]:
    return [s for s in stocks if s["sector"] == sector]
