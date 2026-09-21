"""The consulting, advisory, IT-services and digital-transformation additions."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Company, Role, TagType
from app.seed import seed_taxonomy
from app.seed_data import load_taxonomy
from app.seed_data.mba import MBA_COMPANIES, MBA_ROLES, MBA_SKILLS
from app.tagging import build_index, tag_article

TAX = load_taxonomy()
COMPANY_NAMES = {c.name for c in TAX.companies}
ROLE_TITLES = {r.title for r in TAX.roles}
SKILL_NAMES = {c.name for c in TAX.capabilities}


@pytest.fixture(scope="module")
def tagged():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        seed_taxonomy(db)
        names = {c.id: c.name for c in db.query(Company)}
        index = build_index(db)

    def companies(title: str, teaser: str = "") -> set[str]:
        return {names[ref] for (kind, ref) in tag_article(index, title, teaser) if kind == TagType.COMPANY}

    return companies


@pytest.mark.parametrize(
    "name",
    ["Deloitte", "PwC", "EY", "KPMG", "Grant Thornton", "BDO", "RSM", "Forvis Mazars", "Protiviti", "Guidehouse", "Booz Allen Hamilton",
     "McKinsey & Company", "Boston Consulting Group", "Bain & Company", "Kearney", "Oliver Wyman", "Roland Berger", "Simon-Kucher & Partners",
     "AlixPartners", "FTI Consulting", "Monitor Deloitte", "EY-Parthenon", "BCG X", "Mercer", "Aon", "WTW", "Korn Ferry", "Heidrick & Struggles",
     "Zinnov", "Everest Group", "IDC", "Frost & Sullivan", "Accenture", "Capgemini", "Cognizant", "LTIMindtree", "Mphasis", "Coforge",
     "Thoughtworks", "Publicis Sapient", "NTT DATA", "CGI", "Tata Consultancy Services", "Infosys", "Wipro", "HCLTech", "Tech Mahindra",
     "ServiceNow", "Workday", "Databricks", "UiPath", "Celonis", "CrowdStrike", "Cloudflare"],
)
def test_the_firms_you_would_expect_are_in_the_catalogue(name):
    assert name in COMPANY_NAMES


def test_the_catalogue_grew_a_lot():
    assert len(COMPANY_NAMES) >= 500


@pytest.mark.parametrize(
    "title",
    ["Principal", "Associate Partner", "Partner", "Case Team Leader", "Digital Transformation Consultant", "Technology Strategy Consultant",
     "Cloud Transformation Consultant", "Data and Analytics Consultant", "AI Strategy Consultant", "Risk Consultant", "Financial Advisory Analyst",
     "Forensic Consultant", "Restructuring Consultant", "Human Capital Consultant", "Customer Experience Consultant", "Change Management Consultant",
     "PMO Lead", "Delivery Manager", "Client Partner", "Presales Consultant", "Research Analyst (Consulting)", "Automation Lead",
     "Innovation Lead", "Technical Program Manager", "Solutions Consultant", "Implementation Consultant", "Customer Success Consultant",
     "Management Consultant", "Associate Consultant", "Senior Consultant", "Engagement Manager", "Strategy Consultant"],
)
def test_the_consulting_and_transformation_roles_are_there(title):
    assert title in ROLE_TITLES


def test_every_new_role_names_only_skills_that_exist():
    for role in TAX.roles:
        assert set(role.capabilities) <= SKILL_NAMES, role.title


def test_the_management_student_lists_only_name_real_things():
    assert MBA_COMPANIES <= COMPANY_NAMES and MBA_ROLES <= ROLE_TITLES and MBA_SKILLS <= SKILL_NAMES


@pytest.mark.parametrize(
    "headline, expected",
    [
        ("Deloitte India appoints new head of consulting", "Deloitte"),
        ("PwC India launches an AI practice", "PwC"),
        ("EY-Parthenon adds partners in Mumbai", "EY-Parthenon"),
        ("KPMG India hires 5,000 freshers", "KPMG"),
        ("McKinsey Global Institute report on productivity", "McKinsey & Company"),
        ("BCG X builds an assistant for a bank", "BCG X"),
        ("Accenture Song wins a global creative account", "Accenture Song"),
        ("Infosys Consulting opens a Pune centre", "Infosys"),
        ("LTIMindtree wins a large cloud deal", "LTIMindtree"),
        ("Grant Thornton Bharat expands its advisory team", "Grant Thornton"),
        ("Willis Towers Watson survey on salary hikes", "WTW"),
        ("Publicis Sapient bets on generative AI", "Publicis Sapient"),
        ("UiPath and Celonis partner on process mining", "UiPath"),
    ],
)
def test_common_ways_of_naming_a_firm_find_it(tagged, headline, expected):
    assert expected in tagged(headline)


@pytest.mark.parametrize(
    "headline, wrongly_tagged",
    [
        ("Russell Crowe stars in a new thriller", "Crowe"),
        ("Skiers race through the slalom course in Kitzbuehel", "Slalom"),
        ("Storms hit Lake Huron shipping lanes", "Huron Consulting"),
        ("Mercer County votes on a new school budget", "Mercer"),
        ("Storm over Mercer Island closes the bridge", "Mercer"),
        ("Postman pat returns to television", "Postman"),
    ],
)
def test_ordinary_uses_of_a_name_do_not_tag_a_firm(tagged, headline, wrongly_tagged):
    assert wrongly_tagged not in tagged(headline)


def test_two_firms_in_one_headline_are_both_found(tagged):
    assert {"Deloitte", "PwC"} <= tagged("Deloitte and PwC compete for the same audit mandate")
