document.getElementById("registerForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const errorBox = document.getElementById("formError");
  const btn = document.getElementById("registerBtn");

  errorBox.style.display = "none";
  btn.disabled = true;
  btn.textContent = "Creating account…";

  const fullName =
    document.getElementById("fullName").value.trim();

  const email =
    document.getElementById("email").value.trim();

  const phone =
    document.getElementById("phone").value.trim();

  const address =
    document.getElementById("address").value.trim();

  const password =
    document.getElementById("password").value;

  try {
    // user_metadata is read by the on_auth_user_created DB trigger,
    // which creates the matching profiles + customers rows automatically.
    // The role defaults to "customer" when not specified.

    const { data, error } =
      await supabaseClient.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
            phone: phone || null,
            address: address || null,
          },
        },
      });

    if (error) throw error;

    if (data.session) {
      // Confirm email is off for this project - signed in immediately.
      window.location.href = "index.html";
    } else {
      // Confirm email is on - Supabase emailed a confirmation link.
      document.getElementById("registerForm").style.display = "none";

      errorBox.style.display = "block";
      errorBox.style.color = "var(--text-primary)";

      errorBox.textContent =
        "Account created! Check " +
        email +
        " for a confirmation link, then sign in.";
    }
  } catch (err) {
    errorBox.textContent =
      err.message ||
      "Could not create your account. Please try again.";

    errorBox.style.display = "block";
  } finally {
    btn.disabled = false;
    btn.textContent = "Create account";
  }
});
