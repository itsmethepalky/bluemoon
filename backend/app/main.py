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
    """Tables/RLS/triggers already live in Supabase (see database/migrations/).
    This just fails fast with a clear error if DATABASE_URL is wrong, rather
    than surfacing a confusing error on the first real request."""
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Could not connect to the Supabase Postgres database. Check DATABASE_URL "
            "in backend/.env (Dashboard > Project Settings > Database > Connection string)."
        ) from exc

# Wide-open CORS for local development (e.g. serving the frontend from a
# different port/tool such as VS Code Live Server). Tighten this for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# Serve the static frontend (HTML/CSS/JS) from the sibling `frontend/` folder,
# so the whole app runs from a single `uvicorn` process: http://127.0.0.1:8000/
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
