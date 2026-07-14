// Indices tab: card grid of all tracked indices with distinct VIX treatment.

function vixBand(level) {
  if (level === null || level === undefined) return { cls: "vix-unk", label: "—" };
  if (level < 15) return { cls: "vix-calm", label: "Calm" };
  if (level < 25) return { cls: "vix-elevated", label: "Elevated" };
  return { cls: "vix-high", label: "High volatility" };
}

async function renderIndices() {
  const grid = document.getElementById("indices-grid");
  if (!grid) return;

  try {
    const { indices } = await Api.indices();
    grid.innerHTML = indices.map((idx) => {
      const chg = idx.change_pct;
      const chgClass = (chg || 0) >= 0 ? "up" : "down";
      const chgStr = chg !== null && chg !== undefined
        ? `${chg > 0 ? "+" : ""}${chg}%`
        : "—";
      const priceStr = idx.price !== null && idx.price !== undefined
        ? Number(idx.price).toLocaleString(undefined, { maximumFractionDigits: 2 })
        : "—";

      if (idx.is_vix) {
        const band = vixBand(idx.price);
        return `<div class="index-tile vix-tile ${band.cls}">
          <div class="tile-label">${escapeHtml(idx.label)}</div>
          <div class="tile-price">${escapeHtml(priceStr)}</div>
          <div class="tile-chg ${chgClass}">${escapeHtml(chgStr)}</div>
          <div class="vix-band">${escapeHtml(band.label)}</div>
          <div class="tile-hint">Volatility gauge — not a price index</div>
        </div>`;
      }

      return `<div class="index-tile">
        <div class="tile-label">${escapeHtml(idx.label)}</div>
        <div class="tile-price">${escapeHtml(priceStr)}</div>
        <div class="tile-chg ${chgClass}">${escapeHtml(chgStr)}</div>
        <div class="tile-sym">${escapeHtml(idx.symbol)}</div>
      </div>`;
    }).join("");
  } catch (e) {
    grid.innerHTML = `<p class="empty-note">Could not load indices: ${escapeHtml(e.message)}</p>`;
  }
}
