// Valuation tab: every covered stock, ranked by premium/discount vs its
// sector peers, with a visual "spectrum" ribbon per row.

async function renderValuation() {
  const { stocks } = await Api.valuation();
  const scores = stocks.map((s) => s.valuation_score).filter((v) => v !== null);
  const minS = Math.min(...scores), maxS = Math.max(...scores);

  document.getElementById("valuation-count").textContent =
    `${stocks.length} stocks ranked by premium/discount vs sector peers`;

  const tbody = document.getElementById("valuation-body");
  tbody.innerHTML = stocks.map((s) => {
    const flagClass = s.valuation_flag.startsWith("Under") ? "under"
      : s.valuation_flag.startsWith("Over") ? "over" : "fair";
    let markPos = 73; // center default when score is null
    if (s.valuation_score !== null && maxS > minS) {
      markPos = ((s.valuation_score - minS) / (maxS - minS) * 146);
    }
    return `<tr data-ticker="${escapeHtml(s.ticker)}">
      <td>${escapeHtml(s.ticker)}</td><td class="nm">${escapeHtml(s.name)}</td><td><span class="sector-pill">${escapeHtml(s.sector)}</span></td>
      <td class="num">₹${escapeHtml(fmt(s.price))}</td>
      <td class="num">${escapeHtml(fmt(s.pe_ttm))}x</td><td class="num">${escapeHtml(fmt(s.pb))}x</td>
      <td><div class="ribbon-track"><div class="ribbon-mark" style="left:${markPos.toFixed(0)}px"></div></div></td>
      <td><span class="flag ${flagClass}">${escapeHtml(s.valuation_flag)}</span></td>
    </tr>`;
  }).join("");
  bindTickerRowClicks(tbody);
}
