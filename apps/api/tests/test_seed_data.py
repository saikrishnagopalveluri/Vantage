"""The taxonomy is data, so it gets tests: shape, references, and breadth."""

import pytest

from app.seed_data import CURATED_DOMAINS, DOMAINS, INDUSTRY_DOMAINS, load_taxonomy, validate
from app.seed_data.spec import (
    CapabilitySpec,
    RoleSpec,
    Taxonomy,
    parse_capabilities,
    parse_companies,
    parse_roles,
)


@pytest.fixture(scope="module")
def tax():
    return load_taxonomy()


def test_taxonomy_is_internally_consistent(tax):
    assert validate(tax) == []


def test_breadth_targets(tax):
    assert len(DOMAINS) >= 24
    assert len(tax.roles) >= 150
    assert len(tax.companies) >= 100
    assert len(tax.topics) >= 60
    for slug in CURATED_DOMAINS:
        assert sum(r.domain == slug for r in tax.roles) >= 10, f"{slug} has too few roles"
    for slug in DOMAINS:
        assert sum(t.domain == slug for t in tax.topics) >= 4, f"{slug} has too few topics"


def test_every_role_asks_for_enough_skills(tax):
    assert [r.title for r in tax.roles if len(r.capabilities) < 4] == []


def test_niche_roles_are_present(tax):
    titles = {r.title for r in tax.roles}
    niche = [
        "Actuarial Analyst",
        "Compiler Engineer",
        "Cold Chain Manager",
        "Geospatial Analyst",
        "Digital Forensics Analyst",
        "Biostatistician",
        "Service Designer",
        "Retail Media Manager",
    ]
    assert set(niche) <= titles


def test_every_industry_has_companies_and_hiring_domains(tax):
    assert {c.industry for c in tax.companies} == set(INDUSTRY_DOMAINS)


def test_every_domain_is_hired_for_by_some_industry():
    assert {d for domains in INDUSTRY_DOMAINS.values() for d in domains} == set(DOMAINS)


def test_generic_skills_never_tag_news(tax):
    generic = {"Communication", "Leadership", "Negotiation", "Stakeholder Management"}
    assert all(not c.taggable for c in tax.capabilities if c.name in generic)


def test_parser_keeps_empty_fields_empty():
    (spec,) = parse_capabilities("Java | T | | avoid:West Java; avoid:Java Sea", None)
    assert spec.aliases == () and spec.blockers == ("West Java", "Java Sea")
    (company,) = parse_companies("Apple | saas | | avoid:apple juice")
    assert company.aliases == () and company.blockers == ("apple juice",)


def test_parser_rejects_bad_lines():
    with pytest.raises(ValueError, match="kind must be T or S"):
        parse_capabilities("Excel | X", None)
    with pytest.raises(ValueError, match="no capabilities"):
        parse_roles("Ghost Role | | ", "marketing")


def test_validation_reports_dangling_references_and_alias_clashes():
    tax = Taxonomy(
        capabilities=[CapabilitySpec("A", "tool", None, ("shared",)), CapabilitySpec("B", "tool", None, ("shared",))],
        roles=[RoleSpec("R", "marketing", (), ("A", "Missing"), ("nope",))],
    )
    problems = "\n".join(validate(tax))
    assert "unknown capability 'Missing'" in problems
    assert "unknown industry 'nope'" in problems
    assert "'shared' is claimed by" in problems
