import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


def normalize_url(url: str) -> str:
    """Accept the URLs hosts hand out (postgres://, postgresql://) and use the psycopg 3 driver."""
    for old in ("postgres://", "postgresql://"):
        if url.startswith(old):
            return "postgresql+psycopg://" + url[len(old):]
    return url


DATABASE_URL = normalize_url(os.getenv("DATABASE_URL") or "sqlite:///./vantage.db")  # empty counts as unset
# Vercel runs each request in short-lived functions, so a pool of open connections only wastes them.
SERVERLESS = bool(os.getenv("VERCEL"))


def engine_options(url: str, serverless: bool) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # prepare_threshold=None: Supabase's pooler (port 6543) cannot keep prepared statements between calls.
    options: dict = {"pool_pre_ping": True, "connect_args": {"prepare_threshold": None}}
    if serverless:
        options["poolclass"] = NullPool
    else:
        options.update(pool_size=5, max_overflow=5, pool_recycle=1800)
    return options


engine = create_engine(DATABASE_URL, **engine_options(DATABASE_URL, SERVERLESS))
SessionLocal = sessionmaker(bind=engine, autoflush=False)
