let allCustomers = [];

(async function init() {
  const session = await requireAuth(["admin", "staff"]);
  if (!session) return;

  document.getElementById("addCustomerBtn").addEventListener("click", openAddCustomer);
  document.getElementById("customerForm").addEventListener("submit", saveCustomer);
  document.getElementById("paymentForm").addEventListener("submit", savePayment);
  document.getElementById("searchInput").addEventListener("input", debounce(loadCustomers, 250));

  await loadCustomers();
})();

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

async function loadCustomers() {
  const q = document.getElementById("searchInput").value.trim();
  try {
    allCustomers = await api.get(`/customers${q ? "?q=" + encodeURIComponent(q) : ""}`);
    renderTable();
  } catch (err) {
    friendlyError(err);
  }
}

function renderTable() {
  const body = document.getElementById("customersBody");
  const empty = document.getElementById("customersEmpty");
  body.innerHTML = "";

  if (!allCustomers.length) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");

  const isAdmin = getSession()?.role === "admin";

  for (const c of allCustomers) {
    const owesBadge = c.credit_balance > 0 ? "badge-brick" : "badge-green";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(c.name)}</td>
      <td>${escapeHtml(c.phone || "—")}</td>
      <td>${escapeHtml(c.email || "—")}</td>
      <td class="text-right num">${money(c.credit_limit)}</td>
      <td class="text-right"><span class="badge ${owesBadge}">${money(c.credit_balance)}</span></td>
      <td class="text-right">
        <button class="btn btn-outline btn-sm" data-action="history" data-id="${c.id}">History</button>
        ${c.credit_balance > 0 ? `<button class="btn btn-outline btn-sm" data-action="pay" data-id="${c.id}">Payment</button>` : ""}
        <button class="btn btn-outline btn-sm" data-action="edit" data-id="${c.id}">Edit</button>
        ${isAdmin ? `<button class="btn btn-danger-outline btn-sm" data-action="delete" data-id="${c.id}">Delete</button>` : ""}
      </td>
    `;
    body.appendChild(tr);
  }

  body.querySelectorAll("[data-action='edit']").forEach((btn) => btn.addEventListener("click", () => openEditCustomer(Number(btn.dataset.id))));
  body.querySelectorAll("[data-action='pay']").forEach((btn) => btn.addEventListener("click", () => openPayment(Number(btn.dataset.id))));
  body.querySelectorAll("[data-action='history']").forEach((btn) => btn.addEventListener("click", () => openHistory(Number(btn.dataset.id))));
  body.querySelectorAll("[data-action='delete']").forEach((btn) => btn.addEventListener("click", () => deleteCustomer(Number(btn.dataset.id))));
}

function openAddCustomer() {
  document.getElementById("customerModalTitle").textContent = "Add customer";
  document.getElementById("customerForm").reset();
  document.getElementById("customerId").value = "";
  openModal("customerModal");
}

function openEditCustomer(id) {
  const c = allCustomers.find((x) => x.id === id);
  if (!c) return;
  document.getElementById("customerModalTitle").textContent = "Edit customer";
  document.getElementById("customerId").value = c.id;
  document.getElementById("customerName").value = c.name;
  document.getElementById("customerPhone").value = c.phone || "";
  document.getElementById("customerEmail").value = c.email || "";
  document.getElementById("customerAddress").value = c.address || "";
  document.getElementById("creditLimit").value = c.credit_limit;
  openModal("customerModal");
}

async function saveCustomer(e) {
  e.preventDefault();
  const id = document.getElementById("customerId").value;
  const payload = {
    name: document.getElementById("customerName").value.trim(),
    phone: document.getElementById("customerPhone").value.trim() || null,
    email: document.getElementById("customerEmail").value.trim() || null,
    address: document.getElementById("customerAddress").value.trim() || null,
    credit_limit: Number(document.getElementById("creditLimit").value || 0),
  };

  try {
    if (id) {
      await api.put(`/customers/${id}`, payload);
      toast("Customer updated", "success");
    } else {
      await api.post("/customers", payload);
      toast("Customer added", "success");
    }
    closeModal("customerModal");
    await loadCustomers();
  } catch (err) {
    friendlyError(err);
  }
}

function openPayment(id) {
  const c = allCustomers.find((x) => x.id === id);
  if (!c) return;
  document.getElementById("paymentCustomerId").value = c.id;
  document.getElementById("paymentCustomerLabel").textContent =
    `${c.name} currently owes ${money(c.credit_balance)}`;
  document.getElementById("paymentAmount").max = c.credit_balance;
  document.getElementById("paymentAmount").value = c.credit_balance.toFixed(2);
  document.getElementById("paymentNote").value = "";
  openModal("paymentModal");
}

async function savePayment(e) {
  e.preventDefault();
  const id = document.getElementById("paymentCustomerId").value;
  const amount = Number(document.getElementById("paymentAmount").value);
  const note = document.getElementById("paymentNote").value.trim();
  try {
    await api.post(`/customers/${id}/credit-payment`, { amount, note: note || null });
    toast("Payment recorded", "success");
    closeModal("paymentModal");
    await loadCustomers();
  } catch (err) {
    friendlyError(err);
  }
}

async function openHistory(id) {
  const c = allCustomers.find((x) => x.id === id);
  if (!c) return;
  document.getElementById("historyModalTitle").textContent = `${c.name} — purchase history`;
  try {
    const sales = await api.get(`/customers/${id}/history`);
    const body = document.getElementById("historyBody");
    const empty = document.getElementById("historyEmpty");
    body.innerHTML = "";
    if (!sales.length) {
      empty.classList.remove("hidden");
    } else {
      empty.classList.add("hidden");
      for (const s of sales) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="mono">${s.invoice_no}</td>
          <td>${formatDateTime(s.sale_date)}</td>
          <td class="text-right num">${money(s.total_amount)}</td>
          <td>${s.payment_method}</td>
          <td>${s.payment_status}</td>
        `;
        body.appendChild(tr);
      }
    }
    openModal("historyModal");
  } catch (err) {
    friendlyError(err);
  }
}

async function deleteCustomer(id) {
  if (!confirm("Delete this customer? This can't be undone.")) return;
  try {
    await api.del(`/customers/${id}`);
    toast("Customer deleted", "success");
    await loadCustomers();
  } catch (err) {
    friendlyError(err);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
