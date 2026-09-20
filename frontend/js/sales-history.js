let allSales = [];
let activeSale = null;

(async function init() {
  const session = await requireAuth(["admin", "staff"]);
  if (!session) return;

  document.getElementById("filterBtn").addEventListener("click", loadSales);

  document.getElementById("clearFilterBtn").addEventListener("click", () => {
    document.getElementById("startDate").value = "";
    document.getElementById("endDate").value = "";
    document.getElementById("customerFilter").value = "";
    loadSales();
  });

  document
    .getElementById("returnForm")
    .addEventListener("submit", submitReturn);

  await loadCustomerFilter();
  await loadSales();
})();

async function loadCustomerFilter() {
  try {
    const customers = await api.get("/customers");
    const sel = document.getElementById("customerFilter");

    sel.innerHTML =
      '<option value="">All customers</option>' +
      customers
        .map(
          (c) =>
            `<option value="${c.id}">${escapeHtml(c.name)}</option>`
        )
        .join("");
  } catch (err) {
    friendlyError(err);
  }
}

async function loadSales() {
  const params = new URLSearchParams();

  const start = document.getElementById("startDate").value;
  const end = document.getElementById("endDate").value;
  const customerId = document.getElementById("customerFilter").value;

  if (start) params.set("start", start);
  if (end) params.set("end", end);
  if (customerId) params.set("customer_id", customerId);

  try {
    allSales = await api.get(
      `/sales${params.toString() ? "?" + params.toString() : ""}`
    );

    renderTable();
  } catch (err) {
    friendlyError(err);
  }
}

const STATUS_BADGE = {
  paid: "badge-green",
  partial: "badge-amber",
  unpaid: "badge-brick",
};

const SALE_STATUS_BADGE = {
  completed: "badge-green",
  returned: "badge-brick",
  partially_returned: "badge-amber",
};

function renderTable() {
  const body = document.getElementById("salesBody");
  const empty = document.getElementById("salesEmpty");

  body.innerHTML = "";

  if (!allSales.length) {
    empty.classList.remove("hidden");
    return;
  }

  empty.classList.add("hidden");

  for (const s of allSales) {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td class="mono" data-label="Invoice">
        ${escapeHtml(s.invoice_no)}
      </td>

      <td data-label="Date">
        ${formatDateTime(s.sale_date)}
      </td>

      <td data-label="Customer">
        ${escapeHtml(s.customer_name || "Walk-in")}
      </td>

      <td data-label="Cashier">
        ${escapeHtml(s.cashier_name || "—")}
      </td>

      <td class="text-right num" data-label="Total">
        ${money(s.total_amount)}
      </td>

      <td data-label="Payment">
        <span class="badge ${
          STATUS_BADGE[s.payment_status] || "badge-slate"
        }">
          ${escapeHtml(s.payment_status)}
        </span>
      </td>

      <td data-label="Status">
        <span class="badge ${
          SALE_STATUS_BADGE[s.status] || "badge-slate"
        }">
          ${escapeHtml(String(s.status).replace("_", " "))}
        </span>
      </td>

      <td class="text-right sales-action-cell" data-label="Action">
        <button
          class="btn btn-outline btn-sm"
          data-id="${s.id}"
          type="button"
        >
          <i class="bi bi-eye"></i>
          <span>View</span>
        </button>
      </td>
    `;

    body.appendChild(tr);
  }

  body.querySelectorAll("button[data-id]").forEach((btn) => {
    btn.addEventListener("click", () =>
      openSale(Number(btn.dataset.id))
    );
  });
}

function openSale(id) {
  activeSale = allSales.find((s) => s.id === id);

  if (!activeSale) return;

  document.getElementById("saleModalTitle").textContent =
    `Invoice ${activeSale.invoice_no}`;

  document.getElementById("saleMeta").textContent =
    `${formatDateTime(activeSale.sale_date)} · ${
      activeSale.customer_name || "Walk-in"
    } · Cashier: ${activeSale.cashier_name || "—"}`;

  const body = document.getElementById("saleItemsBody");

  body.innerHTML = activeSale.items
    .map((i) => {
      const remaining = i.quantity - i.returned_quantity;

      return `
        <tr class="sale-item-row">
          <td data-label="Product">
            <span class="sale-product-name">
              ${escapeHtml(i.product_name || "—")}
            </span>
          </td>

          <td class="text-right num" data-label="Qty">
            ${i.quantity}
          </td>

          <td class="text-right num" data-label="Unit price">
            ${money(i.unit_price)}
          </td>

          <td class="text-right num" data-label="Subtotal">
            ${money(i.subtotal)}
          </td>

          <td class="text-right num" data-label="Returned">
            ${i.returned_quantity}
          </td>

          <td class="text-right sale-return-cell" data-label="Action">
            ${
              remaining > 0
                ? `
                  <button
                    class="btn btn-danger-outline btn-sm"
                    type="button"
                    data-return-id="${i.id}"
                    data-remaining="${remaining}"
                    data-name="${escapeHtml(i.product_name || "")}"
                  >
                    <i class="bi bi-arrow-return-left"></i>
                    <span>Return</span>
                  </button>
                `
                : `
                  <span class="text-muted small">
                    Fully returned
                  </span>
                `
            }
          </td>
        </tr>
      `;
    })
    .join("");

  body.querySelectorAll("[data-return-id]").forEach((btn) => {
    btn.addEventListener("click", () => openReturnModal(btn));
  });

  document.getElementById("saleTotalsBlock").innerHTML = `
    <div class="row">
      <span>Subtotal</span>
      <span>${money(activeSale.subtotal)}</span>
    </div>

    <div class="row">
      <span>Discount</span>
      <span>− ${money(activeSale.discount)}</span>
    </div>

    <div class="row">
      <span>Tax</span>
      <span>+ ${money(activeSale.tax)}</span>
    </div>

    <div
      class="row grand"
      style="color:var(--text-primary); border-color:var(--border-subtle);"
    >
      <span>Total</span>
      <span>${money(activeSale.total_amount)}</span>
    </div>

    <div class="row">
      <span>Paid</span>
      <span>${money(activeSale.amount_paid)}</span>
    </div>
  `;

  openModal("saleModal");
}

function openReturnModal(btn) {
  document.getElementById("returnSaleItemId").value =
    btn.dataset.returnId;

  document.getElementById("returnItemLabel").textContent =
    `${btn.dataset.name} — up to ${btn.dataset.remaining} unit(s) can be returned`;

  document.getElementById("returnQty").max =
    btn.dataset.remaining;

  document.getElementById("returnQty").value = 1;
  document.getElementById("returnReason").value = "";

  openModal("returnModal");
}

async function submitReturn(e) {
  e.preventDefault();

  const saleItemId = Number(
    document.getElementById("returnSaleItemId").value
  );

  const quantity = Number(
    document.getElementById("returnQty").value
  );

  const reason = document
    .getElementById("returnReason")
    .value.trim();

  try {
    await api.post("/returns", {
      sale_item_id: saleItemId,
      quantity,
      reason: reason || null,
    });

    toast("Return processed", "success");

    closeModal("returnModal");
    closeModal("saleModal");

    await loadSales();
  } catch (err) {
    friendlyError(err);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
