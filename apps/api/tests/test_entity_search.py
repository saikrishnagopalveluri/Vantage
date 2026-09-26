import httpx
import pytest

from app.entity_search import WebResult, fetch_website_meta, google_search
from app.models import Company, Domain, Role
from tests.conftest import as_user


# ---- entity_search.py: pure functions, mocked network -----------------------------------------


class FakeResponse:
    def __init__(self, json_body=None, text_body="", status_code=200, url="https://example.com"):
        self._json = json_body
        self.text = text_body
        self.status_code = status_code
        self.url = url

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=self)


def test_google_search_returns_empty_without_configured_keys(monkeypatch):
    monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)
    assert google_search("Brand Manager") == []


def test_google_search_parses_items_and_drops_ones_with_no_link(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "k")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "cx")
    monkeypatch.setattr(
        "app.entity_search.httpx.get",
        lambda *a, **kw: FakeResponse(
            json_body={"items": [
                {"title": "Brand Manager - Wikipedia", "snippet": "A role that...", "link": "https://en.wikipedia.org/wiki/Brand_management"},
                {"title": "No link here", "snippet": "..."},
            ]}
        ),
    )
    results = google_search("Brand Manager")
    assert len(results) == 1
    assert results[0] == WebResult(title="Brand Manager - Wikipedia", snippet="A role that...", url="https://en.wikipedia.org/wiki/Brand_management")


def test_google_search_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "k")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "cx")

    def broken(*a, **kw):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr("app.entity_search.httpx.get", broken)
    assert google_search("Brand Manager") == []


def test_fetch_website_meta_reads_title_and_description(monkeypatch):
    html_body = """
    <html><head>
    <title>HUL &amp; Co</title>
    <meta name="description" content="India's largest FMCG company">
    </head></html>
    """
    monkeypatch.setattr(
        "app.entity_search.httpx.get",
        lambda *a, **kw: FakeResponse(text_body=html_body, url="https://www.hul.co.in/"),
    )
    meta = fetch_website_meta("hul.co.in")
    assert meta.title == "HUL & Co"
    assert meta.snippet == "India's largest FMCG company"
    assert meta.url == "https://www.hul.co.in/"


def test_fetch_website_meta_returns_none_on_failure(monkeypatch):
    def broken(*a, **kw):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr("app.entity_search.httpx.get", broken)
    assert fetch_website_meta("not-a-real-site.example") is None


def test_fetch_website_meta_adds_https_when_missing_a_scheme(monkeypatch):
    seen = {}

    def fake_get(url, **kw):
        seen["url"] = url
        return FakeResponse(text_body="<title>X</title>")

    monkeypatch.setattr("app.entity_search.httpx.get", fake_get)
    fetch_website_meta("hul.co.in")
    assert seen["url"] == "https://hul.co.in"


# ---- the router --------------------------------------------------------------------------------


def test_suggest_roles_finds_a_close_match_and_web_results(client, world, monkeypatch):
    monkeypatch.setattr("app.routers.taxonomy.google_search", lambda q: [WebResult("A", "B", "https://x.test")])
    res = client.post("/taxonomy/roles/suggest", json={"query": "Brand"}, headers=as_user("u1"))
    assert res.status_code == 200
    body = res.json()
    assert any(m["title"] == "Brand Manager" for m in body["matches"])
    assert body["web_results"] == [{"title": "A", "snippet": "B", "url": "https://x.test"}]


def test_suggest_roles_requires_identity(client, world):
    assert client.post("/taxonomy/roles/suggest", json={"query": "Brand"}).status_code == 401


def test_add_role_creates_a_new_taggable_role(client, world, db):
    res = client.post("/taxonomy/roles", json={"title": "Growth Marketing Lead"}, headers=as_user("u1"))
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Growth Marketing Lead"
    role = db.query(Role).filter_by(title="Growth Marketing Lead").one()
    assert role.taggable is True and role.source == "user_submitted"


def test_add_role_with_a_domain_id_attaches_it(client, world, db):
    res = client.post("/taxonomy/roles", json={"title": "Field Marketing Specialist", "domain_id": world.fmcg.id}, headers=as_user("u1"))
    # fmcg is an industry id here, not a domain id, so an unknown domain_id is ignored rather than erroring
    assert res.status_code == 201
    assert db.query(Role).filter_by(title="Field Marketing Specialist").one().domain_id is None


def test_adding_a_role_that_already_exists_by_exact_title_returns_it_instead_of_duplicating(client, world, db):
    res = client.post("/taxonomy/roles", json={"title": "Brand Manager"}, headers=as_user("u1"))
    assert res.status_code == 201
    assert res.json()["id"] == world.bm.id
    assert db.query(Role).filter_by(title="Brand Manager").count() == 1


def test_add_role_with_a_real_domain_id_attaches_it(client, world, db):
    marketing = db.query(Domain).filter_by(slug="marketing").one()
    res = client.post("/taxonomy/roles", json={"title": "Performance Marketing Manager", "domain_id": marketing.id}, headers=as_user("u1"))
    assert res.status_code == 201
    assert res.json()["domain"]["id"] == marketing.id
    assert db.query(Role).filter_by(title="Performance Marketing Manager").one().domain_id == marketing.id


def test_suggest_companies_finds_a_close_match_and_can_fetch_a_given_website(client, world, monkeypatch):
    monkeypatch.setattr("app.routers.taxonomy.google_search", lambda q: [])
    monkeypatch.setattr(
        "app.routers.taxonomy.fetch_website_meta",
        lambda url: WebResult("HUL", "FMCG company", "https://hul.co.in"),
    )
    res = client.post("/taxonomy/companies/suggest", json={"query": "HUL", "website": "hul.co.in"}, headers=as_user("u1"))
    assert res.status_code == 200
    body = res.json()
    assert any(m["name"] == "HUL" for m in body["matches"])
    assert body["site_meta"] == {"title": "HUL", "snippet": "FMCG company", "url": "https://hul.co.in"}


def test_add_company_stores_the_website(client, world, db):
    res = client.post("/taxonomy/companies", json={"name": "Acme Foods", "website": "acmefoods.example"}, headers=as_user("u1"))
    assert res.status_code == 201
    company = db.query(Company).filter_by(name="Acme Foods").one()
    assert company.website == "acmefoods.example" and company.taggable is True and company.source == "user_submitted"


def test_adding_a_company_that_already_exists_by_exact_name_returns_it_instead_of_duplicating(client, world, db):
    res = client.post("/taxonomy/companies", json={"name": "HUL"}, headers=as_user("u1"))
    assert res.status_code == 201
    assert res.json()["id"] == world.hul.id
    assert db.query(Company).filter_by(name="HUL").count() == 1


def test_add_company_requires_identity(client, world):
    assert client.post("/taxonomy/companies", json={"name": "New Co"}).status_code == 401


def test_company_detail_includes_the_website(client, world, db):
    world.hul.website = "https://www.hul.co.in"
    db.commit()
    res = client.get(f"/taxonomy/companies/{world.hul.id}")
    assert res.status_code == 200
    assert res.json()["website"] == "https://www.hul.co.in"


@pytest.mark.parametrize("bad", [{"query": ""}, {"query": "x" * 141}])
def test_suggest_rejects_a_bad_query(client, world, bad):
    assert client.post("/taxonomy/roles/suggest", json=bad, headers=as_user("u1")).status_code == 422


@pytest.mark.parametrize("bad", [{"title": ""}, {"title": "x"}, {"title": "x" * 141}])
def test_add_role_rejects_a_bad_title(client, world, bad):
    assert client.post("/taxonomy/roles", json=bad, headers=as_user("u1")).status_code == 422
