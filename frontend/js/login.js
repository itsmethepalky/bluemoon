// If already signed in, skip straight into the app.
(async () => {
  const { data } = await supabaseClient.auth.getSession();

  if (data.session) {
    await goToApp();
  }
})();

async function goToApp() {
  // IMPORTANT:
  // Do not use requireAuth() here.
  // requireAuth() redirects unauthenticated users to index.html.
  // A stale Supabase session in a normal browser can therefore cause
  // an immediate login-page -> homepage redirect.

  const session = await window.getAuthenticatedSession();

  if (!session) {
    return;
  }

  window.location.href =
    session.role === "customer"
      ? "my-account.html"
      : "dashboard.html";
}

async function waitForTurnstile() {
  for (let i = 0; i < 100; i += 1) {
    if (window.turnstile) return true;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return false;
}

let loginTurnstileWidgetId = null;

async function initializeLoginTurnstile() {
  const ready = await waitForTurnstile();
  if (!ready) return;

  const container = document.getElementById("loginTurnstile");
  if (!container || loginTurnstileWidgetId !== null) return;

  loginTurnstileWidgetId = window.turnstile.render(container, {
    sitekey: container.dataset.sitekey,
    theme: "auto",
  });
}

initializeLoginTurnstile();

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const errorBox = document.getElementById("loginError");
  const btn = document.getElementById("loginBtn");

  errorBox.style.display = "none";
  btn.disabled = true;
  btn.textContent = "Signing in…";

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  try {
    const ready = await waitForTurnstile();

    if (!ready || loginTurnstileWidgetId === null) {
      throw new Error("Security verification is still loading. Please try again.");
    }

    const captchaToken = window.turnstile.getResponse(loginTurnstileWidgetId);

    if (!captchaToken) {
      throw new Error("Please complete the security verification.");
    }

    const { error } = await supabaseClient.auth.signInWithPassword({
      email,
      password,
      options: {
        captchaToken,
      },
    });

    if (error) throw error;

    await goToApp();
  } catch (err) {
    errorBox.textContent =
      err.message || "Sign in failed. Please try again.";
    errorBox.style.display = "block";

    if (loginTurnstileWidgetId !== null && window.turnstile) {
      window.turnstile.reset(loginTurnstileWidgetId);
    }
  } finally {
    btn.disabled = false;
    btn.textContent = "Sign in";
  }
});

