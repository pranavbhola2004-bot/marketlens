// Screener tab: pulls filtered results live from /api/screener whenever a
// control changes, and supports client-side column sort.

let screenerSort = { key: "roe", dir: -1 };

async function loadSectorOptions() {
  const sectors = Object.keys(await Api.sectors());
  ["f-sector", "peer-sector"].forEach((id) => {
    const sel = document.getElementById(id);
    sectors.forEach((s) => {
      const o = document.createElement("option");
      o.value = s; o.textContent = s;
      sel.appendChild(o);
    });
  });
  if (sectors.length) document.getElementById("peer-sector").value = sectors[0];
  return sectors;
}

async function renderScreener() {
  const maxPE = +document.getElementById("f-pe").value;
  const minROE = +document.getElementById("f-roe").value;
  const maxDE = +document.getElementById("f-de").value;
  const minMargin = +document.getElementById("f-margin").value;
  const sector = document.getElementById("f-sector").value;

  document.getElementById("f-pe-val").textContent = "≤ " + maxPE + "x";
  document.getElementById("f-roe-val").textContent = "≥ " + minROE + "%";
  document.getElementById("f-de-val").textContent = "≤ " + maxDE + "%";
  document.getElementById("f-margin-val").textContent = "≥ " + minMargin + "%";

  const params = {
    max_pe: maxPE, min_roe: minROE, max_de: maxDE, min_margin: minMargin,
    sort_by: screenerSort.key, descending: screenerSort.dir === -1,
  };
  if (sector) params.sector = sector;

  const { count, stocks } = await Api.screener(params);
  document.getElementById("screener-count").textContent = `${count} stocks match`;
  const tbody = document.getElementById("screener-body");
  tbody.innerHTML = stocks.map((s) => {
    const chgClass = (s.change_pct || 0) >= 0 ? "up" : "down";
    return `
    <tr data-ticker="${escapeHtml(s.ticker)}">
      <td>${escapeHtml(s.ticker)}</td><td class="nm">${escapeHtml(s.name)}</td><td><span class="sector-pill">${escapeHtml(s.sector)}</span></td>
      <td class="num">₹${escapeHtml(fmt(s.price))}</td>
      <td class="num ${chgClass}">${escapeHtml(fmt(s.change_pct))}%</td>
      <td class="num">${escapeHtml(fmt(s.pe_ttm))}x</td><td class="num">${escapeHtml(fmt(s.pb))}x</td>
      <td class="num">${escapeHtml(fmt(s.roe))}%</td><td class="num">${escapeHtml(fmt(s.debt_to_equity))}%</td>
      <td class="num">${escapeHtml(fmt(s.profit_margin))}%</td>
    </tr>`;
  }).join("");
  bindTickerRowClicks(tbody);
}

function initScreenerControls() {
  ["f-pe", "f-roe", "f-de", "f-margin", "f-sector"].forEach((id) =>
    document.getElementById(id).addEventListener("input", renderScreener));
  document.querySelectorAll("#panel-screener thead th").forEach((th) => {
    th.addEventListener("click", () => {
      const k = th.dataset.k;
      if (!k) return;
      screenerSort.dir = screenerSort.key === k ? -screenerSort.dir : -1;
      screenerSort.key = k;
      renderScreener();
    });
  });
}
