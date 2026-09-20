(async function () {
  const session = await requireAuth(["admin", "staff"]);
  if (!session) return;

  document.getElementById("todayLabel").textContent =
    "Today's overview · " + new Date().toLocaleDateString(undefined, {
      weekday: "long", year: "numeric", month: "long", day: "numeric",
    });

  try {
    const [summary, trend, top, lowStock] = await Promise.all([
      api.get("/reports/dashboard"),
      api.get("/reports/sales-trend?days=14"),
      api.get("/reports/top-products?limit=6"),
      api.get("/products/low-stock"),
    ]);

    document.getElementById("statToday").textContent =
      `${money(summary.today_sales_total)}`;
    document.getElementById("statMonth").textContent = money(summary.month_sales_total);
    document.getElementById("statLowStock").textContent = summary.low_stock_count;
    document.getElementById("statCredit").textContent = money(summary.outstanding_credit);

    renderSalesTrend(trend);
    renderTopProducts(top);
    renderLowStock(lowStock);
  } catch (err) {
    friendlyError(err);
  }
})();

function renderSalesTrend(points) {
  const ctx = document.getElementById("salesTrendChart");
  new Chart(ctx, {
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
      scales: {
        y: { beginAtZero: true, ticks: { callback: (v) => "Rs. " + v } },
      },
    },
  });
}

function renderTopProducts(rows) {
  const ctx = document.getElementById("topProductsChart");
  if (!rows.length) {
    ctx.parentElement.innerHTML = '<div class="empty-state"><i class="bi bi-bar-chart"></i>No sales recorded yet.</div>';
    return;
  }
  new Chart(ctx, {
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

function renderLowStock(products) {
  const body = document.getElementById("lowStockBody");
  const empty = document.getElementById("lowStockEmpty");
  body.innerHTML = "";
  if (!products.length) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  for (const p of products) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono">${p.sku}</td>
      <td>${p.name}</td>
      <td>${p.category_name ?? "—"}</td>
      <td class="text-right num">${p.stock_quantity}</td>
      <td class="text-right num text-muted">${p.reorder_level}</td>
    `;
    body.appendChild(tr);
  }
}
