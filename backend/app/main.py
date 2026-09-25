import os

IS_PRODUCTION = os.getenv("ENVIRONMENT", "").lower() == "production"
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .database import engine
from .routers import (
    auth,
    users,
    categories,
    brands,
    products,
    suppliers,
    purchases,
    customers,
    sales,
    returns,
    reports,
    store,
    product_images,
)


app = FastAPI(
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",

    title="The Blue Moon API",
    description="Small Business Management & Point-of-Sale System (Supabase-backed)",
    version="2.0.0",
)


@app.on_event("startup")
def check_database_connection():
    """Verify that the configured Supabase Postgres database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Could not connect to the Supabase Postgres database. Check DATABASE_URL "
            "in backend/.env (Dashboard > Project Settings > Database > Connection string)."
        ) from exc


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
#
# Production frontend is served by this same FastAPI process, so it does not
# need wildcard cross-origin access.
#
# Local development is still supported from common localhost/127.0.0.1 ports.
#
# If you later host the frontend on another trusted domain, add that exact
# origin here instead of using "*".
#
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)

    # HTTPS is enforced by Render in production.
    # One year is a standard HSTS duration.
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )

    # Prevent clickjacking by allowing this application to frame only itself.
    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    # Prevent browsers from MIME-sniffing responses.
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Reduce information sent in the Referer header.
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Restrict browser features that this application does not need.
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    # Basic CSP compatible with the current frontend:
    # - Google Fonts
    # - jsDelivr (Supabase JS, Bootstrap Icons, Chart.js)
    # - Supabase API/auth
    # - same-origin API/frontend
    #
    # Inline JavaScript is not allowed by this CSP.
    # Existing inline styles remain allowed for the current frontend.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'; "
        "object-src 'none'; "
        "script-src 'self' https://cdn.jsdelivr.net https://challenges.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https:; "
        "frame-src 'self' https://challenges.cloudflare.com; "
        "connect-src 'self' https://*.supabase.co https://challenges.cloudflare.com; "
    )

    return response


# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------

for router in (
    auth.router,
    users.router,
    categories.router,
    brands.router,
    products.router,
    suppliers.router,
    purchases.router,
    customers.router,
    sales.router,
    returns.router,
    reports.router,
    store.router,
    product_images.router,
):
    app.include_router(router)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "The Blue Moon API"}


# ---------------------------------------------------------------------------
# Frontend pages
# ---------------------------------------------------------------------------
#
# Clean URLs:
# /                -> index.html
# /login           -> login.html
# /dashboard       -> dashboard.html
# /products        -> products.html
# etc.
#
# Static assets such as /css/* and /js/* are still served normally.
#
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def serve_page(filename: str):
    return FileResponse(FRONTEND_DIR / filename)


@app.get("/", include_in_schema=False)
def frontend_home():
    return serve_page("index.html")


@app.get("/login", include_in_schema=False)
def login_page():
    return serve_page("login.html")


@app.get("/register", include_in_schema=False)
def register_page():
    return serve_page("register.html")


@app.get("/forgot-password", include_in_schema=False)
def forgot_password_page():
    return serve_page("forgot-password.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    return serve_page("dashboard.html")


@app.get("/products", include_in_schema=False)
def products_page():
    return serve_page("products.html")


@app.get("/suppliers", include_in_schema=False)
def suppliers_page():
    return serve_page("suppliers.html")


@app.get("/customers", include_in_schema=False)
def customers_page():
    return serve_page("customers.html")


@app.get("/purchases", include_in_schema=False)
def purchases_page():
    return serve_page("purchases.html")


@app.get("/pos", include_in_schema=False)
def pos_page():
    return serve_page("pos.html")


@app.get("/sales-history", include_in_schema=False)
def sales_history_page():
    return serve_page("sales-history.html")


@app.get("/reports", include_in_schema=False)
def reports_page():
    return serve_page("reports.html")


@app.get("/users", include_in_schema=False)
def users_page():
    return serve_page("users.html")


@app.get("/my-account", include_in_schema=False)
def my_account_page():
    return serve_page("my-account.html")


@app.get("/update-password", include_in_schema=False)
def update_password_page():
    return serve_page("update-password.html")


@app.get("/privacy", include_in_schema=False)
def privacy_page():
    return serve_page("privacy.html")



# ---------------------------------------------------------------------------
# Legacy .html URL redirects
# ---------------------------------------------------------------------------
#
# Keep old bookmarks/links working while ensuring the browser uses clean URLs.
#

LEGACY_PAGE_REDIRECTS = {
    "/index.html": "/",
    "/login.html": "/login",
    "/register.html": "/register",
    "/forgot-password.html": "/forgot-password",
    "/dashboard.html": "/dashboard",
    "/products.html": "/products",
    "/suppliers.html": "/suppliers",
    "/customers.html": "/customers",
    "/purchases.html": "/purchases",
    "/pos.html": "/pos",
    "/sales-history.html": "/sales-history",
    "/reports.html": "/reports",
    "/users.html": "/users",
    "/my-account.html": "/my-account",
    "/update-password.html": "/update-password",
    "/privacy.html": "/privacy",
}


def redirect_legacy_page(path: str):
    return RedirectResponse(
        url=LEGACY_PAGE_REDIRECTS[path],
        status_code=301,
    )


for legacy_path in LEGACY_PAGE_REDIRECTS:
    app.add_api_route(
        legacy_path,
        lambda legacy_path=legacy_path: redirect_legacy_page(legacy_path),
        methods=["GET"],
        include_in_schema=False,
    )


# Static assets
app.mount(
    "/css",
    StaticFiles(directory=str(FRONTEND_DIR / "css")),
    name="frontend-css",
)

app.mount(
    "/js",
    StaticFiles(directory=str(FRONTEND_DIR / "js")),
    name="frontend-js",
)
