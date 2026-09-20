/* ==========================================================================
   The Blue Moon frontend - Supabase Auth + API client + shared UI helpers

   AUTHENTICATION DESIGN
   ---------------------
   This version specifically prevents the common startup race where:

       Page loads
          ↓
       Supabase restores session
          ↓
       Dashboard starts API request too early
          ↓
       FastAPI sees missing/stale token
          ↓
       "Could not validate credentials"
          ↓
       2-3 seconds later everything works

   The client now:

   1. Waits for Supabase's initial session restoration.
   2. Gets the CURRENT session before authenticated API requests.
   3. Shares one session-initialization promise between all components.
   4. Shares one token-refresh promise between simultaneous requests.
   5. Retries a 401 exactly once after refreshing the token.
   6. Does not logout because of temporary backend/network failures.
   7. Keeps the application profile synchronized with the Supabase session.
   8. Avoids using a stale cached access token during startup.
   ========================================================================== */

const API_BASE = "/api";

// Public Supabase values.
// NEVER put a Supabase service-role key in frontend code.
const SUPABASE_URL =
  "https://fulnozrxrucvmvhwfipe.supabase.co";

const SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ1bG5venJ4cnVjdm12aHdmaXBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk3NDY4MTQsImV4cCI6MjEwNTMyMjgxNH0.JtKBHVOITH44aLgpCVVAT5APe6HG3gnHG26ZuRMHYko";


const supabaseClient = supabase.createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY
);


// ==========================================================================
// Authentication state
// ==========================================================================

let _authReadyPromise = null;
let _profilePromise = null;
let _resolvedSession = null;
let _refreshPromise = null;

let _initialSessionResolved = false;
let _lastAuthEvent = null;


// ==========================================================================
// Initial Supabase session restoration
// ==========================================================================

/**
 * Wait until Supabase has completed its initial auth-state restoration.
 *
 * This is the important startup protection.
 *
 * On a fresh page load, Supabase may need a short moment to restore the
 * session from local storage / cookies and process token state.
 */
function waitForInitialSession() {
  if (_authReadyPromise) {
    return _authReadyPromise;
  }

  _authReadyPromise = new Promise((resolve) => {
    let resolved = false;

    const finish = () => {
      if (resolved) return;

      resolved = true;
      _initialSessionResolved = true;

      resolve();
    };

    /*
     * Supabase normally emits INITIAL_SESSION shortly after the client
     * starts.
     */
    const timeout = setTimeout(() => {
      /*
       * Do not leave the application hanging forever if an auth event
       * somehow fails to arrive.
       *
       * getSession() below is still used as the authoritative check.
       */
      finish();
    }, 5000);

    /*
     * Store the listener temporarily.
     *
     * The normal auth listener below will also see INITIAL_SESSION.
     */
    const {
      data: { subscription },
    } = supabaseClient.auth.onAuthStateChange((event) => {
      if (event === "INITIAL_SESSION") {
        clearTimeout(timeout);

        finish();

        /*
         * This listener is only for initial startup.
         */
        setTimeout(() => {
          try {
            subscription.unsubscribe();
          } catch (_) {}
        }, 0);
      }
    });
  });

  return _authReadyPromise;
}


// ==========================================================================
// Get current Supabase session
// ==========================================================================

/**
 * Always ask Supabase for the current session.
 *
 * We deliberately do not rely only on _resolvedSession because that object
 * can contain an older access token while Supabase is refreshing it.
 */
async function getSupabaseSession() {
  try {
    /*
     * Make absolutely sure Supabase has finished startup restoration.
     */
    await waitForInitialSession();

    const {
      data,
      error,
    } = await supabaseClient.auth.getSession();

    if (error) {
      console.error(
        "Supabase getSession error:",
        error
      );

      return null;
    }

    return data?.session || null;
  } catch (err) {
    console.error(
      "Supabase getSession exception:",
      err
    );

    return null;
  }
}


// ==========================================================================
// Refresh Supabase session
// ==========================================================================

/**
 * Refresh the Supabase session.
 *
 * All simultaneous refresh attempts share the same promise.
 */
async function clearLocalAuthSession() {
  try {
    console.warn("[AUTH] Clearing stale local Supabase session...");
    await supabaseClient.auth.signOut({ scope: "local" });
  } catch (err) {
    console.error("[AUTH] Could not clear local Supabase session:", err);
  }

  _resolvedSession = null;
  _profilePromise = null;
  _refreshPromise = null;
}

async function refreshSupabaseSession() {
  if (_refreshPromise) {
    return _refreshPromise;
  }

  _refreshPromise = (async () => {
    try {
      console.log(
        "[AUTH] Refreshing Supabase session..."
      );

      const {
        data,
        error,
      } = await supabaseClient.auth.refreshSession();

      if (error) {
        console.error(
          "[AUTH] Supabase refresh failed:",
          error
        );

        return null;
      }

      if (!data?.session) {
        console.warn(
          "[AUTH] Refresh completed but returned no session."
        );

        return null;
      }

      const session = data.session;

      /*
       * Immediately synchronize our cached application session.
       */
      if (_resolvedSession) {
        _resolvedSession.access_token =
          session.access_token;

        _resolvedSession.refresh_token =
          session.refresh_token;
      }

      /*
       * The old profile bootstrap must not keep using an old token.
       */
      _profilePromise = null;

      console.log(
        "[AUTH] Supabase session refreshed successfully."
      );

      return session;
    } catch (err) {
      console.error(
        "[AUTH] Supabase refresh exception:",
        err
      );

      return null;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}


// ==========================================================================
// Build application session/profile
// ==========================================================================

async function resolveApplicationSession() {
  // Wait until Supabase restores its browser session.
  await waitForInitialSession();

  let sbSession = await getSupabaseSession();

  // No Supabase session = genuinely signed out.
  if (!sbSession) {
    _resolvedSession = null;
    return null;
  }

  try {
    let res = await fetch(`${API_BASE}/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${sbSession.access_token}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    // 401 = stale/expired token. Refresh exactly once.
    if (res.status === 401) {
      console.warn(
        "[AUTH] /api/auth/me returned 401. Trying token refresh..."
      );

      const refreshed = await refreshSupabaseSession();

      if (refreshed?.access_token) {
        sbSession = refreshed;

        res = await fetch(`${API_BASE}/auth/me`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${refreshed.access_token}`,
            Accept: "application/json",
          },
          cache: "no-store",
        });
      }
    }

    // Successful authentication.
    if (res.ok) {
      const profile = await res.json();

      _resolvedSession = {
        access_token: sbSession.access_token,
        refresh_token: sbSession.refresh_token,
        user_id: profile.id,
        role: profile.role,
        full_name: profile.full_name,
        email: profile.email,
      };

      return _resolvedSession;
    }

    // Second 401 = stale/invalid browser session.
    if (res.status === 401) {
      console.error(
        "[AUTH] Backend rejected Supabase token even after refresh."
      );

      await clearLocalAuthSession();
      return null;
    }

    // 403 = authenticated but forbidden/disabled.
    if (res.status === 403) {
      console.warn(
        "[AUTH] /api/auth/me returned 403. Keeping Supabase session."
      );

      return _resolvedSession;
    }

    // Don't log users out because of server errors.
    if (res.status >= 500) {
      console.error(
        "[AUTH] /api/auth/me server error:",
        res.status
      );

      return _resolvedSession;
    }

    console.error(
      "[AUTH] /api/auth/me failed:",
      res.status,
      res.statusText
    );

    return _resolvedSession;
  } catch (err) {
    // Network/backend problems are not logout events.
    console.error(
      "[AUTH] Could not reach /api/auth/me:",
      err
    );

    return _resolvedSession;
  }
}


function bootstrapSession() {
  if (!_profilePromise) {
    _profilePromise =
      resolveApplicationSession();
  }

  return _profilePromise;
}


/**
 * Public synchronous accessor.
 *
 * Returns the already-resolved application session.
 */
function getSession() {
  return _resolvedSession;
}

/*
 * Resolve the authenticated application session WITHOUT redirecting.
 * Login/register pages use this so a stale browser Supabase session
 * cannot force an immediate redirect back to the homepage.
 */
async function getAuthenticatedSession() {
  try {
    return await bootstrapSession();
  } catch (err) {
    console.error("[AUTH] getAuthenticatedSession failed:", err);
    return null;
  }
}


// ==========================================================================
// Require authentication
// ==========================================================================

/**
 * Call at the beginning of protected page initialization:
 *
 *     const session = await requireAuth();
 *
 * Or:
 *
 *     const session = await requireAuth(["admin"]);
 */
async function requireAuth(allowedRoles) {
  const session =
    await bootstrapSession();


  /*
   * No authenticated Supabase session.
   */
  if (!session) {
    window.location.href =
      "index.html";

    return null;
  }


  _resolvedSession = session;


  /*
   * Role restriction.
   */
  if (
    allowedRoles &&
    !allowedRoles.includes(session.role)
  ) {
    window.location.href =
      session.role === "customer"
        ? "my-account.html"
        : "dashboard.html";

    return null;
  }


  return session;
}


// ==========================================================================
// Explicit logout
// ==========================================================================

async function logout() {
  try {
    await supabaseClient.auth.signOut();
  } catch (err) {
    console.error(
      "Supabase logout error:",
      err
    );
  }

  _profilePromise = null;
  _resolvedSession = null;
  _refreshPromise = null;

  window.location.href =
    "index.html";
}


// ==========================================================================
// Supabase auth state listener
// ==========================================================================

supabaseClient.auth.onAuthStateChange(
  (event, session) => {
    _lastAuthEvent = event;

    console.log(
      "[AUTH EVENT]",
      event
    );


    switch (event) {

      // --------------------------------------------------------------------
      // Initial session
      // --------------------------------------------------------------------

      case "INITIAL_SESSION":

        _initialSessionResolved = true;

        /*
         * Do not clear anything here.
         *
         * waitForInitialSession() handles startup synchronization.
         */
        break;


      // --------------------------------------------------------------------
      // User signed in
      // --------------------------------------------------------------------

      case "SIGNED_IN":

        /*
         * A new Supabase session exists.
         *
         * The old application profile may belong to a previous session.
         */
        if (session) {
          if (_resolvedSession) {
            _resolvedSession.access_token =
              session.access_token;

            _resolvedSession.refresh_token =
              session.refresh_token;
          }

          /*
           * Re-resolve profile when necessary.
           */
          _profilePromise = null;
        }

        break;


      // --------------------------------------------------------------------
      // Token refreshed
      // --------------------------------------------------------------------

      case "TOKEN_REFRESHED":

        if (session) {

          if (_resolvedSession) {
            _resolvedSession.access_token =
              session.access_token;

            _resolvedSession.refresh_token =
              session.refresh_token;
          }

          /*
           * Do NOT immediately call /api/auth/me here.
           *
           * Supabase auth callbacks should remain lightweight.
           */
        }

        break;


      // --------------------------------------------------------------------
      // User signed out
      // --------------------------------------------------------------------

      case "SIGNED_OUT":

        _profilePromise = null;
        _resolvedSession = null;
        _refreshPromise = null;

        break;


      default:
        break;
    }
  }
);


// ==========================================================================
// API error
// ==========================================================================

class ApiError extends Error {
  constructor(message, status) {
    super(message);

    this.name = "ApiError";
    this.status = status;
  }
}


// ==========================================================================
// Get a fresh/current access token
// ==========================================================================

/**
 * Get the token that should be used RIGHT NOW.
 *
 * This is intentionally separate from getSession().
 *
 * The application profile can be cached, but the access token should always
 * come from Supabase because Supabase may have refreshed it.
 */
async function getCurrentAccessToken() {
  let session =
    await getSupabaseSession();

  if (session?.access_token) {
    /*
     * Keep application cache synchronized.
     */
    if (_resolvedSession) {
      _resolvedSession.access_token =
        session.access_token;

      _resolvedSession.refresh_token =
        session.refresh_token;
    }

    return session.access_token;
  }


  /*
   * No current session.
   *
   * Give Supabase one opportunity to refresh.
   */
  const refreshed =
    await refreshSupabaseSession();

  if (refreshed?.access_token) {
    return refreshed.access_token;
  }


  return null;
}


// ==========================================================================
// API client
// ==========================================================================

async function apiFetch(
  path,
  {
    method = "GET",
    body,
    auth = true,
    _retry = false,
  } = {}
) {

  const headers = {
    Accept:
      "application/json",
  };


  // ------------------------------------------------------------------------
  // Authentication
  // ------------------------------------------------------------------------

  if (auth) {

    /*
     * Make sure application authentication has been initialized.
     */
    await bootstrapSession();


    /*
     * bootstrapSession() has already resolved and validated the
     * application session. Reuse its current access token here.
     *
     * Token refreshes update _resolvedSession, so this avoids
     * performing another Supabase getSession() call for every
     * protected API request.
     */
    const token =
      _resolvedSession?.access_token || null;

    if (token) {
      headers.Authorization =
        `Bearer ${token}`;
    }
  }


  // ------------------------------------------------------------------------
  // Request body
  // ------------------------------------------------------------------------

  let fetchBody;

  if (body !== undefined) {
    fetchBody =
      JSON.stringify(body);

    headers["Content-Type"] =
      "application/json";
  }


  // ------------------------------------------------------------------------
  // Request
  // ------------------------------------------------------------------------

  let res;

  try {

    res = await fetch(
      `${API_BASE}${path}`,
      {
        method,
        headers,
        body: fetchBody,

        /*
         * Prevent browser caching from returning stale authenticated data.
         */
        cache: "no-store",
      }
    );

  } catch (err) {

    console.error(
      "[API] Network error:",
      err
    );

    throw new ApiError(
      "Unable to connect to the server. Please check your internet connection.",
      0
    );
  }


  // ------------------------------------------------------------------------
  // 401 -> refresh -> retry exactly once
  // ------------------------------------------------------------------------

  if (
    res.status === 401 &&
    auth &&
    !_retry
  ) {

    console.warn(
      `[API] ${method} ${path} returned 401. Refreshing session...`
    );


    const refreshed =
      await refreshSupabaseSession();


    if (refreshed?.access_token) {

      /*
       * IMPORTANT:
       *
       * Don't use the old bootstrap promise on retry.
       *
       * The refreshed Supabase session is authoritative.
       */
      return apiFetch(
        path,
        {
          method,
          body,
          auth,
          _retry: true,
        }
      );
    }


    /*
     * Refresh failed.
     *
     * Check Supabase one final time.
     */
    const current =
      await getSupabaseSession();


    if (!current) {

      /*
       * We have confirmed that the user genuinely has no session.
       */
      await logout();

      /*
       * Never allow page code to continue after logout.
       */
      return new Promise(() => {});
    }


    /*
     * Supabase still has a session.
     *
     * Therefore this is NOT automatically a logout.
     */
    throw new ApiError(
      "Your session could not be verified. Please try again.",
      401
    );
  }


  // ------------------------------------------------------------------------
  // 204 No Content
  // ------------------------------------------------------------------------

  if (res.status === 204) {
    return null;
  }


  // ------------------------------------------------------------------------
  // Parse response
  // ------------------------------------------------------------------------

  let data = null;

  const text =
    await res.text();


  if (text) {

    try {
      data =
        JSON.parse(text);

    } catch (_) {
      data = text;
    }
  }


  // ------------------------------------------------------------------------
  // Backend error
  // ------------------------------------------------------------------------

  if (!res.ok) {

    const message =
      data &&
      typeof data === "object" &&
      (
        data.detail ||
        data.message
      );


    throw new ApiError(
      typeof message === "string"
        ? message
        : message
          ? JSON.stringify(message)
          : `Request failed (${res.status})`,
      res.status
    );
  }


  return data;
}


// ==========================================================================
// Convenient API methods
// ==========================================================================

const api = {

  get: (path) =>
    apiFetch(path),

  post: (path, body) =>
    apiFetch(
      path,
      {
        method: "POST",
        body,
      }
    ),

  put: (path, body) =>
    apiFetch(
      path,
      {
        method: "PUT",
        body,
      }
    ),

  del: (path) =>
    apiFetch(
      path,
      {
        method: "DELETE",
      }
    ),
};


// ==========================================================================
// Formatting
// ==========================================================================

function money(amount) {
  const n =
    Number(amount || 0);

  return (
    "Rs. " +
    n.toLocaleString(
      "en-IN",
      {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }
    )
  );
}


function formatDate(iso) {
  const d =
    new Date(iso);

  return d.toLocaleDateString(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
    }
  );
}


function formatDateTime(iso) {
  const d =
    new Date(iso);

  return d.toLocaleString(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  );
}


// ==========================================================================
// Toasts
// ==========================================================================

function toast(
  message,
  type = "info"
) {
  let stack =
    document.querySelector(
      ".toast-stack"
    );

  if (!stack) {
    stack =
      document.createElement(
        "div"
      );

    stack.className =
      "toast-stack";

    document.body.appendChild(
      stack
    );
  }


  const el =
    document.createElement(
      "div"
    );

  el.className =
    `toast ${type}`;

  el.textContent =
    message;

  stack.appendChild(el);


  setTimeout(() => {
    el.remove();
  }, 4200);
}


function friendlyError(err) {
  toast(
    err instanceof Error
      ? err.message
      : String(err),
    "error"
  );
}


// ==========================================================================
// Modals
// ==========================================================================

function openModal(id) {
  document
    .getElementById(id)
    ?.classList.add("open");
}


function closeModal(id) {
  document
    .getElementById(id)
    ?.classList.remove("open");
}


function wireModals() {

  document
    .querySelectorAll(
      "[data-close]"
    )
    .forEach((btn) => {

      btn.addEventListener(
        "click",
        () => {

          closeModal(
            btn.getAttribute(
              "data-close"
            )
          );

        }
      );

    });


  document
    .querySelectorAll(
      ".modal-backdrop"
    )
    .forEach((backdrop) => {

      backdrop.addEventListener(
        "click",
        (e) => {

          if (
            e.target === backdrop
          ) {
            backdrop.classList.remove(
              "open"
            );
          }

        }
      );

    });
}


// ==========================================================================
// Shared page chrome
// ==========================================================================

async function initChrome() {

  wireModals();


  // ------------------------------------------------------------------------
  // Logout buttons
  // ------------------------------------------------------------------------

  document
    .querySelectorAll(
      "[data-logout]"
    )
    .forEach((btn) => {

      btn.addEventListener(
        "click",
        logout
      );

    });


  // ------------------------------------------------------------------------
  // Responsive sidebar
  // ------------------------------------------------------------------------

  const toggle = document.querySelector(".menu-toggle");
  const sidebar = document.querySelector(".sidebar");
  const backdrop = document.querySelector(".sidebar-backdrop");
  const shell = document.querySelector(".app-shell");

  if (toggle && sidebar) {
    toggle.addEventListener("click", () => {
      const isDesktop = window.matchMedia("(min-width: 701px)").matches;

      if (isDesktop) {
        // Desktop: hide/show the sidebar and expand/shrink content.
        sidebar.classList.toggle("collapsed");

        const desktopCollapsed = sidebar.classList.contains("collapsed");

        shell?.classList.toggle(
          "sidebar-collapsed",
          desktopCollapsed
        );

        if (desktopCollapsed) {
          localStorage.setItem(
            "bookbridge_desktop_sidebar_collapsed",
            "1"
          );
        } else {
          localStorage.removeItem(
            "bookbridge_desktop_sidebar_collapsed"
          );
        }

        // Make sure mobile-only state does not interfere.
        sidebar.classList.remove("open");
        backdrop?.classList.remove("open");

      } else {
        // Mobile: slide the sidebar in/out with backdrop.
        sidebar.classList.toggle("open");
        backdrop?.classList.toggle("open");
      }
    });
  }

  backdrop?.addEventListener("click", () => {
    sidebar?.classList.remove("open");
    backdrop?.classList.remove("open");
  });

  // Reset desktop/mobile state when crossing the breakpoint.
  window.addEventListener("resize", () => {
    const isDesktop = window.matchMedia("(min-width: 701px)").matches;

    if (isDesktop) {
      sidebar?.classList.remove("open");
      backdrop?.classList.remove("open");
    } else {
      sidebar?.classList.remove("collapsed");
      shell?.classList.remove("sidebar-collapsed");
    }
  });

  // ------------------------------------------------------------------------
  // Keep desktop sidebar state when navigating between sections
  // ------------------------------------------------------------------------

  const sidebarNavLinks = document.querySelectorAll(".sidebar a[href]");

  sidebarNavLinks.forEach((link) => {
    link.addEventListener("click", () => {
      const isDesktop = window.matchMedia("(min-width: 701px)").matches;

      if (isDesktop && sidebar) {
        sidebar.classList.add("collapsed");
        shell?.classList.add("sidebar-collapsed");

        // Keep the sidebar collapsed after the new page loads.
        localStorage.setItem("bookbridge_desktop_sidebar_collapsed", "1");
      }
    });
  });

  // Restore the desktop sidebar state after page navigation.
  if (
    window.matchMedia("(min-width: 701px)").matches &&
    localStorage.getItem("bookbridge_desktop_sidebar_collapsed") === "1"
  ) {
    sidebar?.classList.add("collapsed");
    shell?.classList.add("sidebar-collapsed");
  }

  // ------------------------------------------------------------------------
  // Session-dependent chrome
  // ------------------------------------------------------------------------

  const session =
    await bootstrapSession();


  if (!session) {
    return;
  }


  _resolvedSession =
    session;


  // ------------------------------------------------------------------------
  // User name
  // ------------------------------------------------------------------------

  const whoEl =
    document.querySelector(
      "[data-who]"
    );


  if (whoEl) {

    whoEl.textContent =
      session.full_name ||
      session.email ||
      "";

  }


  // ------------------------------------------------------------------------
  // User role
  // ------------------------------------------------------------------------

  const roleEl =
    document.querySelector(
      "[data-role]"
    );


  if (roleEl) {

    roleEl.textContent =
      session.role ||
      "";

  }


  // ------------------------------------------------------------------------
  // Role-based navigation
  // ------------------------------------------------------------------------

  document
    .querySelectorAll(
      "[data-roles]"
    )
    .forEach((el) => {

      const allowed =
        el
          .getAttribute(
            "data-roles"
          )
          .split(",")
          .map(
            (role) =>
              role.trim()
          )
          .filter(Boolean);


      if (
        allowed.length &&
        !allowed.includes(
          session.role
        )
      ) {
        el.remove();
      }

    });
}


// ==========================================================================
// Global initialization
// ==========================================================================

document.addEventListener(
  "DOMContentLoaded",
  () => {

    initChrome()
      .catch((err) => {

        console.error(
          "initChrome error:",
          err
        );

      });

  }
);
window.getAuthenticatedSession = getAuthenticatedSession;
window.clearLocalAuthSession = clearLocalAuthSession;
