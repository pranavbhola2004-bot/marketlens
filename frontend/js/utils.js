// Shared DOM helpers: HTML escaping and delegated ticker click handling.
// Load this before any panel that inserts dynamic strings into innerHTML.

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Bind a single delegated click listener on `container`.
 * - Elements with data-ticker open the stock modal (unless a data-action button)
 * - Elements with data-action="remove-watchlist" remove from watchlist
 */
function bindTickerRowClicks(container) {
  if (!container || container.dataset.delegatedBound === "1") return;
  container.dataset.delegatedBound = "1";
  container.addEventListener("click", (e) => {
    const actionEl = e.target.closest("[data-action]");
    if (actionEl) {
      e.stopPropagation();
      const action = actionEl.dataset.action;
      const ticker = actionEl.dataset.ticker;
      if (action === "remove-watchlist" && ticker && typeof removeFromWatchlist === "function") {
        removeFromWatchlist(ticker);
      }
      return;
    }
    const el = e.target.closest("[data-ticker]");
    if (el && el.dataset.ticker) {
      openStockModal(el.dataset.ticker);
    }
  });
}
