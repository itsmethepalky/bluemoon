let allUsers = [];

(async function init() {
  const session = await requireAuth(["admin"]);
  if (!session) return;

  document.getElementById("addUserBtn").addEventListener("click", openAddUser);
  document.getElementById("userForm").addEventListener("submit", saveUser);

  await loadUsers();
})();

async function loadUsers() {
  try {
    allUsers = await api.get("/users");
    renderTable();
  } catch (err) {
    friendlyError(err);
  }
}

const ROLE_BADGE = { admin: "badge-ink", staff: "badge-slate", customer: "badge-green" };

function renderTable() {
  const body = document.getElementById("usersBody");
  const me = getSession()?.user_id;
  body.innerHTML = "";

  for (const u of allUsers) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(u.full_name)}</td>
      <td class="mono">${escapeHtml(u.email || "—")}</td>
      <td><span class="badge ${ROLE_BADGE[u.role] || "badge-slate"}">${u.role}</span></td>
      <td>${escapeHtml(u.phone || "—")}</td>
      <td>${u.is_active ? '<span class="badge badge-green">Active</span>' : '<span class="badge badge-brick">Disabled</span>'}</td>
      <td class="text-right">
        <button class="btn btn-outline btn-sm" data-action="edit" data-id="${u.id}">Edit</button>
        ${u.is_active && u.id !== me ? `<button class="btn btn-danger-outline btn-sm" data-action="disable" data-id="${u.id}">Disable</button>` : ""}
      </td>
    `;
    body.appendChild(tr);
  }

  body.querySelectorAll("[data-action='edit']").forEach((btn) => btn.addEventListener("click", () => openEditUser(btn.dataset.id)));
  body.querySelectorAll("[data-action='disable']").forEach((btn) => btn.addEventListener("click", () => disableUser(btn.dataset.id)));
}

function openAddUser() {
  document.getElementById("userModalTitle").textContent = "Add account";
  document.getElementById("userForm").reset();
  document.getElementById("userId").value = "";
  document.getElementById("userEmail").disabled = false;
  document.getElementById("userPassword").required = true;
  document.getElementById("passwordLabel").textContent = "Password";
  document.getElementById("userPassword").placeholder = "Min. 6 characters";
  openModal("userModal");
}

function openEditUser(id) {
  const u = allUsers.find((x) => x.id === id);
  if (!u) return;
  document.getElementById("userModalTitle").textContent = "Edit account";
  document.getElementById("userId").value = u.id;
  document.getElementById("fullName").value = u.full_name;
  document.getElementById("userEmail").value = u.email || "";
  document.getElementById("roleSelect").value = u.role === "customer" ? "staff" : u.role;
  document.getElementById("userPhone").value = u.phone || "";
  document.getElementById("userPassword").value = "";
  document.getElementById("userPassword").required = false;
  document.getElementById("passwordLabel").textContent = "New password (optional)";
  document.getElementById("userPassword").placeholder = "Leave blank to keep current password";
  openModal("userModal");
}

async function saveUser(e) {
  e.preventDefault();
  const id = document.getElementById("userId").value;
  const password = document.getElementById("userPassword").value;

  try {
    if (id) {
      const payload = {
        full_name: document.getElementById("fullName").value.trim(),
        role: document.getElementById("roleSelect").value,
        email: document.getElementById("userEmail").value.trim() || null,
        phone: document.getElementById("userPhone").value.trim() || null,
      };
      if (password) payload.password = password;
      await api.put(`/users/${id}`, payload);
      toast("Account updated", "success");
    } else {
      const payload = {
        full_name: document.getElementById("fullName").value.trim(),
        email: document.getElementById("userEmail").value.trim(),
        role: document.getElementById("roleSelect").value,
        phone: document.getElementById("userPhone").value.trim() || null,
        password,
      };
      await api.post("/users", payload);
      toast("Account created", "success");
    }
    closeModal("userModal");
    await loadUsers();
  } catch (err) {
    friendlyError(err);
  }
}

async function disableUser(id) {
  if (!confirm("Disable this account? They will no longer be able to sign in.")) return;
  try {
    await api.del(`/users/${id}`);
    toast("Account disabled", "success");
    await loadUsers();
  } catch (err) {
    friendlyError(err);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
