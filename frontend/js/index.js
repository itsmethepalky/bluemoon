// Landing page authentication CTA handling.
//
// A visitor who's already signed in gets their CTA pointed straight at
// the app instead of the sign-in form. The landing page itself stays
// visible either way - this is the front door, not a redirect.

(async () => {
  const { data } = await supabaseClient.auth.getSession();

  if (!data.session) return;

  const session = await requireAuth();

  if (!session) return;

  const target =
    session.role === "customer"
      ? "/my-account"
      : "/dashboard";

  const label =
    session.role === "customer"
      ? "Go to My Account"
      : "Go to Dashboard";

  document.querySelectorAll("#navCta, #heroCta").forEach((el) => {
    el.href = target;
    el.textContent = label;
  });
})();
