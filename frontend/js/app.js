// App entry point: wires up tab switching and loads each panel's data
// once, then on-demand when its tab is opened.

const HEAT_COLORS = { pos: "#3DDC97", neg: "#FF5A5F", flat: "#5A6B5E" };

function initTabs() {
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    document.getElementById("panel-" + t.dataset.panel).classList.add("active");

    const panel = t.dataset.panel;
    if (panel === "peers") renderPeers();
    if (panel === "valuation") renderValuation();
    if (panel === "movers") renderMovers();
    if (panel === "indices") renderIndices();
    if (panel === "watchlist") renderWatchlist();
  }));
}

async function renderIndexStrip() {
  try {
    const { indices, breadth } = await Api.marketSummary();
    const strip = document.getElementById("index-strip");
    strip.innerHTML = Object.entries(indices).map(([label, v]) => {
      const chgClass = (v.change_pct || 0) >= 0 ? "up" : "down";
      const isVix = label === "INDIA VIX";
      const price = v.price !== null && v.price !== undefined ? v.price.toLocaleString() : "—";
      const chg = v.change_pct !== null && v.change_pct !== undefined ? v.change_pct + "%" : "";
      return `<div class="index-card${isVix ? " vix-card" : ""}">
        <div class="label">${escapeHtml(label)}</div>
        <div class="price">${escapeHtml(price)}</div>
        <div class="chg ${chgClass}">${escapeHtml(chg)}</div>
      </div>`;
    }).join("") + `<div class="index-card">
        <div class="label">Market Breadth</div>
        <div class="price"><span class="up">${breadth.advances}</span> / <span class="down">${breadth.declines}</span></div>
        <div class="chg">advances / declines</div>
      </div>`;
  } catch (e) {
    console.warn("Index strip failed:", e);
  }
}

async function renderMarquee() {
  const { stocks } = await Api.stocks();
  const items = stocks.map((s) => {
    const up = (s.change_pct || 0) >= 0;
    const price = s.price !== null && s.price !== undefined ? `₹${fmt(s.price)}` : "—";
    return `<span class="mq-item" data-ticker="${escapeHtml(s.ticker)}">${escapeHtml(s.ticker)}
      <span class="mq-price">${escapeHtml(price)}</span>
      <span class="${up ? "mq-up" : "mq-down"}">${up ? "▲" : "▼"} ${Math.abs(s.change_pct || 0)}%</span></span>`;
  }).join("");
  const track = document.getElementById("marquee");
  track.innerHTML = items + items; // duplicate for seamless loop
  bindTickerRowClicks(track);
}

async function renderMovers() {
  const [gainers, losers, heat] = await Promise.all([Api.topGainers(8), Api.topLosers(8), Api.heatmap()]);

  const gBody = document.getElementById("gainers-body");
  gBody.innerHTML = gainers.stocks.map((s) => `
    <tr data-ticker="${escapeHtml(s.ticker)}">
      <td>${escapeHtml(s.ticker)}</td><td class="nm">${escapeHtml(s.name)}</td>
      <td class="num">₹${escapeHtml(fmt(s.price))}</td>
      <td class="num up">▲ ${escapeHtml(fmt(s.change_pct))}%</td></tr>`).join("");
  bindTickerRowClicks(gBody);

  const lBody = document.getElementById("losers-body");
  lBody.innerHTML = losers.stocks.map((s) => `
    <tr data-ticker="${escapeHtml(s.ticker)}">
      <td>${escapeHtml(s.ticker)}</td><td class="nm">${escapeHtml(s.name)}</td>
      <td class="num">₹${escapeHtml(fmt(s.price))}</td>
      <td class="num down">▼ ${escapeHtml(fmt(Math.abs(s.change_pct || 0)))}%</td></tr>`).join("");
  bindTickerRowClicks(lBody);

  const maxAbs = Math.max(...Object.values(heat).map((h) => Math.abs(h.avg_change_pct)), 1);
  document.getElementById("heatmap-grid").innerHTML = Object.entries(heat).map(([sector, h]) => {
    const intensity = Math.min(Math.abs(h.avg_change_pct) / maxAbs, 1);
    const color = h.avg_change_pct > 0.05 ? HEAT_COLORS.pos : h.avg_change_pct < -0.05 ? HEAT_COLORS.neg : HEAT_COLORS.flat;
    return `<div class="heat-cell" style="background:${color}; opacity:${0.45 + intensity * 0.55}">
      <div class="sec">${escapeHtml(sector)}</div><div class="chg">${h.avg_change_pct > 0 ? "+" : ""}${escapeHtml(String(h.avg_change_pct))}%</div>
    </div>`;
  }).join("");
}

async function init() {
  initTabs();
  initScreenerControls();
  initPeerControls();
  initWatchlistControls();

  await loadSectorOptions();
  await Promise.all([renderIndexStrip(), renderMarquee(), renderScreener()]);
}

document.addEventListener("DOMContentLoaded", init);
