(async function init() {
  const session = await requireAuth(["customer"]);
  if (!session) return;

  try {
    const customer = await api.get("/customers/me");

    document.getElementById("profileName").textContent = customer.name || "—";
    document.getElementById("profilePhone").textContent = customer.phone || "—";
    document.getElementById("profileEmail").textContent = customer.email || "—";
    document.getElementById("profileAddress").textContent = customer.address || "—";

    document.getElementById("statCreditLimit").textContent = money(customer.credit_limit);
    document.getElementById("statCreditBalance").textContent = money(customer.credit_balance);

    const sales = await api.get(`/customers/${customer.id}/history`);
    document.getElementById("statOrderCount").textContent = sales.length;
    renderHistory(sales);
  } catch (err) {
    friendlyError(err);
  }
})();

function renderHistory(sales) {
  const body = document.getElementById("historyBody");
  const empty = document.getElementById("historyEmpty");
  body.innerHTML = "";

  if (!sales.length) {
    empty.classList.remove("hidden");
    return;
  }
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
