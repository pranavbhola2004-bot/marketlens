// Thin fetch wrapper around the MarketLens FastAPI backend.
// When served BY the backend, relative paths work. When frontend is on
// Vercel separately, set window.MARKETLENS_API_BASE (via config.js) to the
// backend origin, e.g. "https://marketlens-api.up.railway.app".
var API_BASE = (typeof window !== "undefined" && window.MARKETLENS_API_BASE) || "";

var _fetchOpts = { credentials: "include" };

var Api = {
  async get(path) {
    const res = await fetch(API_BASE + path, _fetchOpts);
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(API_BASE + path, {
      ..._fetchOpts,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
    return res.json();
  },
  async del(path) {
    const res = await fetch(API_BASE + path, { ..._fetchOpts, method: "DELETE" });
    if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
    return res.json();
  },
  async upload(path, file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(API_BASE + path, { ..._fetchOpts, method: "POST", body: form });
    if (!res.ok) {
      let detail = `UPLOAD ${path} failed: ${res.status}`;
      try {
        const err = await res.json();
        if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      } catch (_) { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  },

  stocks: () => Api.get("/api/stocks"),
  stock: (ticker) => Api.get(`/api/stock/${encodeURIComponent(ticker)}`),
  history: (ticker, period = "3mo") => Api.get(`/api/stock/${encodeURIComponent(ticker)}/history?period=${period}`),
  screener: (params) => Api.get(`/api/screener?${new URLSearchParams(params)}`),
  sectors: () => Api.get("/api/sectors"),
  sector: (name) => Api.get(`/api/sector/${encodeURIComponent(name)}`),
  valuation: () => Api.get("/api/valuation"),
  marketSummary: () => Api.get("/api/market-summary"),
  indices: () => Api.get("/api/indices"),
  topGainers: (limit = 10) => Api.get(`/api/top-gainers?limit=${limit}`),
  topLosers: (limit = 10) => Api.get(`/api/top-losers?limit=${limit}`),
  heatmap: () => Api.get("/api/heatmap"),
  watchlist: () => Api.get("/api/watchlist"),
  addWatchlist: (ticker) => Api.post("/api/watchlist", { ticker }),
  removeWatchlist: (ticker) => Api.del(`/api/watchlist/${encodeURIComponent(ticker)}`),
};
