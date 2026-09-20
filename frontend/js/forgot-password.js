let forgotPasswordTurnstileWidgetId = null;
let turnstileReadyPromise = null;

function waitForTurnstile() {
  if (turnstileReadyPromise) {
    return turnstileReadyPromise;
  }

  turnstileReadyPromise = new Promise((resolve, reject) => {
    const started = Date.now();

    const check = () => {
      if (
        window.turnstile &&
        typeof window.turnstile.render === "function"
      ) {
        resolve(true);
        return;
      }

      if (Date.now() - started >= 15000) {
        reject(
          new Error(
            "Security verification could not load. Please refresh the page and try again."
          )
        );
        return;
      }

      setTimeout(check, 100);
    };

    check();
  });

  return turnstileReadyPromise;
}

async function initializeForgotPasswordTurnstile() {
  const container = document.getElementById(
    "forgotPasswordTurnstile"
  );

  if (!container) {
    return;
  }

  try {
    await waitForTurnstile();

    if (forgotPasswordTurnstileWidgetId !== null) {
      return;
    }

    forgotPasswordTurnstileWidgetId =
      window.turnstile.render(container, {
        sitekey: container.dataset.sitekey,
        theme: container.dataset.theme || "auto",
      });
  } catch (err) {
    console.error(
      "[TURNSTILE] Failed to initialize:",
      err
    );

    const message =
      document.getElementById("formMessage");

    if (message) {
      message.className = "login-error";
      message.style.display = "block";
      message.textContent =
        "Security verification could not load. Please refresh the page and try again.";
    }
  }
}

document
  .getElementById("forgotPasswordForm")
  .addEventListener("submit", async (event) => {
    event.preventDefault();

    const form =
      document.getElementById("forgotPasswordForm");

    const email =
      document.getElementById("email").value.trim();

    const message =
      document.getElementById("formMessage");

    const button =
      document.getElementById("resetBtn");

    message.style.display = "none";
    message.className = "login-error";

    if (!email) {
      message.textContent =
        "Please enter your email address.";
      message.style.display = "block";
      return;
    }

    button.disabled = true;
    button.textContent = "Sending…";

    try {
      await waitForTurnstile();

      if (forgotPasswordTurnstileWidgetId === null) {
        throw new Error(
          "Security verification is still loading. Please try again."
        );
      }

      const captchaToken =
        window.turnstile.getResponse(
          forgotPasswordTurnstileWidgetId
        );

      if (!captchaToken) {
        throw new Error(
          "Please complete the security verification."
        );
      }

      const redirectTo =
        `${window.location.origin}/update-password.html`;

      const { error } =
        await supabaseClient.auth.resetPasswordForEmail(
          email,
          {
            redirectTo,
            captchaToken,
          }
        );

      if (error) {
        throw error;
      }

      message.className = "login-error";
      message.style.display = "block";
      message.textContent =
        "If an account exists for that email, a password reset link has been sent. Please check your inbox and spam folder.";

      form.reset();

      if (
        forgotPasswordTurnstileWidgetId !== null &&
        window.turnstile
      ) {
        window.turnstile.reset(
          forgotPasswordTurnstileWidgetId
        );
      }
    } catch (err) {
      console.error(
        "[PASSWORD RESET]",
        err
      );

      message.className = "login-error";
      message.style.display = "block";
      message.textContent =
        err.message ||
        "Could not send the reset link. Please try again.";

      if (
        forgotPasswordTurnstileWidgetId !== null &&
        window.turnstile
      ) {
        window.turnstile.reset(
          forgotPasswordTurnstileWidgetId
        );
      }
    } finally {
      button.disabled = false;
      button.textContent = "Send reset link";
    }
  });

initializeForgotPasswordTurnstile();
