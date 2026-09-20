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


def check_url(url: str) -> str:
    """Catch the two usual mistakes when pasting a connection string, with a message that says what to fix."""
    if not url:
        raise SystemExit("There is no database URL. Set DATABASE_URL, or pass one with --to.")
    if "<" in url or ">" in url or "[YOUR" in url.upper() or "PASSWORD]" in url.upper():
        raise SystemExit(
            "The database URL still has a placeholder in it (something in < > or [ ]). "
            "Copy the real string from Supabase (Connect button) and replace only the password."
        )
    if url.startswith("postgres") and url.split("://", 1)[1].count("@") > 1:
        raise SystemExit(
            "The database URL has more than one @. If your password contains @, # / : or ?, write it URL-encoded "
            "(@ becomes %40, # becomes %23, / becomes %2F, : becomes %3A, ? becomes %3F)."
        )
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
