import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("VANTAGE_SCHEDULER", "0")  # tests must never start a background ingest
os.environ.setdefault("VANTAGE_REQUIRE_CONSENT", "0")  # consent has its own tests (tests/test_privacy.py)

from app.deps import get_db
from app.main import app
from app.models import (
    Base,
    Capability,
    CapabilityKind,
    Company,
    Domain,
    IndustryDomain,
    Industry,
    Role,
    RoleIndustry,
    User,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)


@pytest.fixture()
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture()
def client(session_factory):
    def override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def taxonomy(db):
    """Reference data only, no users."""
    fmcg, ecom = Industry(name="FMCG"), Industry(name="E-commerce")
    marketing = Domain(name="Marketing", slug="marketing")
    db.add(marketing)
    db.flush()
    bm = Role(title="Brand Manager", domain_id=marketing.id, taggable=True)
    dmm = Role(title="Digital Marketing Manager", domain_id=marketing.id, taggable=True)
    hul = Company(name="HUL", industry=fmcg, taggable=True)
    itc = Company(name="ITC", industry=fmcg, taggable=True)
    nestle = Company(name="Nestle", industry=fmcg, taggable=True)
    amazon = Company(name="Amazon", industry=ecom, taggable=True)
    nameless_industry = Company(name="Startup Co", taggable=True)
    excel = Capability(name="Excel", kind=CapabilityKind.TOOL)
    powerbi = Capability(name="Power BI", kind=CapabilityKind.TOOL)
    insights = Capability(name="Consumer Insights", kind=CapabilityKind.SKILL)
    db.add_all([fmcg, ecom, bm, dmm, hul, itc, nestle, amazon, nameless_industry])
    db.add_all([excel, powerbi, insights])
    db.flush()
    # Hiring is derived: an industry hires a field, and a role can be limited to certain industries.
    db.add_all([IndustryDomain(industry_id=fmcg.id, domain_id=marketing.id), IndustryDomain(industry_id=ecom.id, domain_id=marketing.id)])
    db.add_all([RoleIndustry(role_id=bm.id, industry_id=fmcg.id), RoleIndustry(role_id=dmm.id, industry_id=ecom.id)])
    db.commit()
    return SimpleNamespace(
        fmcg=fmcg, ecom=ecom, bm=bm, dmm=dmm, hul=hul, itc=itc, nestle=nestle, amazon=amazon,
        nameless_industry=nameless_industry, excel=excel, powerbi=powerbi, insights=insights,
    )


@pytest.fixture()
def world(db, taxonomy):
    """Student 'u1' targeting Brand Manager at HUL/ITC/Nestle (+ Amazon, which doesn't hire BMs)."""
    db.add_all([User(id="u1"), User(id="u2")])
    db.flush()
    db.add_all([UserProfile(user_id="u1"), UserProfile(user_id="u2")])
    db.add(UserTargetRole(user_id="u1", role_id=taxonomy.bm.id))
    for company in (taxonomy.hul, taxonomy.itc, taxonomy.nestle, taxonomy.amazon):
        db.add(UserTargetCompany(user_id="u1", company_id=company.id))
    db.commit()
    return taxonomy


def as_user(user_id: str) -> dict[str, str]:
    return {"X-User-Id": user_id}
