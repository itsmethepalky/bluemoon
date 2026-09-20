let recoverySessionReady = false;
let recoverySubscription = null;

function showMessage(text, type) {
  const message = document.getElementById("formMessage");

  message.textContent = text;
  message.className = `form-message ${type}`;
  message.style.display = "block";
}

function enablePasswordForm() {
  recoverySessionReady = true;

  const form = document.getElementById("updatePasswordForm");

  if (form) {
    form.style.display = "block";
  }
}

function showInvalidRecoveryLink() {
  const form = document.getElementById("updatePasswordForm");

  if (form) {
    form.style.display = "none";
  }

  showMessage(
    "This password reset link is invalid or has expired. Please request a new reset link.",
    "error"
  );
}

async function initializePasswordRecovery() {
  /*
   * Register this listener immediately.
   *
   * Supabase emits PASSWORD_RECOVERY when the reset link
   * establishes the recovery session.
   */
  const {
    data: { subscription },
  } = supabaseClient.auth.onAuthStateChange((event, session) => {
    if (event === "PASSWORD_RECOVERY" && session) {
      enablePasswordForm();
    }
  });

  recoverySubscription = subscription;

  /*
   * Also check whether the recovery session is already available.
   * This handles cases where Supabase processed the URL before
   * our listener was registered.
   */
  const { data, error } = await supabaseClient.auth.getSession();

  if (!error && data.session) {
    enablePasswordForm();
    return;
  }

  /*
   * Give Supabase a short amount of time to process the recovery
   * URL and emit PASSWORD_RECOVERY.
   */
  setTimeout(async () => {
    if (recoverySessionReady) return;

    const result = await supabaseClient.auth.getSession();

    if (result.data.session) {
      enablePasswordForm();
    } else {
      showInvalidRecoveryLink();
    }
  }, 3000);
}

document
  .getElementById("updatePasswordForm")
  .addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!recoverySessionReady) {
      showInvalidRecoveryLink();
      return;
    }

    const password = document.getElementById("password").value;
    const confirmPassword =
      document.getElementById("confirmPassword").value;

    const button = document.getElementById("updatePasswordBtn");

    if (password.length < 6) {
      showMessage(
        "Password must be at least 6 characters long.",
        "error"
      );
      return;
    }

    if (password !== confirmPassword) {
      showMessage(
        "The passwords do not match.",
        "error"
      );
      return;
    }

    button.disabled = true;
    button.textContent = "Updating…";

    try {
      const { error } =
        await supabaseClient.auth.updateUser({
          password,
        });

      if (error) {
        throw error;
      }

      showMessage(
        "Your password has been updated successfully. Redirecting to sign in…",
        "success"
      );

      document.getElementById("updatePasswordForm").style.display =
        "none";

      if (recoverySubscription) {
        recoverySubscription.unsubscribe();
        recoverySubscription = null;
      }

      await supabaseClient.auth.signOut({ scope: "local" });

      setTimeout(() => {
        window.location.href = "login.html?reset=success";
      }, 1800);
    } catch (err) {
      showMessage(
        err.message ||
          "Could not update your password. Please try again.",
        "error"
      );

      button.disabled = false;
      button.textContent = "Update password";
    }
  });

document.getElementById("updatePasswordForm").style.display = "none";

initializePasswordRecovery();
