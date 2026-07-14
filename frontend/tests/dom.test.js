/**
 * Headless DOM tests for every frontend panel.
 * Run from frontend/:  npm install && npm test
 */
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");

const FRONTEND = path.join(__dirname, "..");

const MOCK = {
  stocks: {
    stocks: [
      { ticker: "RELIANCE.NS", name: "Reliance", sector: "Energy", price: 2800, change_pct: 1.8, pe_ttm: 25, pb: 2.5, roe: 15, debt_to_equity: 40, profit_margin: 10, market_cap: 1e12, valuation_flag: "Fair Value", valuation_score: 0 },
      { ticker: "TCS.NS", name: "TCS", sector: "Technology", price: 3800, change_pct: -2.5, pe_ttm: 28, pb: 10, roe: 40, debt_to_equity: 10, profit_margin: 22, market_cap: 1e12, valuation_flag: "Overvalued", valuation_score: 1.2 },
      { ticker: "INFY.NS", name: 'INFY<img src=x onerror=alert(1)>', sector: "Technology", price: 1500, change_pct: 1.3, pe_ttm: 24, pb: 7, roe: 30, debt_to_equity: 5, profit_margin: 18, market_cap: 1e12, valuation_flag: "Undervalued", valuation_score: -0.8 },
    ],
  },
  sectors: { Energy: { pe_ttm: 25 }, Technology: { pe_ttm: 26, pb: 8.5, ev_ebitda: 16 } },
  sector: {
    sector: "Technology",
    averages: { pe_ttm: 26, pb: 8.5, ev_ebitda: 16 },
    stocks: [
      { ticker: "TCS.NS", name: "TCS", sector: "Technology", pe_ttm: 28, pb: 10, ev_ebitda: 18 },
      { ticker: "INFY.NS", name: "Infosys", sector: "Technology", pe_ttm: 24, pb: 7, ev_ebitda: 15 },
    ],
  },
  valuation: {
    stocks: [
      { ticker: "INFY.NS", name: "Infosys", sector: "Technology", pe_ttm: 24, pb: 7, valuation_flag: "Undervalued", valuation_score: -0.8 },
      { ticker: "TCS.NS", name: "TCS", sector: "Technology", pe_ttm: 28, pb: 10, valuation_flag: "Overvalued", valuation_score: 1.2 },
      { ticker: "RELIANCE.NS", name: "Reliance", sector: "Energy", pe_ttm: 25, pb: 2.5, valuation_flag: "Fair Value", valuation_score: 0 },
    ],
  },
  marketSummary: {
    indices: {
      "NIFTY 50": { price: 22000, change_pct: 0.5 },
      "SENSEX": { price: 72000, change_pct: 0.4 },
      "BANK NIFTY": { price: 48000, change_pct: -0.2 },
      "INDIA VIX": { price: 14.2, change_pct: -1.1 },
    },
    breadth: { advances: 2, declines: 1, unchanged: 0 },
  },
  indices: {
    indices: [
      { label: "NIFTY 50", symbol: "^NSEI", price: 22000, change_pct: 0.5, is_vix: false },
      { label: "NIFTY IT", symbol: "^CNXIT", price: 35000, change_pct: 1.2, is_vix: false },
      { label: "INDIA VIX", symbol: "^INDIAVIX", price: 14.2, change_pct: -1.1, is_vix: true },
    ],
  },
  gainers: { stocks: [{ ticker: "RELIANCE.NS", name: "Reliance", change_pct: 1.8 }] },
  losers: { stocks: [{ ticker: "TCS.NS", name: "TCS", change_pct: -2.5 }] },
  heatmap: { Energy: { avg_change_pct: 1.8, count: 1 }, Technology: { avg_change_pct: -0.6, count: 2 } },
  watchlist: { watchlist: [] },
  portfolio: {
    holdings: [
      { ticker: "RELIANCE.NS", quantity: 10, buy_price: 2400, current_price: 2800, invested_value: 24000, current_value: 28000, return_pct: 16.67 },
    ],
    total_invested: 24000,
    total_current_value: 28000,
    total_return_pct: 16.67,
    xirr_pct: 45.2,
    sector_allocation: { Energy: 100 },
  },
  history: { ticker: "TCS.NS", period: "3mo", history: [{ date: "2024-01-01", close: 100 }, { date: "2024-01-02", close: 105 }] },
  stockDetail: {
    ticker: "TCS.NS", name: "TCS", sector: "Technology", price: 3800, change_pct: -2.5,
    pe_ttm: 28, pb: 10, ev_ebitda: 18, roe: 40, debt_to_equity: 10, profit_margin: 22,
    dividend_yield: 1.5, beta: 0.8, week52_high: 4200, week52_low: 3200, market_cap: 1e12,
    valuation_flag: "Overvalued",
  },
};

function loadScripts(dom) {
  const files = [
    "js/utils.js", "js/api.js", "js/charts.js", "js/screener.js", "js/peers.js",
    "js/valuation.js", "js/indices.js", "js/watchlist.js", "js/app.js",
  ];
  const { window } = dom;
  // Stub Chart.js
  window.Chart = function Chart() { this.destroy = () => {}; };
  window.alert = () => {};

  // Mock fetch / Api
  const responses = {
    "/api/stocks": MOCK.stocks,
    "/api/sectors": MOCK.sectors,
    "/api/sector/Technology": MOCK.sector,
    "/api/screener": { count: MOCK.stocks.stocks.length, stocks: MOCK.stocks.stocks },
    "/api/valuation": MOCK.valuation,
    "/api/market-summary": MOCK.marketSummary,
    "/api/indices": MOCK.indices,
    "/api/top-gainers": MOCK.gainers,
    "/api/top-losers": MOCK.losers,
    "/api/heatmap": MOCK.heatmap,
    "/api/watchlist": MOCK.watchlist,
    "/api/portfolio/summary": MOCK.portfolio,
    "/api/stock/TCS.NS": MOCK.stockDetail,
    "/api/stock/TCS.NS/history": MOCK.history,
  };

  window.fetch = async (url, opts = {}) => {
    const path = url.replace(/^https?:\/\/[^/]+/, "").split("?")[0];
    let body = responses[path];
    if (path.startsWith("/api/screener")) body = responses["/api/screener"];
    if (path.startsWith("/api/stock/") && path.endsWith("/history")) body = MOCK.history;
    else if (path.startsWith("/api/stock/")) body = MOCK.stockDetail;
    if (path === "/api/sector/Technology" || path.startsWith("/api/sector/")) body = MOCK.sector;
    if (!body && opts.method === "POST" && path === "/api/watchlist") {
      body = { added: "TCS.NS" };
    }
    if (!body && opts.method === "DELETE") body = { removed: "TCS.NS" };
    if (!body) body = {};
    return {
      ok: true,
      status: 200,
      json: async () => body,
    };
  };

  for (const f of files) {
    const code = fs.readFileSync(path.join(FRONTEND, f), "utf8");
    window.eval(code);
  }
  // Ensure Api is on window for cross-script access under jsdom eval
  if (typeof window.Api === "undefined" && typeof Api !== "undefined") {
    window.Api = Api;
  }
  return window;
}

function setupDom() {
  const html = fs.readFileSync(path.join(FRONTEND, "index.html"), "utf8");
  // Strip script tags — we load them manually
  const cleaned = html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<link[^>]*>/gi, "");
  const dom = new JSDOM(cleaned, { url: "http://localhost/", runScripts: "outside-only", pretendToBeVisual: true });
  return loadScripts(dom);
}

async function run() {
  const fails = [];
  const pass = (name) => console.log(`  PASS  ${name}`);
  const fail = (name, err) => {
    console.log(`  FAIL  ${name}: ${err}`);
    fails.push(name);
  };

  console.log("\nFrontend panel tests (jsdom)\n");

  // --- escapeHtml / XSS ---
  {
    const w = setupDom();
    try {
      const escaped = w.escapeHtml(`<img src=x onerror=alert(1)>`);
      if (escaped.includes("<img") || escaped.includes("<script")) throw new Error("raw tag leaked: " + escaped);
      if (!escaped.includes("&lt;img") || !escaped.includes("&gt;")) throw new Error("expected entities: " + escaped);
      pass("escapeHtml sanitizes tags");
    } catch (e) { fail("escapeHtml sanitizes tags", e.message); }
  }

  // --- Screener ---
  {
    const w = setupDom();
    try {
      await w.loadSectorOptions();
      await w.renderScreener();
      const body = w.document.getElementById("screener-body").innerHTML;
      if (!body.includes("RELIANCE.NS")) throw new Error("missing ticker");
      if (body.includes("<img src=x") || body.includes("<img src=")) throw new Error("XSS in screener");
      if (!body.includes("&lt;img") && body.includes("INFY")) {
        // INFY mock name has XSS payload — must be entity-escaped
        const infyRow = body.includes("INFY");
        if (infyRow && /INFY<img/.test(body)) throw new Error("unescaped XSS payload");
      }
      if (!body.includes("data-ticker=")) throw new Error("missing data-ticker");
      if (body.includes("onclick=")) throw new Error("inline onclick still present");
      pass("Screener renders escaped + data-ticker");
    } catch (e) { fail("Screener renders escaped + data-ticker", e.message); }
  }

  // --- Peers ---
  {
    const w = setupDom();
    try {
      await w.loadSectorOptions();
      w.document.getElementById("peer-sector").value = "Technology";
      await w.renderPeers();
      const chart = w.document.getElementById("peer-chart").innerHTML;
      if (!chart.includes("bar-fill")) throw new Error("no bars");
      if (!chart.includes("bar-avg-line")) throw new Error("no avg marker");
      if (chart.includes("onclick=")) throw new Error("inline onclick");
      pass("Peers bar chart + sector avg marker");
    } catch (e) { fail("Peers bar chart + sector avg marker", e.message); }
  }

  // --- Valuation ---
  {
    const w = setupDom();
    try {
      await w.renderValuation();
      const body = w.document.getElementById("valuation-body").innerHTML;
      if (!body.includes("ribbon-mark")) throw new Error("no ribbon");
      if (!body.includes("Undervalued") && !body.includes("flag")) throw new Error("no flags");
      if (body.includes("onclick=")) throw new Error("inline onclick");
      pass("Valuation flags + spectrum ribbon");
    } catch (e) { fail("Valuation flags + spectrum ribbon", e.message); }
  }

  // --- Movers ---
  {
    const w = setupDom();
    try {
      await w.renderMovers();
      if (!w.document.getElementById("gainers-body").innerHTML.includes("RELIANCE")) throw new Error("no gainers");
      if (!w.document.getElementById("losers-body").innerHTML.includes("TCS")) throw new Error("no losers");
      if (!w.document.getElementById("heatmap-grid").innerHTML.includes("heat-cell")) throw new Error("no heatmap");
      pass("Movers & heatmap");
    } catch (e) { fail("Movers & heatmap", e.message); }
  }

  // --- Indices ---
  {
    const w = setupDom();
    try {
      await w.renderIndices();
      const grid = w.document.getElementById("indices-grid").innerHTML;
      if (!grid.includes("NIFTY 50")) throw new Error("missing nifty");
      if (!grid.includes("vix-tile")) throw new Error("VIX not distinctly styled");
      if (!grid.includes("vix-calm") && !grid.includes("vix-elevated") && !grid.includes("vix-high")) {
        throw new Error("missing VIX band class");
      }
      pass("Indices tab + distinct VIX");
    } catch (e) { fail("Indices tab + distinct VIX", e.message); }
  }

  // --- Watchlist empty ---
  {
    const w = setupDom();
    try {
      await w.renderWatchlist();
      const empty = w.document.getElementById("watchlist-empty");
      if (empty.style.display === "none") throw new Error("empty state hidden");
      pass("Watchlist empty state");
    } catch (e) { fail("Watchlist empty state", e.message); }
  }

  // --- Watchlist with XSS ticker in CSV-style payload ---
  {
    const w = setupDom();
    try {
      MOCK.watchlist.watchlist = [{ ticker: "EVIL'.NS", added_at: "now" }];
      // Re-setup so fetch returns evil ticker - patch responses via stocks empty match
      await w.renderWatchlist();
      const body = w.document.getElementById("watchlist-body").innerHTML;
      if (body.includes("onclick=")) throw new Error("inline onclick in watchlist");
      if (body.includes("data-action=\"remove-watchlist\"")) {
        // good — delegated remove
      } else if (body.includes("Remove")) {
        // still OK if button present
      }
      // Attribute must be escaped quotes
      if (body.includes("onclick=\"removeFromWatchlist('EVIL")) throw new Error("injection via onclick");
      pass("Watchlist no inline onclick (CSV-style tickers)");
      MOCK.watchlist.watchlist = [];
    } catch (e) {
      MOCK.watchlist.watchlist = [];
      fail("Watchlist no inline onclick (CSV-style tickers)", e.message);
    }
  }

  // --- Portfolio removed from UI ---
  {
    const w = setupDom();
    try {
      if (w.document.getElementById("panel-portfolio")) throw new Error("portfolio panel still present");
      const tabs = [...w.document.querySelectorAll(".tab")].map((t) => t.dataset.panel);
      if (tabs.includes("portfolio")) throw new Error("portfolio tab still present");
      pass("Portfolio feature removed");
    } catch (e) { fail("Portfolio feature removed", e.message); }
  }

  // --- Index strip ---
  {
    const w = setupDom();
    try {
      await w.renderIndexStrip();
      const strip = w.document.getElementById("index-strip").innerHTML;
      if (!strip.includes("NIFTY 50")) throw new Error("no nifty");
      if (!strip.includes("vix-card")) throw new Error("VIX header card missing class");
      pass("Index strip header");
    } catch (e) { fail("Index strip header", e.message); }
  }

  // --- Modal opens ---
  {
    const w = setupDom();
    try {
      await w.openStockModal("TCS.NS");
      const modal = w.document.getElementById("modal-body").innerHTML;
      if (!modal.includes("TCS")) throw new Error("modal empty");
      if (!w.document.getElementById("modal-overlay").classList.contains("open")) throw new Error("overlay not open");
      pass("Company detail modal");
    } catch (e) { fail("Company detail modal", e.message); }
  }

  // --- Tabs exist including Indices ---
  {
    const w = setupDom();
    try {
      const tabs = [...w.document.querySelectorAll(".tab")].map((t) => t.dataset.panel);
      if (!tabs.includes("indices")) throw new Error("no indices tab");
      if (!w.document.getElementById("panel-indices")) throw new Error("no panel-indices");
      pass("Indices tab present in DOM");
    } catch (e) { fail("Indices tab present in DOM", e.message); }
  }

  console.log("");
  if (fails.length) {
    console.error(`${fails.length} failed`);
    process.exit(1);
  }
  console.log("All frontend tests passed.\n");
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
