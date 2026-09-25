(function () {
  "use strict";

  const currentPath =
    window.location.pathname + window.location.search;

  const loginUrl =
    "/login?redirect=" + encodeURIComponent(currentPath);

  // Hide private page content immediately while authorization is checked.
  document.documentElement.classList.add("auth-checking");

  const style = document.createElement("style");
  style.id = "auth-guard-style";
  style.textContent = `
    html.auth-checking body {
      visibility: hidden !important;
    }

    html.auth-checking::before {
      content: "Checking authorization...";
      position: fixed;
      inset: 0;
      z-index: 2147483647;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f4efe5;
      color: #18242b;
      font-family: system-ui, sans-serif;
      font-size: 15px;
    }
  `;

  document.head.appendChild(style);

  function allowPage() {
    document.documentElement.classList.remove("auth-checking");
  }

  function redirectToLogin() {
    window.location.replace(loginUrl);
  }

  async function getApplicationSession() {
    // api.js already contains the POS's authoritative authentication flow.
    if (typeof window.getAuthenticatedSession === "function") {
      return await window.getAuthenticatedSession();
    }

    if (typeof window.bootstrapSession === "function") {
      return await window.bootstrapSession();
    }

    throw new Error("POS authentication system is not available.");
  }

  function requiredRoles(path) {
    const page = path.split("/").pop().toLowerCase();

    // My Account and password update only require authentication.
    if (
      page === "my-account" ||
      page === "update-password"
    ) {
      return null;
    }

    // User management is admin-only.
    if (page === "users") {
      return ["admin"];
    }

    // POS management pages require staff-level access.
    const staffPages = [
      "dashboard",
      "pos",
      "products",
      "purchases",
      "suppliers",
      "customers",
      "reports",
      "sales-history"
    ];

    if (staffPages.includes(page)) {
      return ["admin", "staff"];
    }

    return null;
  }

  async function guard() {
    try {
      const session = await getApplicationSession();

      if (!session || !session.access_token) {
        redirectToLogin();
        return;
      }

      const roles = requiredRoles(window.location.pathname);

      if (
        roles &&
        !roles.includes(String(session.role || "").toLowerCase())
      ) {
        // Send authenticated users to an appropriate safe page.
        if (session.role === "customer") {
          window.location.replace("/my-account");
        } else {
          window.location.replace("/dashboard");
        }

        return;
      }

      allowPage();

    } catch (error) {
      console.error("AUTH GUARD ERROR:", error);
      redirectToLogin();
    }
  }

  window.authGuard = {
    check: guard
  };

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      guard,
      { once: true }
    );
  } else {
    guard();
  }
})();
