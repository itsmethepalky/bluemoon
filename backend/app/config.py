"""
Central configuration for The Blue Moon backend.

All values can be overridden with environment variables (see .env.example).
Copy .env.example to .env and edit it - python-dotenv loads it automatically.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Database (Supabase Postgres) -----------------------------------
    # Get this from Supabase Dashboard > Project Settings > Database >
    # Connection string ("Transaction pooler" or "Session pooler" both
    # work; use the URI with your database password filled in). Example:
    #   postgresql+psycopg2://postgres.xxxx:PASSWORD@aws-0-region.pooler.supabase.com:5432/postgres
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # --- Supabase Auth ----------------------------------------------------
    # Dashboard > Project Settings > API
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    # SECRET - service_role key. Only ever used server-side (admin user
    # management). Never send this to the frontend.
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # --- App -----------------------------------------------------------
    APP_NAME: str = "The Blue Moon"
    # Currency symbol used only for seed data / receipts formatting on the backend side
    CURRENCY: str = os.getenv("CURRENCY", "Rs.")

    # Low stock default threshold used when a product doesn't set its own reorder_level
    DEFAULT_REORDER_LEVEL: int = 5


settings = Settings()
