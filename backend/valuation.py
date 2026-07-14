"""
Relative-valuation heuristic: flags each stock Undervalued / Fair / Overvalued
based on its P/E and P/B premium vs its own sector average.

IMPORTANT — this is a screening heuristic, not a discounted cash flow model.
It's meant to shortlist names for deeper analysis, the same way a screener
column would, not to state a "fair price". For an actual intrinsic value
estimate (like the BEL DCF built earlier in this project), a proper
multi-year FCFF projection with its own assumptions is required — that
can't be reduced to a formula that works generically across 50+ companies
with different capital structures, growth phases, and reinvestment needs.
"""
from sectors import with_peer_comparison

UNDERVALUED_THRESHOLD = -0.15
OVERVALUED_THRESHOLD = 0.15


def compute_valuation(stocks: list[dict]) -> list[dict]:
    rows = with_peer_comparison(stocks)
    out = []
    for r in rows:
        pe_prem = r.get("pe_ttm_premium_vs_sector")
        pb_prem = r.get("pb_premium_vs_sector")
        parts = [p for p in (pe_prem, pb_prem) if p is not None]
        score = round(sum(parts) / len(parts), 4) if parts else None

        peg = None
        if r.get("pe_ttm") and r.get("earnings_growth") and r["earnings_growth"] > 0:
            peg = round(r["pe_ttm"] / r["earnings_growth"], 2)

        if score is None:
            flag = "Insufficient data"
        elif score < UNDERVALUED_THRESHOLD:
            flag = "Undervalued vs peers"
        elif score > OVERVALUED_THRESHOLD:
            flag = "Overvalued vs peers"
        else:
            flag = "Fairly valued vs peers"

        row = dict(r)
        row["valuation_score"] = score
        row["peg"] = peg
        row["valuation_flag"] = flag
        out.append(row)

    out.sort(key=lambda x: (x["valuation_score"] is None, x["valuation_score"]))
    return out
