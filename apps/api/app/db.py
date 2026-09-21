import os
import re
import sys
from urllib.parse import quote, unquote

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


def _encode_password(rest: str) -> str:
    """A password with a raw @ in it splits the address in the wrong place. The real separator is the last @, so
    everything before it is the user and password, and the password is written out safely."""
    at = rest.rfind("@")
    userinfo = rest[:at] if at > 0 else ""
    if "@" not in userinfo or ":" not in userinfo:
        return rest
    user, _, password = userinfo.partition(":")
    return f"{user}:{quote(unquote(password), safe='')}{rest[at:]}"


def normalize_url(url: str) -> str:
    """Accept the URLs hosts hand out (postgres://, postgresql://) and use the psycopg 3 driver."""
    for old in ("postgres://", "postgresql://"):
        if url.startswith(old):
            return "postgresql+psycopg://" + _encode_password(url[len(old):])
    return url


_DIRECT_HOST = re.compile(r"@db\.[a-z0-9]+\.supabase\.co(?::\d+)?/", re.IGNORECASE)


def connection_problem(url: str) -> str | None:
    """A plain-language warning when the address is one that can't work from a serverless host, or None."""
    if _DIRECT_HOST.search(url):
        return (
            "DATABASE_URL is Supabase's direct connection address (db.<project>.supabase.co). It only works over IPv6, which "
            "Vercel does not have. Use the Transaction pooler string instead: host aws-0-<region>.pooler.supabase.com, port 6543, "
            "user postgres.<project>. python -m app.vercel_env writes the right one."
        )
    return None


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
if SERVERLESS and (_problem := connection_problem(DATABASE_URL)):
    print(f"[vantage] {_problem}", file=sys.stderr)  # shows up in the host's logs, never in a response


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
