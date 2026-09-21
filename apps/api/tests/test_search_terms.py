import pytest

from app.models import Capability, CapabilityKind, Company, Role
from app.search_terms import MAX_VARIANTS, variants


@pytest.mark.parametrize(
    "query, expected",
    [
        ("modelling", "modeling"),
        ("financial modelling", "financial modeling"),
        ("Organizational Behavior", "organisational behavior"),
        ("organisation design", "organization design"),
        ("analyse data", "analyze data"),
        ("programme manager", "program manager"),
        ("optimisation", "optimization"),
        ("go-to-market", "go to market"),
        ("e commerce", "e-commerce"),
        ("ms excel", "excel"),
        ("Microsoft Excel", "excel"),
        ("dcf", "discounted cash flow"),
        ("fmcg", "consumer goods"),
        ("m&a", "mergers and acquisitions"),
        ("gtm", "go-to-market"),
    ],
)
def test_variants_include_the_other_way_of_saying_it(query, expected):
    assert variants(query)[0] == " ".join(query.lower().split()) and expected in variants(query)


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
def test_blank_queries_have_no_variants(query):
    assert variants(query) == []


@pytest.mark.parametrize("query", ["brand manager", "excel", "x" * 80, "%", "'; drop table roles;--", "日本語", "🙂"])
def test_variants_are_bounded_unique_and_start_with_the_query(query):
    v = variants(query)
    assert v[0] == query.lower() and len(v) == len(set(v)) <= MAX_VARIANTS


def test_a_short_acronym_only_expands_when_it_is_the_whole_query():
    assert "artificial intelligence" in variants("ai")
    assert "artificial intelligence" not in variants("email marketing")  # "ai" inside a word is left alone
    assert variants("retail") == ["retail"]


@pytest.fixture()
def catalogue(db, taxonomy):
    db.add_all(
        [
            Capability(name="Financial Modeling", kind=CapabilityKind.SKILL),
            Capability(name="Discounted Cash Flow", kind=CapabilityKind.SKILL),
            Capability(name="Organisational Readiness", kind=CapabilityKind.SKILL),
            Capability(name="Organizational Behavior", kind=CapabilityKind.SKILL),
            Role(title="Programme Manager", taggable=False),
            Company(name="Consumer Goods Co", taggable=False),
        ]
    )
    db.commit()


@pytest.mark.parametrize(
    "q, expected",
    [("modelling", "Financial Modeling"), ("DCF", "Discounted Cash Flow"), ("MS Excel", "Excel"), ("Microsoft Excel", "Excel")],
)
def test_skill_search_finds_the_catalogue_name(client, catalogue, q, expected):
    assert expected in [c["name"] for c in client.get("/taxonomy/capabilities", params={"q": q}).json()]


def test_uk_and_us_spellings_find_each_other_both_ways(client, catalogue):
    names = {c["name"] for c in client.get("/taxonomy/capabilities", params={"q": "organisational"}).json()}
    assert names == {"Organisational Readiness", "Organizational Behavior"}
    names = {c["name"] for c in client.get("/taxonomy/capabilities", params={"q": "organizational"}).json()}
    assert names == {"Organisational Readiness", "Organizational Behavior"}


def test_role_and_company_and_global_search_use_the_variants(client, catalogue):
    assert [r["title"] for r in client.get("/taxonomy/roles", params={"q": "program manager"}).json()] == ["Programme Manager"]
    assert "Programme Manager" in [r["title"] for r in client.get("/taxonomy/roles", params={"q": "programme"}).json()]
    assert "Consumer Goods Co" in [c["name"] for c in client.get("/taxonomy/companies", params={"q": "fmcg"}).json()]
    found = client.get("/taxonomy/search", params={"q": "dcf"}).json()
    assert [c["name"] for c in found["capabilities"]] == ["Discounted Cash Flow"]


def test_the_typed_spelling_still_ranks_first(client, catalogue, db):
    db.add(Capability(name="Modelling Standards", kind=CapabilityKind.SKILL))
    db.commit()
    names = [c["name"] for c in client.get("/taxonomy/capabilities", params={"q": "modelling"}).json()]
    assert names[0] == "Modelling Standards" and "Financial Modeling" in names


def test_search_variants_do_not_make_wildcards_match_everything(client, catalogue):
    assert client.get("/taxonomy/capabilities", params={"q": "%"}).json() == []
    assert client.get("/taxonomy/capabilities", params={"q": "_"}).json() == []
