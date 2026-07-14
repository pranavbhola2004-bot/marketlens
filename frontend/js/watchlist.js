// Watchlist tab: add/remove tickers (persisted server-side via SQLite),
// cross-referenced against the live stock cache for current price/P-E.

async function renderWatchlist() {
  const [{ watchlist }, { stocks }] = await Promise.all([Api.watchlist(), Api.stocks()]);
  const stockMap = Object.fromEntries(stocks.map((s) => [s.ticker, s]));

  const body = document.getElementById("watchlist-body");
  const empty = document.getElementById("watchlist-empty");

  if (!watchlist.length) {
    body.innerHTML = "";
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";

  body.innerHTML = watchlist.map(({ ticker }) => {
    const s = stockMap[ticker];
    if (!s) {
      return `<tr>
        <td>${escapeHtml(ticker)}</td>
        <td class="nm" colspan="5">Not in current coverage universe — add it to config.DEFAULT_WATCHLIST</td>
        <td><button type="button" class="btn small" data-action="remove-watchlist" data-ticker="${escapeHtml(ticker)}">Remove</button></td>
      </tr>`;
    }
    const chgClass = s.change_pct >= 0 ? "up" : "down";
    return `<tr data-ticker="${escapeHtml(s.ticker)}">
      <td>${escapeHtml(s.ticker)}</td>
      <td class="nm">${escapeHtml(s.name)}</td><td><span class="sector-pill">${escapeHtml(s.sector)}</span></td>
      <td class="num">${escapeHtml(fmt(s.price))}</td>
      <td class="num ${chgClass}">${escapeHtml(fmt(s.change_pct))}%</td>
      <td class="num">${escapeHtml(fmt(s.pe_ttm))}x</td>
      <td><button type="button" class="btn small" data-action="remove-watchlist" data-ticker="${escapeHtml(s.ticker)}">Remove</button></td>
    </tr>`;
  }).join("");
  bindTickerRowClicks(body);
}

async function removeFromWatchlist(ticker) {
  await Api.removeWatchlist(ticker);
  renderWatchlist();
}

function initWatchlistControls() {
  document.getElementById("wl-add-btn").addEventListener("click", async () => {
    const input = document.getElementById("wl-input");
    const ticker = input.value.trim().toUpperCase();
    if (!ticker) return;
    await Api.addWatchlist(ticker);
    input.value = "";
    renderWatchlist();
  });
}
