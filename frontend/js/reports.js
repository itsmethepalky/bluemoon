const CATEGORY_COLORS = ["#16324f", "#c9722e", "#5b8a72", "#a24942", "#7d6ba6", "#3d7a8a"];

(async function init() {
  const session = await requireAuth(["admin", "staff"]);
  if (!session) return;

  document.getElementById("trendDays").addEventListener("change", loadAll);
  await loadAll();
})();

async function loadAll() {
  const days = document.getElementById("trendDays").value;
  try {
    const [trend, top, inventory, profit] = await Promise.all([
      api.get(`/reports/sales-trend?days=${days}`),
      api.get("/reports/top-products?limit=8"),
      api.get("/reports/inventory-status"),
      api.get(`/reports/profit?start=${daysAgoIso(Number(days))}`),
    ]);
    renderSalesTrend(trend);
    renderTopProducts(top);
    renderInventory(inventory);
    renderProfit(profit);
  } catch (err) {
    friendlyError(err);
  }
}

function daysAgoIso(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

let _trendChart, _topChart, _invChart;

function renderSalesTrend(points) {
  const ctx = document.getElementById("salesTrendChart");
  _trendChart?.destroy();
  _trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: points.map((p) => p.label),
      datasets: [{
        label: "Sales",
        data: points.map((p) => p.total),
        borderColor: "#c9722e",
        backgroundColor: "rgba(201, 114, 46, 0.12)",
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 0,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { callback: (v) => "Rs. " + v } } },
    },
  });
}

function renderTopProducts(rows) {
  const ctx = document.getElementById("topProductsChart");
  _topChart?.destroy();
  if (!rows.length) {
    ctx.parentElement.innerHTML = '<div class="empty-state"><i class="bi bi-bar-chart"></i>No sales recorded yet.</div>';
    return;
  }
  _topChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: rows.map((r) => r.product_name),
      datasets: [{
        label: "Units sold",
        data: rows.map((r) => r.quantity_sold),
        backgroundColor: "#16324f",
        borderRadius: 4,
        maxBarThickness: 28,
      }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true } },
    },
  });
}

function renderInventory(rows) {
  const ctx = document.getElementById("inventoryChart");
  _invChart?.destroy();
  const body = document.getElementById("inventoryBody");
  body.innerHTML = "";

  if (!rows.length) {
    ctx.parentElement.innerHTML = '<div class="empty-state"><i class="bi bi-box-seam"></i>No active products yet.</div>';
    return;
  }

  _invChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: rows.map((r) => r.category),
      datasets: [{
        data: rows.map((r) => r.stock_value),
        backgroundColor: rows.map((_, i) => CATEGORY_COLORS[i % CATEGORY_COLORS.length]),
        borderWidth: 0,
      }],
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });

  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(r.category)}</td>
      <td class="text-right num">${r.quantity}</td>
      <td class="text-right num">${money(r.stock_value)}</td>
    `;
    body.appendChild(tr);
  }
}

function renderProfit(p) {
  document.getElementById("profitRevenue").textContent = money(p.revenue);
  document.getElementById("profitCost").textContent = money(p.estimated_cost);
  document.getElementById("profitMargin").textContent = money(p.estimated_profit);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
