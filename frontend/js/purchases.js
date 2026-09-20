let purchaseProducts = [];
let purchaseSuppliers = [];
let allPurchases = [];
let itemRowCounter = 0;

(async function init() {
  const session = await requireAuth(["admin", "staff"]);
  if (!session) return;

  document.getElementById("addPurchaseBtn").addEventListener("click", openPurchaseModal);
  document.getElementById("addItemRowBtn").addEventListener("click", () => addItemRow());
  document.getElementById("purchaseForm").addEventListener("submit", savePurchase);

  await Promise.all([loadProducts(), loadSuppliers()]);
  await loadPurchases();
})();

async function loadProducts() {
  purchaseProducts = await api.get("/products?active_only=true");
}

async function loadSuppliers() {
  purchaseSuppliers = await api.get("/suppliers");
  const sel = document.getElementById("supplierSelect");
  sel.innerHTML =
    '<option value="">Select a supplier…</option>' +
    purchaseSuppliers.map((s) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join("");
}

async function loadPurchases() {
  try {
    allPurchases = await api.get("/purchases");
    renderTable();
  } catch (err) {
    friendlyError(err);
  }
}

function renderTable() {
  const body = document.getElementById("purchasesBody");
  const empty = document.getElementById("purchasesEmpty");
  body.innerHTML = "";

  if (!allPurchases.length) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");

  for (const p of allPurchases) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono">${escapeHtml(p.reference_no)}</td>
      <td>${formatDateTime(p.purchase_date)}</td>
      <td>${escapeHtml(p.supplier_name || "—")}</td>
      <td class="text-right num">${p.items.length}</td>
      <td class="text-right num">${money(p.total_amount)}</td>
      <td class="text-right"><button class="btn btn-outline btn-sm" data-id="${p.id}">View</button></td>
    `;
    body.appendChild(tr);
  }

  body.querySelectorAll("button[data-id]").forEach((btn) =>
    btn.addEventListener("click", () => viewPurchase(Number(btn.dataset.id)))
  );
}

function viewPurchase(id) {
  const p = allPurchases.find((x) => x.id === id);
  if (!p) return;
  document.getElementById("viewPurchaseTitle").textContent = p.reference_no;
  document.getElementById("viewPurchaseMeta").textContent =
    `${formatDateTime(p.purchase_date)} · ${p.supplier_name || "—"}${p.notes ? " · " + p.notes : ""}`;
  document.getElementById("viewPurchaseItemsBody").innerHTML = p.items
    .map(
      (i) => `
      <tr>
        <td>${escapeHtml(i.product_name || "—")}</td>
        <td class="text-right num">${i.quantity}</td>
        <td class="text-right num">${money(i.unit_cost)}</td>
        <td class="text-right num">${money(i.subtotal)}</td>
      </tr>
    `
    )
    .join("");
  openModal("viewPurchaseModal");
}

// ---- Record purchase modal -----------------------------------------------

function openPurchaseModal() {
  document.getElementById("purchaseForm").reset();
  document.getElementById("purchaseItemsBody").innerHTML = "";
  itemRowCounter = 0;
  addItemRow();
  recalcGrandTotal();
  openModal("purchaseModal");
}

function addItemRow() {
  const id = ++itemRowCounter;
  const body = document.getElementById("purchaseItemsBody");
  const tr = document.createElement("tr");
  tr.dataset.rowId = id;
  tr.innerHTML = `
    <td>
      <select class="row-product" required>
        <option value="">Select product…</option>
        ${purchaseProducts.map((p) => `<option value="${p.id}" data-cost="${p.cost_price}">${escapeHtml(p.name)} (${escapeHtml(p.sku)})</option>`).join("")}
      </select>
    </td>
    <td><input class="row-qty" type="number" min="1" step="1" value="1" required></td>
    <td><input class="row-cost" type="number" min="0" step="0.01" value="0" required></td>
    <td class="text-right num row-subtotal">Rs. 0.00</td>
    <td class="text-right"><button type="button" class="btn btn-outline btn-sm row-remove"><i class="bi bi-x"></i></button></td>
  `;
  body.appendChild(tr);

  const productSel = tr.querySelector(".row-product");
  const qtyInput = tr.querySelector(".row-qty");
  const costInput = tr.querySelector(".row-cost");

  productSel.addEventListener("change", () => {
    const opt = productSel.selectedOptions[0];
    if (opt && opt.dataset.cost) costInput.value = Number(opt.dataset.cost).toFixed(2);
    recalcRow(tr);
  });
  qtyInput.addEventListener("input", () => recalcRow(tr));
  costInput.addEventListener("input", () => recalcRow(tr));
  tr.querySelector(".row-remove").addEventListener("click", () => {
    tr.remove();
    recalcGrandTotal();
  });

  recalcRow(tr);
}

function recalcRow(tr) {
  const qty = Number(tr.querySelector(".row-qty").value || 0);
  const cost = Number(tr.querySelector(".row-cost").value || 0);
  tr.querySelector(".row-subtotal").textContent = money(qty * cost);
  recalcGrandTotal();
}

function recalcGrandTotal() {
  let total = 0;
  document.querySelectorAll("#purchaseItemsBody tr").forEach((tr) => {
    const qty = Number(tr.querySelector(".row-qty")?.value || 0);
    const cost = Number(tr.querySelector(".row-cost")?.value || 0);
    total += qty * cost;
  });
  document.getElementById("purchaseGrandTotal").textContent = money(total);
}

async function savePurchase(e) {
  e.preventDefault();
  const supplierId = document.getElementById("supplierSelect").value;
  if (!supplierId) {
    toast("Select a supplier", "error");
    return;
  }

  const rows = [...document.querySelectorAll("#purchaseItemsBody tr")];
  if (!rows.length) {
    toast("Add at least one item", "error");
    return;
  }

  const items = [];
  for (const tr of rows) {
    const productId = tr.querySelector(".row-product").value;
    const quantity = Number(tr.querySelector(".row-qty").value);
    const unitCost = Number(tr.querySelector(".row-cost").value);
    if (!productId || quantity <= 0) {
      toast("Every item row needs a product and a quantity greater than zero", "error");
      return;
    }
    items.push({ product_id: Number(productId), quantity, unit_cost: unitCost });
  }

  const payload = {
    supplier_id: Number(supplierId),
    notes: document.getElementById("purchaseNotes").value.trim() || null,
    items,
  };

  try {
    await api.post("/purchases", payload);
    toast("Purchase recorded — stock updated", "success");
    closeModal("purchaseModal");
    await Promise.all([loadProducts(), loadPurchases()]);
  } catch (err) {
    friendlyError(err);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
