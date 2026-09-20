let allSuppliers = [];

(async function init() {
  const session = await requireAuth(["admin", "staff"]);
  if (!session) return;

  document.getElementById("addSupplierBtn").addEventListener("click", openAddSupplier);
  document.getElementById("supplierForm").addEventListener("submit", saveSupplier);

  await loadSuppliers();
})();

async function loadSuppliers() {
  try {
    allSuppliers = await api.get("/suppliers");
    renderTable();
  } catch (err) {
    friendlyError(err);
  }
}

function renderTable() {
  const body = document.getElementById("suppliersBody");
  const empty = document.getElementById("suppliersEmpty");
  body.innerHTML = "";

  if (!allSuppliers.length) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");

  const isAdmin = getSession()?.role === "admin";

  for (const s of allSuppliers) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(s.name)}</td>
      <td>${escapeHtml(s.contact_person || "—")}</td>
      <td>${escapeHtml(s.phone || "—")}</td>
      <td>${escapeHtml(s.email || "—")}</td>
      <td>${escapeHtml(s.address || "—")}</td>
      <td class="text-right">
        <button class="btn btn-outline btn-sm" data-action="edit" data-id="${s.id}">Edit</button>
        ${isAdmin ? `<button class="btn btn-danger-outline btn-sm" data-action="delete" data-id="${s.id}">Delete</button>` : ""}
      </td>
    `;
    body.appendChild(tr);
  }

  body.querySelectorAll("[data-action='edit']").forEach((btn) =>
    btn.addEventListener("click", () => openEditSupplier(Number(btn.dataset.id)))
  );
  body.querySelectorAll("[data-action='delete']").forEach((btn) =>
    btn.addEventListener("click", () => deleteSupplier(Number(btn.dataset.id)))
  );
}

function openAddSupplier() {
  document.getElementById("supplierModalTitle").textContent = "Add supplier";
  document.getElementById("supplierForm").reset();
  document.getElementById("supplierId").value = "";
  openModal("supplierModal");
}

function openEditSupplier(id) {
  const s = allSuppliers.find((x) => x.id === id);
  if (!s) return;
  document.getElementById("supplierModalTitle").textContent = "Edit supplier";
  document.getElementById("supplierId").value = s.id;
  document.getElementById("supplierName").value = s.name;
  document.getElementById("contactPerson").value = s.contact_person || "";
  document.getElementById("supplierPhone").value = s.phone || "";
  document.getElementById("supplierEmail").value = s.email || "";
  document.getElementById("supplierAddress").value = s.address || "";
  openModal("supplierModal");
}

async function saveSupplier(e) {
  e.preventDefault();
  const id = document.getElementById("supplierId").value;
  const payload = {
    name: document.getElementById("supplierName").value.trim(),
    contact_person: document.getElementById("contactPerson").value.trim() || null,
    phone: document.getElementById("supplierPhone").value.trim() || null,
    email: document.getElementById("supplierEmail").value.trim() || null,
    address: document.getElementById("supplierAddress").value.trim() || null,
  };

  try {
    if (id) {
      await api.put(`/suppliers/${id}`, payload);
      toast("Supplier updated", "success");
    } else {
      await api.post("/suppliers", payload);
      toast("Supplier added", "success");
    }
    closeModal("supplierModal");
    await loadSuppliers();
  } catch (err) {
    friendlyError(err);
  }
}

async function deleteSupplier(id) {
  if (!confirm("Delete this supplier? This can't be undone.")) return;
  try {
    await api.del(`/suppliers/${id}`);
    toast("Supplier deleted", "success");
    await loadSuppliers();
  } catch (err) {
    friendlyError(err);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
