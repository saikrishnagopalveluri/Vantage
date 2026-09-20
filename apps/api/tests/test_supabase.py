import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateIndex, CreateTable

from app.copy_db import copy_database, personal_tables
from app.db import engine_options, normalize_url
from app.migrate import rls_statements, secure_postgres
from app.models import Account, Base, Capability, Company, Consent, Role, User, UserProfile

API_DIR = Path(__file__).resolve().parents[1]


def test_host_urls_are_turned_into_psycopg_urls():
    assert normalize_url("postgres://u:p@h:6543/postgres") == "postgresql+psycopg://u:p@h:6543/postgres"
    assert normalize_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_url("sqlite:///./vantage.db") == "sqlite:///./vantage.db"


def test_engine_options_suit_each_place_it_runs():
    assert engine_options("sqlite:///x.db", False) == {"connect_args": {"check_same_thread": False}}
    server = engine_options("postgresql+psycopg://u:p@h/db", False)
    assert server["pool_size"] == 5 and server["connect_args"] == {"prepare_threshold": None}  # pooler safe
    serverless = engine_options("postgresql+psycopg://u:p@h/db", True)
    assert serverless["poolclass"] is NullPool and "pool_size" not in serverless


def test_every_table_and_index_can_be_created_on_postgres():
    dialect = postgresql.dialect()
    for table in Base.metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=dialect)).startswith("\nCREATE TABLE")
        for index in table.indexes:
            str(CreateIndex(index).compile(dialect=dialect))
    ddl = str(CreateTable(Base.metadata.tables["roles"]).compile(dialect=dialect))
    assert "mba BOOLEAN" in ddl and "aliases JSON" in ddl and "PRIMARY KEY (id)" in ddl


def test_row_level_security_covers_every_table_and_only_runs_on_postgres(tmp_path):
    statements = rls_statements()
    assert len(statements) == len(Base.metadata.sorted_tables)
    assert 'ALTER TABLE "accounts" ENABLE ROW LEVEL SECURITY' in statements
    assert secure_postgres(create_engine(f"sqlite:///{tmp_path / 'x.db'}")) == 0


def make_source(path):
    engine = create_engine(f"sqlite:///{path}", **engine_options("sqlite:///", False))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(title="Brand Manager", mba=True), Company(name="HUL", mba=True), Capability(name="Excel", kind="tool")])
        db.add_all([User(id="u1"), UserProfile(user_id="u1"), Account(user_id="u1", email="a@example.com", password_hash="x")])
        db.add(Consent(user_id="u1", terms_version="v", privacy_version="v", over_18=True, source="signup"))
        db.commit()
    return engine


def count(engine, model):
    with Session(engine) as db:
        return db.scalar(select(func.count()).select_from(model))


def test_the_copy_moves_the_taxonomy_and_leaves_people_behind(tmp_path):
    source = make_source(tmp_path / "src.db")
    target = create_engine(f"sqlite:///{tmp_path / 'dst.db'}")
    copied = copy_database(source, target, log=lambda *_: None)
    assert copied["roles"] == 1 and copied["companies"] == 1 and copied["capabilities"] == 1
    assert count(target, Role) == 1
    for table in ("users", "accounts", "consents", "user_profiles"):
        assert table not in copied
    assert count(target, User) == 0 and count(target, Account) == 0 and count(target, Consent) == 0
    with Session(target) as db:
        assert db.scalars(select(Role.mba)).one() is True  # values survive the trip


def test_the_copy_can_include_people_and_refuses_a_target_that_has_data(tmp_path):
    source = make_source(tmp_path / "src.db")
    target = create_engine(f"sqlite:///{tmp_path / 'dst.db'}")
    copy_database(source, target, include_users=True, log=lambda *_: None)
    assert count(target, Account) == 1 and count(target, Consent) == 1
    with pytest.raises(SystemExit, match="already has data"):
        copy_database(source, target, log=lambda *_: None)
    copy_database(source, target, include_users=True, replace=True, log=lambda *_: None)
    assert count(target, Role) == 1


def test_personal_tables_are_found_from_the_schema():
    names = personal_tables()
    assert {"users", "accounts", "consents", "user_profiles", "user_interactions", "jds", "jd_capabilities", "profile_events"} <= names
    assert "roles" not in names and "articles" not in names


def test_the_vercel_entry_point_serves_the_app_and_the_config_routes_everything_to_it():
    from index import app

    assert any(getattr(route, "path", "") == "/health" for route in app.routes)
    config = json.loads((API_DIR / "vercel.json").read_text(encoding="utf-8"))
    assert config["builds"][0]["src"] == "index.py" and config["routes"] == [{"src": "/(.*)", "dest": "index.py"}]
    assert "psycopg" in (API_DIR / "requirements.txt").read_text(encoding="utf-8")


def test_demo_stories_are_not_copied_to_a_real_database(tmp_path):
    from datetime import datetime, timezone

    from app.models import Article, ArticleTag, Source

    source = make_source(tmp_path / "src.db")
    with Session(source) as db:
        demo = Source(name="Vantage Samples (placeholder)", feed_url="sample://x", authority=1)
        real = Source(name="Mint - Companies", feed_url="https://x.test/rss", authority=4)
        db.add_all([demo, real])
        db.flush()
        for src, title in ((demo, "[Sample] a"), (real, "A real story")):
            db.add(Article(source_id=src.id, title=title, url=f"https://x.test/{title}", published_at=datetime.now(timezone.utc)))
        db.flush()
        db.add(ArticleTag(article_id=db.scalars(select(Article.id).where(Article.title == "[Sample] a")).one(), tag_type="topic", ref_id="t"))
        db.commit()
    target = create_engine(f"sqlite:///{tmp_path / 'dst.db'}")
    copy_database(source, target, log=lambda *_: None)
    with Session(target) as db:
        assert [a.title for a in db.scalars(select(Article))] == ["A real story"]
        assert [s.name for s in db.scalars(select(Source))] == ["Mint - Companies"]
        assert db.scalar(select(func.count()).select_from(ArticleTag)) == 0


def test_a_pasted_connection_string_with_a_placeholder_or_a_raw_at_sign_gets_a_clear_message():
    from app.db import check_url

    with pytest.raises(SystemExit, match="placeholder"):
        check_url("postgresql://postgres.abc:pw@aws-0-<region>.pooler.supabase.com:5432/postgres")
    with pytest.raises(SystemExit, match="placeholder"):
        check_url("postgresql://postgres.abc:[YOUR-PASSWORD]@host:5432/postgres")
    with pytest.raises(SystemExit, match="URL-encoded"):
        check_url("postgresql://postgres.abc:pass@1@host:5432/postgres")
    with pytest.raises(SystemExit, match="no database URL"):
        check_url("")
    assert check_url("postgresql://postgres.abc:pa%401@host:5432/postgres").startswith("postgresql://")
    assert check_url("sqlite:///./vantage.db") == "sqlite:///./vantage.db"


def test_the_region_finder_reads_supabase_errors_correctly():
    import psycopg

    from app.supabase_load import classify, find_pooler

    assert classify("FATAL:  Tenant or user not found") == "wrong-region"
    assert classify('FATAL:  password authentication failed for user "postgres.abc"') == "wrong-password"
    assert classify("connection timed out") == "other"

    def fake(right_host, message=None):
        def connect(host, **_):
            if host == right_host:
                if message:
                    raise psycopg.OperationalError(message)
                import contextlib

                return contextlib.nullcontext()
            raise psycopg.OperationalError("FATAL:  Tenant or user not found")

        return connect

    assert find_pooler("abc", "pw", fake("aws-0-ap-south-1.pooler.supabase.com")) == ("aws-0-ap-south-1.pooler.supabase.com", "ok")
    host, status = find_pooler("abc", "bad", fake("aws-1-eu-west-2.pooler.supabase.com", "password authentication failed"))
    assert (host, status) == ("aws-1-eu-west-2.pooler.supabase.com", "wrong-password")
    assert find_pooler("abc", "pw", fake("nowhere.example")) == (None, "not-found")
