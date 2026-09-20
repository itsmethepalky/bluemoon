let posProducts = [];
let posCustomers = [];
let cart = []; // [{product_id, name, unit_price, quantity, stock}]
let lastSale = null;

(async function init() {
  const session = await requireAuth(["admin", "staff"]);
  if (!session) return;

  document.getElementById("productSearch").addEventListener("input", debounce(renderProductGrid, 150));
  document.getElementById("orderDiscount").addEventListener("input", renderTotals);
  document.getElementById("orderTax").addEventListener("input", renderTotals);
  document.getElementById("paymentMethod").addEventListener("change", onPaymentMethodChange);
  document.getElementById("completeSaleBtn").addEventListener("click", completeSale);
  document.getElementById("newSaleBtn").addEventListener("click", startNextSale);
  document.getElementById("printReceiptBtn").addEventListener("click", () => window.print());

  await Promise.all([loadProducts(), loadCustomers()]);
})();

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

async function loadProducts() {
  try {
    posProducts = await api.get("/products?active_only=true");
    renderProductGrid();
  } catch (err) {
    friendlyError(err);
  }
}

async function loadCustomers() {
  try {
    posCustomers = await api.get("/customers");
    const sel = document.getElementById("customerSelect");
    sel.innerHTML =
      '<option value="">Walk-in / cash customer</option>' +
      posCustomers.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
  } catch (err) {
    friendlyError(err);
  }
}

function renderProductGrid() {
  const q = document.getElementById("productSearch").value.trim().toLowerCase();
  const grid = document.getElementById("productGrid");
  const rows = posProducts.filter(
    (p) => !q || p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
  );

  if (!rows.length) {
    grid.innerHTML = '<div class="empty-state"><i class="bi bi-search"></i>No products match your search.</div>';
    return;
  }

  grid.innerHTML = rows
    .map((p) => {
      const out = p.stock_quantity <= 0;
      return `
        <button type="button" class="product-tile ${out ? "out-of-stock" : ""}" data-id="${p.id}" ${out ? "disabled" : ""}>
          <div class="name">${escapeHtml(p.name)}</div>
          <div class="price">${money(p.unit_price)}</div>
          <div class="stock">${out ? "Out of stock" : p.stock_quantity + " in stock"}</div>
        </button>
      `;
    })
    .join("");

  grid.querySelectorAll(".product-tile:not(:disabled)").forEach((tile) => {
    tile.addEventListener("click", () => addToCart(Number(tile.dataset.id)));
  });
}

function addToCart(productId) {
  const product = posProducts.find((p) => p.id === productId);
  if (!product) return;

  const line = cart.find((l) => l.product_id === productId);
  if (line) {
    if (line.quantity + 1 > product.stock_quantity) {
      toast(`Only ${product.stock_quantity} unit(s) of "${product.name}" available`, "error");
      return;
    }
    line.quantity += 1;
  } else {
    if (product.stock_quantity < 1) return;
    cart.push({
      product_id: product.id,
      name: product.name,
      unit_price: product.unit_price,
      quantity: 1,
      stock: product.stock_quantity,
    });
  }
  renderCart();
}

function changeQty(productId, delta) {
  const line = cart.find((l) => l.product_id === productId);
  if (!line) return;
  const product = posProducts.find((p) => p.id === productId);
  const newQty = line.quantity + delta;
  if (newQty <= 0) {
    cart = cart.filter((l) => l.product_id !== productId);
  } else if (product && newQty > product.stock_quantity) {
    toast(`Only ${product.stock_quantity} unit(s) of "${line.name}" available`, "error");
    return;
  } else {
    line.quantity = newQty;
  }
  renderCart();
}

function removeLine(productId) {
  cart = cart.filter((l) => l.product_id !== productId);
  renderCart();
}

function renderCart() {
  const box = document.getElementById("cartLines");
  const completeBtn = document.getElementById("completeSaleBtn");

  if (!cart.length) {
    box.innerHTML = '<div class="receipt-empty">Cart is empty — add a product to begin.</div>';
    completeBtn.disabled = true;
    renderTotals();
    return;
  }
  completeBtn.disabled = false;

  box.innerHTML = cart
    .map(
      (l) => `
      <div class="receipt-line">
        <div>
          <div>${escapeHtml(l.name)}</div>
          <div class="qty-controls">
            <button type="button" data-action="dec" data-id="${l.product_id}">−</button>
            <span>${l.quantity}</span>
            <button type="button" data-action="inc" data-id="${l.product_id}">+</button>
          </div>
        </div>
        <div style="text-align:right;">
          <div>${money(l.unit_price * l.quantity)}</div>
          <button type="button" data-action="remove" data-id="${l.product_id}" style="background:none;border:none;color:var(--text-on-ink-muted);cursor:pointer;font-size:11px;padding:0;margin-top:4px;">Remove</button>
        </div>
      </div>
    `
    )
    .join("");

  box.querySelectorAll("[data-action='inc']").forEach((b) => b.addEventListener("click", () => changeQty(Number(b.dataset.id), 1)));
  box.querySelectorAll("[data-action='dec']").forEach((b) => b.addEventListener("click", () => changeQty(Number(b.dataset.id), -1)));
  box.querySelectorAll("[data-action='remove']").forEach((b) => b.addEventListener("click", () => removeLine(Number(b.dataset.id))));

  renderTotals();
}

function cartSubtotal() {
  return cart.reduce((sum, l) => sum + l.unit_price * l.quantity, 0);
}

function renderTotals() {
  const subtotal = cartSubtotal();
  const discount = Number(document.getElementById("orderDiscount").value || 0);
  const tax = Number(document.getElementById("orderTax").value || 0);
  const total = Math.max(0, subtotal - discount + tax);

  document.getElementById("totalSubtotal").textContent = money(subtotal);
  document.getElementById("totalDiscount").textContent = "− " + money(discount);
  document.getElementById("totalTax").textContent = "+ " + money(tax);
  document.getElementById("totalGrand").textContent = money(total);

  const method = document.getElementById("paymentMethod").value;
  if (method !== "credit") {
    document.getElementById("amountPaid").value = total.toFixed(2);
  }
}

function onPaymentMethodChange() {
  const method = document.getElementById("paymentMethod").value;
  const amountPaid = document.getElementById("amountPaid");
  if (method === "credit") {
    amountPaid.value = "0.00";
  } else {
    const subtotal = cartSubtotal();
    const discount = Number(document.getElementById("orderDiscount").value || 0);
    const tax = Number(document.getElementById("orderTax").value || 0);
    amountPaid.value = Math.max(0, subtotal - discount + tax).toFixed(2);
  }
}

async function completeSale() {
  if (!cart.length) return;
  const customerId = document.getElementById("customerSelect").value;
  const paymentMethod = document.getElementById("paymentMethod").value;

  if (paymentMethod === "credit" && !customerId) {
    toast("Select a customer for a credit sale", "error");
    return;
  }

  const payload = {
    customer_id: customerId ? Number(customerId) : null,
    items: cart.map((l) => ({ product_id: l.product_id, quantity: l.quantity, discount: 0 })),
    discount: Number(document.getElementById("orderDiscount").value || 0),
    tax: Number(document.getElementById("orderTax").value || 0),
    payment_method: paymentMethod,
    amount_paid: Number(document.getElementById("amountPaid").value || 0),
  };

  const btn = document.getElementById("completeSaleBtn");
  btn.disabled = true;
  try {
    const sale = await api.post("/sales", payload);
    lastSale = sale;
    showReceipt(sale);
    await loadProducts(); // stock levels changed
  } catch (err) {
    friendlyError(err);
    btn.disabled = false;
  }
}

function showReceipt(sale) {
  const lines = sale.items
    .map(
      (i) =>
        `${i.product_name.padEnd(24).slice(0, 24)} x${i.quantity}`.padEnd(32) +
        money(i.subtotal).padStart(14)
    )
    .join("\n");

  document.getElementById("receiptContent").textContent =
    `The Blue Moon — Invoice ${sale.invoice_no}\n` +
    `${formatDateTime(sale.sale_date)}\n` +
    `Customer: ${sale.customer_name}\n` +
    `Cashier: ${sale.cashier_name}\n` +
    `${"-".repeat(46)}\n` +
    `${lines}\n` +
    `${"-".repeat(46)}\n` +
    `Subtotal:`.padEnd(32) + money(sale.subtotal).padStart(14) + "\n" +
    `Discount:`.padEnd(32) + ("− " + money(sale.discount)).padStart(14) + "\n" +
    `Tax:`.padEnd(32) + ("+ " + money(sale.tax)).padStart(14) + "\n" +
    `TOTAL:`.padEnd(32) + money(sale.total_amount).padStart(14) + "\n" +
    `Paid (${sale.payment_method}):`.padEnd(32) + money(sale.amount_paid).padStart(14) + "\n" +
    (sale.total_amount - sale.amount_paid > 0
      ? `Balance due:`.padEnd(32) + money(sale.total_amount - sale.amount_paid).padStart(14) + "\n"
      : "");

  openModal("receiptModal");
}

function startNextSale() {
  cart = [];
  document.getElementById("orderDiscount").value = 0;
  document.getElementById("orderTax").value = 0;
  document.getElementById("paymentMethod").value = "cash";
  document.getElementById("customerSelect").value = "";
  renderCart();
  closeModal("receiptModal");
  document.getElementById("completeSaleBtn").disabled = true;
  document.getElementById("productSearch").focus();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
