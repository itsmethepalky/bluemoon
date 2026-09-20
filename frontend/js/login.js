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
    const { error } =
      await supabaseClient.auth.signInWithPassword({
        email,
        password,
      });

    if (error) throw error;

    await goToApp();
  } catch (err) {
    errorBox.textContent =
      err.message || "Sign in failed. Please try again.";

    errorBox.style.display = "block";
  } finally {
    btn.disabled = false;
    btn.textContent = "Sign in";
  }
});
