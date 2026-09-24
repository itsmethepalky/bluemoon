let allProducts = [];
let categories = [];
let brands = [];
let session;
let pendingProductImages = [];

(async function init() {
  session = await requireAuth(["admin", "staff"]);
  if (!session) return;

  document.getElementById("addProductBtn").addEventListener("click", openAddProduct);
  document.getElementById("manageTagsBtn").addEventListener("click", openTagsModal);
  document.getElementById("productForm").addEventListener("submit", saveProduct);
  document.getElementById("stockForm").addEventListener("submit", saveStockAdjustment);
  document.getElementById("categoryForm").addEventListener("submit", addCategory);
  document.getElementById("brandForm").addEventListener("submit", addBrand);

  document
    .getElementById("productImageFiles")
    .addEventListener("change", handleProductImageSelection);

  document.getElementById("searchInput").addEventListener("input", debounce(renderTable, 200));
  document.getElementById("categoryFilter").addEventListener("change", renderTable);
  document.getElementById("lowStockOnly").addEventListener("change", renderTable);

  await loadLookups();
  await loadProducts();
})();

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

async function loadLookups() {
  try {
    [categories, brands] = await Promise.all([
      api.get("/categories"),
      api.get("/brands"),
    ]);

    fillSelect("categorySelect", categories, "—");
    fillSelect("brandSelect", brands, "—");
    fillSelect("categoryFilter", categories, "All categories", true);

    renderTagLists();
  } catch (err) {
    friendlyError(err);
  }
}

function fillSelect(id, items, placeholder) {
  const el = document.getElementById(id);
  const current = el.value;

  el.innerHTML =
    `<option value="">${placeholder}</option>` +
    items
      .map(
        (i) =>
          `<option value="${i.id}">${escapeHtml(i.name)}</option>`
      )
      .join("");

  if (current) el.value = current;
}

async function loadProducts() {
  try {
    allProducts = await api.get("/products?active_only=true");
    renderTable();
  } catch (err) {
    friendlyError(err);
  }
}

function renderTable() {
  const q = document.getElementById("searchInput").value.trim().toLowerCase();
  const categoryId = document.getElementById("categoryFilter").value;
  const lowOnly = document.getElementById("lowStockOnly").checked;

  const rows = allProducts.filter((p) => {
    if (
      q &&
      !(
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q)
      )
    ) {
      return false;
    }

    if (categoryId && String(p.category_id) !== categoryId) {
      return false;
    }

    if (lowOnly && p.stock_quantity > p.reorder_level) {
      return false;
    }

    return true;
  });

  const body = document.getElementById("productsBody");
  const empty = document.getElementById("productsEmpty");

  body.innerHTML = "";

  if (!rows.length) {
    empty.classList.remove("hidden");
    return;
  }

  empty.classList.add("hidden");

  const isAdmin = session?.role === "admin";

  for (const p of rows) {
    const low = p.stock_quantity <= p.reorder_level;

    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td class="mono">${escapeHtml(p.sku)}</td>
      <td>${escapeHtml(p.name)}</td>
      <td>${escapeHtml(p.category_name ?? "—")}</td>
      <td>${escapeHtml(p.brand_name ?? "—")}</td>
      <td class="text-right num">${money(p.cost_price)}</td>
      <td class="text-right num">${money(p.unit_price)}</td>
      <td class="text-right">
        <span class="badge ${low ? "badge-brick" : "badge-green"}">
          ${p.stock_quantity}
        </span>
      </td>
      <td class="text-right">
        <button
          class="btn btn-outline btn-sm"
          data-action="stock"
          data-id="${p.id}"
        >
          Stock
        </button>

        <button
          class="btn btn-outline btn-sm"
          data-action="edit"
          data-id="${p.id}"
        >
          Edit
        </button>

        <button
          class="btn btn-danger-outline btn-sm"
          data-action="delete"
          data-id="${p.id}"
        >
          Delete
        </button>
      </td>
    `;

    body.appendChild(tr);
  }

  body
    .querySelectorAll("[data-action='edit']")
    .forEach((btn) =>
      btn.addEventListener(
        "click",
        () => openEditProduct(Number(btn.dataset.id))
      )
    );

  body
    .querySelectorAll("[data-action='stock']")
    .forEach((btn) =>
      btn.addEventListener(
        "click",
        () => openStockModal(Number(btn.dataset.id))
      )
    );

  body
    .querySelectorAll("[data-action='delete']")
    .forEach((btn) =>
      btn.addEventListener(
        "click",
        () => deleteProduct(Number(btn.dataset.id))
      )
    );
}


function handleProductImageSelection(e) {
  const files = Array.from(e.target.files || []);

  for (const file of files) {
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast(`${file.name}: only JPEG, PNG, or WebP images are allowed`, "error");
      continue;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast(`${file.name}: image must be 5 MB or smaller`, "error");
      continue;
    }

    pendingProductImages.push(file);
  }

  e.target.value = "";
  renderPendingProductImages();
}

function renderPendingProductImages() {
  const grid = document.getElementById("productImagesGrid");
  const empty = document.getElementById("productImagesEmpty");

  if (!grid || !empty) return;

  grid.querySelectorAll("[data-pending-image]").forEach((el) => el.remove());

  if (!pendingProductImages.length) {
    const hasExistingImages =
      grid.querySelectorAll("[data-existing-image]").length > 0;

    if (!hasExistingImages) {
      empty.textContent = "No images added yet.";
      empty.classList.remove("hidden");
    }

    return;
  }

  empty.classList.add("hidden");

  pendingProductImages.forEach((file, index) => {
    const url = URL.createObjectURL(file);

    const card = document.createElement("div");
    card.className = "product-image-card";
    card.dataset.pendingImage = "true";

    const img = document.createElement("img");
    img.src = url;
    img.alt = file.name;

    const actions = document.createElement("div");
    actions.className = "image-actions";

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "btn btn-danger-outline btn-sm";
    removeButton.textContent = "Remove";

    removeButton.addEventListener("click", () => {
      URL.revokeObjectURL(url);
      pendingProductImages.splice(index, 1);
      renderPendingProductImages();
    });

    actions.appendChild(removeButton);
    card.appendChild(img);
    card.appendChild(actions);
    grid.appendChild(card);
  });
}

async function loadProductImages(productId) {
  const grid = document.getElementById("productImagesGrid");
  const empty = document.getElementById("productImagesEmpty");

  if (!grid || !empty) return;

  grid.innerHTML = "";
  empty.textContent = "Loading images...";
  empty.classList.remove("hidden");

  try {
    const images = await api.get(`/product-images/${productId}`);

    grid.innerHTML = "";

    if (!images.length && !pendingProductImages.length) {
      empty.textContent = "No images added yet.";
      empty.classList.remove("hidden");
      return;
    }

    empty.classList.add("hidden");

    for (const image of images) {
      const card = document.createElement("div");
      card.className = "product-image-card";
      card.dataset.existingImage = "true";

      const img = document.createElement("img");
      img.src = image.image_url;
      img.alt = "Product image";

      card.appendChild(img);

      if (image.is_primary) {
        const badge = document.createElement("span");
        badge.className = "image-primary";
        badge.textContent = "Primary";
        card.appendChild(badge);
      }

      const actions = document.createElement("div");
      actions.className = "image-actions";

      if (!image.is_primary) {
        const primaryButton = document.createElement("button");
        primaryButton.type = "button";
        primaryButton.className = "btn btn-outline btn-sm";
        primaryButton.textContent = "Primary";

        primaryButton.addEventListener("click", () => {
          setPrimaryProductImage(image.id, productId);
        });

        actions.appendChild(primaryButton);
      }

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "btn btn-danger-outline btn-sm";
      deleteButton.textContent = "Delete";

      deleteButton.addEventListener("click", () => {
        deleteProductImage(image.id, productId);
      });

      actions.appendChild(deleteButton);
      card.appendChild(actions);
      grid.appendChild(card);
    }

    renderPendingProductImages();

  } catch (err) {
    console.error("Failed to load product images:", err);
    grid.innerHTML = "";
    empty.textContent = "Could not load product images.";
    empty.classList.remove("hidden");
  }
}

async function uploadPendingProductImages(productId) {
  if (!pendingProductImages.length) return;

  const files = [...pendingProductImages];

  for (const file of files) {
    const token = await getCurrentAccessToken();

    if (!token) {
      throw new Error("Your session has expired. Please log in again.");
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`/api/product-images/${productId}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      let message = `Failed to upload ${file.name}`;

      try {
        const data = await response.json();
        if (data?.detail) {
          message = data.detail;
        }
      } catch (_) {}

      throw new Error(message);
    }
  }

  pendingProductImages = [];
}

async function setPrimaryProductImage(imageId, productId) {
  try {
    const token = await getCurrentAccessToken();

    if (!token) {
      throw new Error("Your session has expired. Please log in again.");
    }

    const response = await fetch(`/api/product-images/${imageId}/primary`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      let message = "Failed to set primary image";

      try {
        const data = await response.json();
        if (data?.detail) {
          message = data.detail;
        }
      } catch (_) {}

      throw new Error(message);
    }

    toast("Primary image updated", "success");
    await loadProductImages(productId);

  } catch (err) {
    friendlyError(err);
  }
}

async function deleteProductImage(imageId, productId) {
  if (!confirm("Delete this product image?")) return;

  try {
    const token = await getCurrentAccessToken();

    if (!token) {
      throw new Error("Your session has expired. Please log in again.");
    }

    const response = await fetch(`/api/product-images/${imageId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      let message = "Failed to delete image";

      try {
        const data = await response.json();
        if (data?.detail) {
          message = data.detail;
        }
      } catch (_) {}

      throw new Error(message);
    }

    toast("Image deleted", "success");
    await loadProductImages(productId);

  } catch (err) {
    friendlyError(err);
  }
}

function openAddProduct() {
  document.getElementById("productModalTitle").textContent = "Add product";
  document.getElementById("productForm").reset();
  document.getElementById("productId").value = "";

  document.getElementById("stockField").classList.remove("hidden");
  document.getElementById("reorderLevel").value = 5;

  pendingProductImages = [];

  document.getElementById("productImagesGrid").innerHTML = "";
  document.getElementById("productImagesEmpty").textContent =
    "No images added yet.";
  document.getElementById("productImagesEmpty").classList.remove("hidden");

  openModal("productModal");
}

function openEditProduct(id) {
  const p = allProducts.find((x) => x.id === id);

  if (!p) return;

  document.getElementById("productModalTitle").textContent = "Edit product";

  document.getElementById("productId").value = p.id;
  document.getElementById("sku").value = p.sku;
  document.getElementById("name").value = p.name;
  document.getElementById("categorySelect").value = p.category_id ?? "";
  document.getElementById("brandSelect").value = p.brand_id ?? "";
  document.getElementById("costPrice").value = p.cost_price;
  document.getElementById("unitPrice").value = p.unit_price;
  document.getElementById("reorderLevel").value = p.reorder_level;

  document.getElementById("stockField").classList.add("hidden");

  pendingProductImages = [];

  openModal("productModal");
  loadProductImages(p.id);
}

async function saveProduct(e) {
  e.preventDefault();

  const id = document.getElementById("productId").value;

  const payload = {
    sku: document.getElementById("sku").value.trim(),
    name: document.getElementById("name").value.trim(),
    category_id: document.getElementById("categorySelect").value || null,
    brand_id: document.getElementById("brandSelect").value || null,
    cost_price: Number(document.getElementById("costPrice").value),
    unit_price: Number(document.getElementById("unitPrice").value),
    reorder_level: Number(document.getElementById("reorderLevel").value),
  };

  if (payload.category_id) {
    payload.category_id = Number(payload.category_id);
  }

  if (payload.brand_id) {
    payload.brand_id = Number(payload.brand_id);
  }

  try {
    let productId = id;

    if (id) {
      await api.put(`/products/${id}`, payload);
      toast("Product updated", "success");
    } else {
      payload.stock_quantity = Number(
        document.getElementById("stockQuantity").value || 0
      );

      const created = await api.post("/products", payload);
      productId = created.id;

      toast("Product added", "success");
    }

    await uploadPendingProductImages(productId);

    closeModal("productModal");
    await loadProducts();

  } catch (err) {
    friendlyError(err);
  }
}

async function deleteProduct(id) {
  const product = allProducts.find((p) => p.id === id);

  if (!product) return;

  const confirmed = confirm(
    `Delete "${product.name}"?\n\n` +
    `This will deactivate the product and remove it from the active inventory list.`
  );

  if (!confirmed) return;

  try {
    await api.del(`/products/${id}`);

    toast("Product deleted", "success");

    await loadProducts();
  } catch (err) {
    friendlyError(err);
  }
}

function openStockModal(id) {
  const p = allProducts.find((x) => x.id === id);

  if (!p) return;

  document.getElementById("stockProductId").value = id;

  document.getElementById("stockProductLabel").textContent =
    `${p.name} — currently ${p.stock_quantity} in stock`;

  document.getElementById("stockDelta").value = "";
  document.getElementById("stockReason").value = "";

  openModal("stockModal");
}

async function saveStockAdjustment(e) {
  e.preventDefault();

  const id = document.getElementById("stockProductId").value;
  const delta = Number(document.getElementById("stockDelta").value);
  const reason = document.getElementById("stockReason").value.trim();

  if (!Number.isInteger(delta) || delta === 0) {
    toast("Enter a non-zero whole-number quantity", "error");
    return;
  }

  try {
    await api.post(`/products/${id}/adjust-stock`, {
      delta,
      reason,
    });

    toast("Stock updated", "success");

    closeModal("stockModal");

    await loadProducts();
  } catch (err) {
    friendlyError(err);
  }
}

// -------------------------------------------------------------------------
// Categories & Brands
// -------------------------------------------------------------------------

function openTagsModal() {
  renderTagLists();
  openModal("tagsModal");
}

function renderTagLists() {
  const catList = document.getElementById("categoryList");

  catList.innerHTML =
    categories
      .map(
        (c) => `
          <li
            style="
              padding:8px 0;
              border-bottom:1px solid var(--border-subtle);
              display:flex;
              align-items:center;
              justify-content:space-between;
              gap:8px;
            "
          >
            <span>${escapeHtml(c.name)}</span>

            <span class="flex gap-8">
              <button
                class="btn btn-outline btn-sm"
                data-category-action="edit"
                data-id="${c.id}"
              >
                Edit
              </button>

              ${
                session?.role === "admin"
                  ? `
                    <button
                      class="btn btn-danger-outline btn-sm"
                      data-category-action="delete"
                      data-id="${c.id}"
                    >
                      Delete
                    </button>
                  `
                  : ""
              }
            </span>
          </li>
        `
      )
      .join("") ||
    '<li class="text-muted small">No categories yet.</li>';

  const brandList = document.getElementById("brandList");

  brandList.innerHTML =
    brands
      .map(
        (b) => `
          <li
            style="
              padding:8px 0;
              border-bottom:1px solid var(--border-subtle);
              display:flex;
              align-items:center;
              justify-content:space-between;
              gap:8px;
            "
          >
            <span>${escapeHtml(b.name)}</span>

            <span class="flex gap-8">
              <button
                class="btn btn-outline btn-sm"
                data-brand-action="edit"
                data-id="${b.id}"
              >
                Edit
              </button>

              ${
                session?.role === "admin"
                  ? `
                    <button
                      class="btn btn-danger-outline btn-sm"
                      data-brand-action="delete"
                      data-id="${b.id}"
                    >
                      Delete
                    </button>
                  `
                  : ""
              }
            </span>
          </li>
        `
      )
      .join("") ||
    '<li class="text-muted small">No brands yet.</li>';

  catList
    .querySelectorAll("[data-category-action='edit']")
    .forEach((btn) =>
      btn.addEventListener(
        "click",
        () => editCategory(Number(btn.dataset.id))
      )
    );

  catList
    .querySelectorAll("[data-category-action='delete']")
    .forEach((btn) =>
      btn.addEventListener(
        "click",
        () => deleteCategory(Number(btn.dataset.id))
      )
    );

  brandList
    .querySelectorAll("[data-brand-action='edit']")
    .forEach((btn) =>
      btn.addEventListener(
        "click",
        () => editBrand(Number(btn.dataset.id))
      )
    );

  brandList
    .querySelectorAll("[data-brand-action='delete']")
    .forEach((btn) =>
      btn.addEventListener(
        "click",
        () => deleteBrand(Number(btn.dataset.id))
      )
    );
}

async function addCategory(e) {
  e.preventDefault();

  const input = document.getElementById("newCategoryName");
  const name = input.value.trim();

  if (!name) return;

  try {
    await api.post("/categories", { name });

    input.value = "";

    await loadLookups();
    renderTagLists();

    toast("Category added", "success");
  } catch (err) {
    friendlyError(err);
  }
}

async function editCategory(id) {
  const category = categories.find((c) => c.id === id);

  if (!category) return;

  const name = prompt("Edit category name:", category.name);

  if (name === null) return;

  const trimmed = name.trim();

  if (!trimmed) {
    toast("Category name is required", "error");
    return;
  }

  try {
    await api.put(`/categories/${id}`, {
      name: trimmed,
    });

    await loadLookups();
    renderTagLists();

    toast("Category updated", "success");
  } catch (err) {
    friendlyError(err);
  }
}

async function deleteCategory(id) {
  const category = categories.find((c) => c.id === id);

  if (!category) return;

  if (
    !confirm(
      `Delete category "${category.name}"?\n\n` +
      `Categories used by products may not be deletable.`
    )
  ) {
    return;
  }

  try {
    await api.del(`/categories/${id}`);

    await loadLookups();
    renderTagLists();

    toast("Category deleted", "success");
  } catch (err) {
    friendlyError(err);
  }
}

async function addBrand(e) {
  e.preventDefault();

  const input = document.getElementById("newBrandName");
  const name = input.value.trim();

  if (!name) return;

  try {
    await api.post("/brands", { name });

    input.value = "";

    await loadLookups();
    renderTagLists();

    toast("Brand added", "success");
  } catch (err) {
    friendlyError(err);
  }
}

async function editBrand(id) {
  const brand = brands.find((b) => b.id === id);

  if (!brand) return;

  const name = prompt("Edit brand name:", brand.name);

  if (name === null) return;

  const trimmed = name.trim();

  if (!trimmed) {
    toast("Brand name is required", "error");
    return;
  }

  try {
    await api.put(`/brands/${id}`, {
      name: trimmed,
    });

    await loadLookups();
    renderTagLists();

    toast("Brand updated", "success");
  } catch (err) {
    friendlyError(err);
  }
}

async function deleteBrand(id) {
  const brand = brands.find((b) => b.id === id);

  if (!brand) return;

  if (
    !confirm(
      `Delete brand "${brand.name}"?\n\n` +
      `A brand cannot be deleted while products are using it.`
    )
  ) {
    return;
  }

  try {
    await api.del(`/brands/${id}`);

    await loadLookups();
    renderTagLists();

    toast("Brand deleted", "success");
  } catch (err) {
    friendlyError(err);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
