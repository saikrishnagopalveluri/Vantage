"""Copy the taxonomy and news from one database to another, for example the local SQLite file into Supabase.

    python -m app.copy_db --to "postgresql://postgres:...@db.xxxx.supabase.co:5432/postgres"

By default people are left behind: accounts, profiles, saved stories, job descriptions and consent
records stay in the source, so a local test user never reaches production. Add --include-users to move
them too. The target must be empty unless --replace is given.
"""

import argparse
import sys

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import Engine

from app.db import DATABASE_URL, engine_options, normalize_url
from app.migrate import secure_postgres
from app.models import Article, ArticleTag, Base, Source

CHUNK = 2000


def personal_tables() -> set[str]:
    """Every table that holds something about a person, found from the schema so a new one is not missed."""
    names = {t.name for t in Base.metadata.sorted_tables if "user_id" in t.c}
    return names | {"users", "jd_capabilities", "ingest_runs"}


def copy_database(source: Engine, target: Engine, *, include_users: bool = False, replace: bool = False, log=print) -> dict[str, int]:
    skip = set() if include_users else personal_tables()
    tables = [t for t in Base.metadata.sorted_tables if t.name not in skip]
    Base.metadata.create_all(target)

    with target.begin() as tgt:
        if replace:
            for table in reversed(tables):
                tgt.execute(delete(table))
        else:
            busy = [t.name for t in tables if tgt.execute(select(func.count()).select_from(t)).scalar()]
            if busy:
                raise SystemExit(f"The target already has data in: {', '.join(busy)}. Use --replace to overwrite it.")

        copied: dict[str, int] = {}
        placeholder = select(Source.id).where(Source.name.like("%(placeholder)"))
        with source.connect() as src:
            for table in tables:
                total = 0
                rows = src.execute(select(table)).mappings()
                while chunk := [dict(r) for r in rows.fetchmany(CHUNK)]:
                    tgt.execute(table.insert(), chunk)
                    total += len(chunk)
                copied[table.name] = total
                log(f"  {table.name}: {total}")

        if not include_users:
            # The [Sample] stories are for demos and browser tests; a real database never carries them.
            gone = select(Article.id).where(Article.source_id.in_(placeholder))
            tgt.execute(delete(ArticleTag).where(ArticleTag.article_id.in_(gone)))
            tgt.execute(delete(Article).where(Article.source_id.in_(placeholder)))
            tgt.execute(delete(Source).where(Source.name.like("%(placeholder)")))
    return copied


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", default=DATABASE_URL, help="source database URL (default: DATABASE_URL, the local SQLite file)")
    parser.add_argument("--to", dest="target", required=True, help="target database URL, such as your Supabase connection string")
    parser.add_argument("--include-users", action="store_true", help="also copy accounts, profiles and everything personal")
    parser.add_argument("--replace", action="store_true", help="empty the target tables first")
    args = parser.parse_args(argv)

    source_url, target_url = normalize_url(args.source), normalize_url(args.target)
    if source_url == target_url:
        raise SystemExit("The source and the target are the same database.")
    source = create_engine(source_url, **engine_options(source_url, False))
    target = create_engine(target_url, **engine_options(target_url, False))
    print(f"Copying {source.url.render_as_string(hide_password=True)} -> {target.url.render_as_string(hide_password=True)}")
    copied = copy_database(source, target, include_users=args.include_users, replace=args.replace)
    print(f"Done: {sum(copied.values()):,} rows in {len(copied)} tables.")
    print(f"Row level security enabled on {secure_postgres(target)} tables.")


if __name__ == "__main__":
    main(sys.argv[1:])
