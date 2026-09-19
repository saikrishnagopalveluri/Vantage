from datetime import datetime, timezone

import pytest

from app.ingest import FeedEntry, ingest_entries
from app.models import Company, Domain, Role, Source
from app.seed import seed_taxonomy


@pytest.fixture()
def seeded(db):
    seed_taxonomy(db)
    return db


def find(db, model, **kw):
    return db.query(model).filter_by(**kw).one().id


def add_article(db, title, url, source_name="Wire"):
    source = db.query(Source).filter_by(name=source_name).first()
    if source is None:
        source = Source(name=source_name, feed_url=f"https://{source_name}.test/rss", authority=4)
        db.add(source)
        db.commit()
    ingest_entries(db, source, [FeedEntry(title, url, "", datetime.now(timezone.utc))])


def test_domains_list_with_role_counts(client, seeded):
    body = client.get("/taxonomy/domains").json()
    assert len(body) == 24
    curated = {"marketing", "finance", "sales", "hr", "consulting", "b2b", "software", "data-ai", "it-security", "product-design", "digital-transformation", "platform-business", "operations"}
    assert all(d["role_count"] >= 10 for d in body if d["slug"] in curated)
    assert {d["group"] for d in body} >= {"Business & Finance", "Technology", "Operations & Industry"}
    assert {d["slug"] for d in body} >= {"marketing", "finance", "software", "operations", "hr"}


def test_roles_filter_by_domain_and_carry_it(client, seeded):
    finance = find(seeded, Domain, slug="finance")
    roles = client.get("/taxonomy/roles", params={"domain_id": finance, "limit": 500}).json()
    assert 20 <= len(roles) <= 40
    assert {r["domain"]["name"] for r in roles} == {"Finance & Banking"}
    assert "Actuarial Analyst" in {r["title"] for r in roles}


def test_capabilities_for_a_domain_include_shared_ones(client, seeded):
    finance = find(seeded, Domain, slug="finance")
    names = {c["name"] for c in client.get("/taxonomy/capabilities", params={"domain_id": finance, "limit": 500}).json()}
    assert "Financial Modeling" in names and "Excel" in names  # its own plus the shared ones
    assert "Kubernetes" not in names


def test_companies_filter_by_domain(client, seeded):
    finance = find(seeded, Domain, slug="finance")
    fin = {c["name"] for c in client.get("/taxonomy/companies", params={"domain_id": finance, "limit": 500}).json()}
    assert "Goldman Sachs" in fin
    assert "Bosch" in fin  # manufacturers hire finance roles too
    marketing = find(seeded, Domain, slug="agriculture")
    assert "Goldman Sachs" not in {c["name"] for c in client.get("/taxonomy/companies", params={"domain_id": marketing, "limit": 500}).json()}


def test_role_detail_shows_skills_companies_and_related_roles(client, seeded):
    body = client.get(f"/taxonomy/roles/{find(seeded, Role, title='Data Scientist')}").json()
    assert body["domain"]["name"] == "Data & AI"
    assert {"Python", "Machine Learning"} <= {c["name"] for c in body["capabilities"]}
    assert body["companies"]
    assert "Decision Scientist" in {r["role"]["title"] for r in body["related_roles"]}
    assert all(0 < r["similarity"] <= 1 and r["shared_capabilities"] for r in body["related_roles"])
    assert client.get("/taxonomy/roles/nope").status_code == 404


def test_role_industry_hints_narrow_who_hires(client, seeded):
    body = client.get(f"/taxonomy/roles/{find(seeded, Role, title='Actuarial Analyst')}").json()
    assert {c["industry"]["name"] for c in body["companies"]} == {"Insurance"}


def test_company_detail_groups_roles_and_lists_news(client, seeded):
    add_article(seeded, "Infosys wins large cloud deal", "https://x.test/1")
    body = client.get(f"/taxonomy/companies/{find(seeded, Company, name='Infosys')}").json()
    assert body["industry"]["name"] == "IT Services"
    assert {g["domain"]["name"] for g in body["roles_by_domain"]} >= {"Software Engineering", "Data & AI"}
    assert [a["title"] for a in body["articles"]] == ["Infosys wins large cloud deal"]
    assert "Infosys" in body["articles"][0]["tags"]["companies"]
    assert client.get("/taxonomy/companies/nope").status_code == 404


def test_search_spans_roles_companies_skills_and_articles(client, seeded):
    add_article(seeded, "Kubernetes adoption grows among banks", "https://x.test/k")
    body = client.get("/taxonomy/search", params={"q": "kubernetes"}).json()
    assert [c["name"] for c in body["capabilities"]] == ["Kubernetes"]
    assert [a["title"] for a in body["articles"]] == ["Kubernetes adoption grows among banks"]
    analyst = client.get("/taxonomy/search", params={"q": "analyst"}).json()
    assert len(analyst["roles"]) == 8 and all("Analyst" in r["title"] for r in analyst["roles"])
    assert client.get("/taxonomy/search", params={"q": "x"}).status_code == 422


def test_search_escapes_wildcards(client, seeded):
    body = client.get("/taxonomy/search", params={"q": "%%"}).json()
    assert body["roles"] == [] and body["companies"] == [] and body["capabilities"] == []
