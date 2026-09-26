from sqlalchemy import create_engine, inspect, text

from app.migrate import add_missing_columns
from app.models import Capability, Company, Role
from app.seed import seed_taxonomy
from app.seed_data.mba import MBA_COMPANIES, MBA_ROLES, MBA_SKILLS
from app.sync import sync_taxonomy


def test_every_management_pick_exists_and_is_flagged(db):
    seed_taxonomy(db)
    assert {r.title for r in db.query(Role).filter_by(mba=True)} == MBA_ROLES
    assert {c.name for c in db.query(Company).filter_by(mba=True)} == MBA_COMPANIES
    assert {c.name for c in db.query(Capability).filter_by(mba=True)} == MBA_SKILLS


def test_the_management_lists_are_substantial():
    assert len(MBA_ROLES) >= 100 and len(MBA_COMPANIES) >= 140 and len(MBA_SKILLS) >= 70


def test_filters_return_only_what_management_students_want(client, db):
    seed_taxonomy(db)
    roles = client.get("/taxonomy/roles", params={"mba": "true", "limit": 500}).json()
    assert {r["title"] for r in roles} == MBA_ROLES and all(r["mba"] for r in roles)
    companies = client.get("/taxonomy/companies", params={"mba": "true", "limit": 500}).json()
    assert {c["name"] for c in companies} == MBA_COMPANIES
    skills = client.get("/taxonomy/capabilities", params={"mba": "true", "limit": 500}).json()
    assert {s["name"] for s in skills} == MBA_SKILLS


def test_browsing_and_searching_put_management_picks_first(client, db):
    seed_taxonomy(db)
    # a plain company list starts with the recruiters students target
    first_companies = client.get("/taxonomy/companies", params={"limit": 40}).json()
    assert sum(c["mba"] for c in first_companies) >= 30
    # among equally good matches, a management role comes before one that is not
    manager = client.get("/taxonomy/roles", params={"q": "manager", "limit": 60}).json()
    flags = [r["mba"] for r in manager if r["title"].lower().startswith("manager")] or [r["mba"] for r in manager]
    assert flags == sorted(flags, reverse=True)
    brand = client.get("/taxonomy/roles", params={"q": "brand manager", "limit": 5}).json()
    assert brand[0]["title"] == "Brand Manager" and brand[0]["mba"] is True


def test_recruiters_from_the_wish_list_are_there(db):
    seed_taxonomy(db)
    names = {c.name for c in db.query(Company)}
    assert {"McKinsey & Company", "Goldman Sachs", "Hindustan Unilever", "Kearney", "Peak XV Partners", "Trent", "Avendus Capital"} <= names
    titles = {r.title for r in db.query(Role)}
    assert {"Associate Brand Manager", "Investment Banking Associate", "Engagement Manager", "Chief of Staff", "Area Sales Manager"} <= titles


def test_sync_flags_an_older_database_without_wiping_it(db):
    seed_taxonomy(db)
    db.query(Role).update({"mba": False})
    db.query(Company).update({"mba": False})
    db.query(Capability).update({"mba": False})
    db.commit()
    sync_taxonomy(db)
    assert db.query(Role).filter_by(mba=True).count() == len(MBA_ROLES)
    assert db.query(Company).filter_by(mba=True).count() == len(MBA_COMPANIES)


def test_new_columns_are_added_to_a_database_made_by_an_older_version(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        for table in ("roles", "companies", "capabilities"):
            conn.execute(text(f"CREATE TABLE {table} (id TEXT PRIMARY KEY, name TEXT)"))
    first = add_missing_columns(engine)
    assert sorted(first) == ["capabilities.mba", "companies.mba", "companies.website", "roles.mba"]
    assert "mba" in {c["name"] for c in inspect(engine).get_columns("roles")}
    assert add_missing_columns(engine) == []  # safe to run every time
