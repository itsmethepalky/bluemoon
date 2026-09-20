from pathlib import Path

from fastapi import FastAPI
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
)


app = FastAPI(
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
    # 'unsafe-inline' is currently required because several existing HTML
    # pages contain inline scripts/styles. We can tighten this later by
    # migrating those inline blocks to external files/nonces.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'; "
        "object-src 'none'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https://*.supabase.co; "
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
):
    app.include_router(router)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "The Blue Moon API"}


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------
#
# The frontend lives beside backend/:
#
# the-blue-moon/
# ├── backend/
# └── frontend/
#
# This lets the same FastAPI process serve the production UI.
#
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
    )
