// Peer comparison tab: bar chart of one metric across all stocks in a
// chosen sector, with the sector average marked.

async function renderPeers() {
  const sector = document.getElementById("peer-sector").value;
  const metric = document.getElementById("peer-metric").value;
  if (!sector) return;

  const { averages, stocks } = await Api.sector(sector);
  const avg = averages ? averages[metric] : null;
  const vals = stocks.map((s) => s[metric]).filter((v) => typeof v === "number");
  const maxVal = Math.max(...vals, avg || 0) * 1.15 || 1;

  document.getElementById("peer-title").textContent = `${sector} — ${metric.toUpperCase()} vs sector average`;
  const chart = document.getElementById("peer-chart");
  chart.innerHTML = stocks.map((s) => {
    const v = s[metric];
    if (typeof v !== "number") return "";
    const pct = (v / maxVal * 100).toFixed(1);
    const avgPct = avg ? (avg / maxVal * 100).toFixed(1) : 0;
    return `<div class="bar-row">
      <div class="bar-label" data-ticker="${escapeHtml(s.ticker)}">${escapeHtml(s.ticker)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div>
        <div class="bar-avg-line" style="left:${avgPct}%"></div></div>
      <div class="bar-val">${v.toFixed(1)}x</div>
    </div>`;
  }).join("");
  bindTickerRowClicks(chart);
}

function initPeerControls() {
  document.getElementById("peer-sector").addEventListener("change", renderPeers);
  document.getElementById("peer-metric").addEventListener("change", renderPeers);
}
