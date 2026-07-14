// Company detail modal: fetches /api/stock/{ticker} + price history and
// renders a small dashboard-within-a-dashboard. Any ticker row/label across
// the app can call openStockModal(ticker) to trigger this.

let priceChartInstance = null;

async function openStockModal(ticker) {
  const overlay = document.getElementById("modal-overlay");
  const body = document.getElementById("modal-body");
  body.innerHTML = `<p class="chart-sub">Loading ${escapeHtml(ticker)}…</p>`;
  overlay.classList.add("open");

  try {
    const [detail, hist] = await Promise.all([
      Api.stock(ticker),
      Api.history(ticker, "3mo"),
    ]);
    renderModal(detail, hist.history);
  } catch (e) {
    body.innerHTML = `<p class="chart-sub">Couldn't load ${escapeHtml(ticker)}: ${escapeHtml(e.message)}</p>`;
  }
}

function renderModal(s, history) {
  const body = document.getElementById("modal-body");
  const flagClass = s.valuation_flag?.startsWith("Under") ? "under"
    : s.valuation_flag?.startsWith("Over") ? "over" : "fair";
  const chg = s.change_pct;
  const chgClass = chg >= 0 ? "up" : "down";

  body.innerHTML = `
    <h2>${escapeHtml(s.name || s.ticker)}</h2>
    <p class="sub">${escapeHtml(s.ticker)} · <span class="sector-pill">${escapeHtml(s.sector)}</span>
      ${s.valuation_flag ? `<span class="flag ${flagClass}">${escapeHtml(s.valuation_flag)}</span>` : ""}</p>
    <div class="modal-metrics">
      ${metric("Price", escapeHtml(fmt(s.price)))}
      ${metric("Change", `<span class="${chgClass}">${escapeHtml(fmt(chg))}%</span>`)}
      ${metric("Market Cap", escapeHtml(fmtCr(s.market_cap)))}
      ${metric("P/E (TTM)", escapeHtml(fmt(s.pe_ttm)) + "x")}
      ${metric("P/B", escapeHtml(fmt(s.pb)) + "x")}
      ${metric("EV/EBITDA", escapeHtml(fmt(s.ev_ebitda)) + "x")}
      ${metric("ROE", escapeHtml(fmt(s.roe)) + "%")}
      ${metric("Debt/Equity", escapeHtml(fmt(s.debt_to_equity)) + "%")}
      ${metric("Net Margin", escapeHtml(fmt(s.profit_margin)) + "%")}
      ${metric("Dividend Yield", escapeHtml(fmt(s.dividend_yield)) + "%")}
      ${metric("Beta", escapeHtml(fmt(s.beta)))}
      ${metric("52W Range", `${escapeHtml(fmt(s.week52_low))} – ${escapeHtml(fmt(s.week52_high))}`)}
    </div>
    <canvas id="price-chart" height="120"></canvas>
  `;

  if (priceChartInstance) priceChartInstance.destroy();
  const ctx = document.getElementById("price-chart");
  if (ctx && history && history.length) {
    priceChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: history.map(h => h.date),
        datasets: [{
          label: "Close",
          data: history.map(h => h.close),
          borderColor: "#E8A017",
          backgroundColor: "rgba(232,160,23,0.08)",
          fill: true,
          tension: 0.15,
          pointRadius: 0,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: {
            ticks: { maxTicksLimit: 6, color: "#8A9A8E" },
            grid: { color: "rgba(138,154,142,0.12)" },
          },
          y: {
            ticks: { color: "#8A9A8E" },
            grid: { color: "rgba(138,154,142,0.12)" },
          },
        },
      },
    });
  }
}

function metric(label, value) {
  return `<div class="m"><div class="l">${escapeHtml(label)}</div><div class="v">${value}</div></div>`;
}
function fmt(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return typeof v === "number" ? (Math.round(v * 100) / 100).toLocaleString() : v;
}
function fmtCr(v) {
  if (!v) return "—";
  return "₹" + (v / 1e7).toLocaleString(undefined, { maximumFractionDigits: 0 }) + " Cr";
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("modal-close").addEventListener("click", () => {
    document.getElementById("modal-overlay").classList.remove("open");
  });
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "modal-overlay") e.target.classList.remove("open");
  });
});
