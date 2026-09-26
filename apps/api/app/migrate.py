"""Adds columns that newer versions of the models need to a database created by an older one.

There is no migration tool yet (see the README). `create_all` makes missing tables but never adds a
column to an existing table, so the few columns added since the first release are listed here and
added on startup when they are missing. Safe to run every time.
"""

from sqlalchemy import Engine, inspect, text

from app.models import Base

ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("roles", "mba", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("companies", "mba", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("capabilities", "mba", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "name", "VARCHAR(120)"),
    ("companies", "website", "VARCHAR"),
]


def add_missing_columns(engine: Engine) -> list[str]:
    added = []
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in ADDED_COLUMNS:
            if not inspector.has_table(table):
                continue
            if column not in {c["name"] for c in inspector.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                added.append(f"{table}.{column}")
    return added


def rls_statements() -> list[str]:
    """Row level security on every table, with no policies.

    Supabase publishes the tables of the `public` schema through its own REST API, and a table without
    row level security can be read and changed by anyone holding the project's public "anon" key. Vantage
    only ever reaches the database through its own API, as the `postgres` role, which is not affected.
    Turning this on closes the other door.
    """
    return [f'ALTER TABLE "{t.name}" ENABLE ROW LEVEL SECURITY' for t in Base.metadata.sorted_tables]


def secure_postgres(engine: Engine) -> int:
    """Apply rls_statements to a Postgres database. Does nothing on SQLite. Safe to repeat."""
    if engine.dialect.name != "postgresql":
        return 0
    statements = rls_statements()
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    return len(statements)


if __name__ == "__main__":
    # `python -m app.migrate` creates any missing tables and columns. Run it once against a new database,
    # or set VANTAGE_SKIP_DDL=1 on a serverless host, where doing it on every cold start would be slow.
    from sqlalchemy.exc import OperationalError

    from app.db import DATABASE_URL, check_url, engine

    check_url(DATABASE_URL)
    try:
        Base.metadata.create_all(engine)
    except OperationalError as exc:
        raise SystemExit(f"Could not use the database: {str(exc.orig or exc).splitlines()[0]}")
    print("Tables ready. Added columns:", add_missing_columns(engine) or "none")
    print("Row level security enabled on", secure_postgres(engine), "tables")
