from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from .config import settings


DATABASE_URL = settings.DATABASE_URL

# Supabase Transaction Pooler normally uses port 6543.
# Render uses the transaction pooler, while local development
# can continue using the normal/direct Postgres connection.
IS_TRANSACTION_POOLER = ":6543" in DATABASE_URL


if IS_TRANSACTION_POOLER:
    # Supabase Transaction Pooling / PgBouncer.
    # Let Supabase/PgBouncer manage connection pooling instead
    # of maintaining a second SQLAlchemy connection pool.
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
else:
    # Local/direct Postgres connection.
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
