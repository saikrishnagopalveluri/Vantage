"""Loads the placeholder taxonomy, curated sources, sample articles and a demo student."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app.migrate import add_missing_columns
from app.ingest import FeedEntry, ingest_entries
from app.models import (
    Base,
    Capability,
    CapabilityKind,
    Company,
    IndustryDomain,
    RoleIndustry,
    CompanyRoleCapability,
    Domain,
    Industry,
    Role,
    RoleCapability,
    Source,
    Topic,
    User,
    UserCapability,
    UserDomain,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)
from app.seed_data import (
    COMPANY_ROLE_CAPABILITIES,
    DOMAINS,
    INDUSTRIES,
    INDUSTRY_DOMAINS,
    SAMPLE_ARTICLES,
    SAMPLE_SOURCE,
    SOURCES,
    load_taxonomy,
)
from app.seed_data.mba import MBA_COMPANIES, MBA_ROLES, MBA_SKILLS

DEMO_USER_ID = "demo-student"


def seed_taxonomy(db: Session) -> None:
    """Load the hand-curated taxonomy. Safe to call on a database that already has it."""
    if db.query(Domain).first() is not None:
        return
    tax = load_taxonomy()

    domains = {slug: Domain(name=name, slug=slug, group=group) for slug, (name, group) in DOMAINS.items()}
    industries = {key: Industry(name=name, aliases=aliases) for key, (name, aliases) in INDUSTRIES.items()}
    db.add_all([*domains.values(), *industries.values()])
    db.flush()

    roles = {
        r.title: Role(
            title=r.title,
            aliases=list(r.aliases),
            domain_id=domains[r.domain].id,
            taggable=True,
            source="curated",
            mba=r.title in MBA_ROLES,
        )
        for r in tax.roles
    }
    capabilities = {
        c.name: Capability(
            name=c.name,
            kind=CapabilityKind(c.kind),
            aliases=list(c.aliases),
            blockers=list(c.blockers),
            taggable=c.taggable,
            source="curated",
            mba=c.name in MBA_SKILLS,
            domain_id=domains[c.domain].id if c.domain else None,
        )
        for c in tax.capabilities
    }
    companies = {
        c.name: Company(
            name=c.name,
            aliases=list(c.aliases),
            blockers=list(c.blockers),
            industry_id=industries[c.industry].id,
            taggable=True,
            source="curated",
            mba=c.name in MBA_COMPANIES,
        )
        for c in tax.companies
    }
    topics = [
        Topic(name=t.name, aliases=list(t.aliases), blockers=list(t.blockers), domain_id=domains[t.domain].id)
        for t in tax.topics
    ]
    db.add_all([*roles.values(), *capabilities.values(), *companies.values(), *topics])
    db.flush()

    db.execute(
        RoleCapability.__table__.insert(),
        [
            {"role_id": roles[r.title].id, "capability_id": capabilities[cap].id}
            for r in tax.roles
            for cap in r.capabilities
        ],
    )
    # Hiring is derived from these two small tables; see app/hiring.py.
    db.execute(
        IndustryDomain.__table__.insert(),
        [
            {"industry_id": industries[key].id, "domain_id": domains[slug].id}
            for key, slugs in INDUSTRY_DOMAINS.items()
            for slug in slugs
        ],
    )
    hints = [
        {"role_id": roles[r.title].id, "industry_id": industries[key].id}
        for r in tax.roles
        for key in r.industries
    ]
    if hints:
        db.execute(RoleIndustry.__table__.insert(), hints)

    for (company, role), cap_names in COMPANY_ROLE_CAPABILITIES.items():
        for cap in cap_names:
            db.add(
                CompanyRoleCapability(
                    company_id=companies[company].id, role_id=roles[role].id, capability_id=capabilities[cap].id
                )
            )
    db.commit()


def seed_sources(db: Session) -> None:
    existing = {s.name for s in db.query(Source)}
    db.add_all(
        Source(name=n, feed_url=u, authority=a)
        for n, u, a in [*SOURCES, SAMPLE_SOURCE]
        if n not in existing
    )
    db.commit()


def seed_samples(db: Session) -> int:
    source = db.query(Source).filter_by(name=SAMPLE_SOURCE[0]).one()
    now = datetime.now(timezone.utc)
    return ingest_entries(
        db,
        source,
        [
            FeedEntry(
                title=title,
                url=f"https://example.com/vantage-sample/{i}",
                summary=summary,
                published_at=now - timedelta(days=days_ago),
            )
            for i, (days_ago, title, summary) in enumerate(SAMPLE_ARTICLES)
        ],
    )


def seed_demo_user(db: Session) -> None:
    if db.get(User, DEMO_USER_ID) is not None:
        return
    role = db.query(Role).filter_by(title="Brand Manager").one()
    domain = db.query(Domain).filter_by(slug="marketing").one()
    db.add(User(id=DEMO_USER_ID))
    db.flush()
    db.add(UserProfile(user_id=DEMO_USER_ID))
    db.add(UserDomain(user_id=DEMO_USER_ID, domain_id=domain.id))
    db.add(UserTargetRole(user_id=DEMO_USER_ID, role_id=role.id))
    for name in ("Hindustan Unilever", "ITC", "Nestle India", "Procter & Gamble"):
        db.add(UserTargetCompany(user_id=DEMO_USER_ID, company_id=db.query(Company).filter_by(name=name).one().id))
    for name in ("Excel", "Consumer Insights"):
        db.add(UserCapability(user_id=DEMO_USER_ID, capability_id=db.query(Capability).filter_by(name=name).one().id))
    db.commit()


def seed(db: Session, *, samples: bool = False) -> None:
    """Sample articles are placeholders for demos and the browser tests; real installs skip them."""
    seed_taxonomy(db)
    seed_sources(db)
    if samples:
        seed_samples(db)
        seed_demo_user(db)


if __name__ == "__main__":
    import sys

    Base.metadata.create_all(bind=engine)
    add_missing_columns(engine)
    with SessionLocal() as session:
        if "--sync" in sys.argv:
            from app.sync import sync_taxonomy

            print("Synced:", sync_taxonomy(session))
        else:
            seed(session, samples="--samples" in sys.argv)
            print("Seeded." + (f" Demo user id: {DEMO_USER_ID}" if "--samples" in sys.argv else ""))
