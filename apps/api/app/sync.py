"""Bring an existing database up to date with the hand-curated taxonomy without wiping anything.

`python -m app.seed --sync` adds curated roles, skills, companies, topics, feeds and links that are
missing. A curated name that was already imported (a company from SEC, a tool from O*NET) is promoted
to curated rather than duplicated. Users, saved stories and everything else are left alone.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.common import norm_company
from app.models import (
    Capability,
    CapabilityKind,
    Company,
    CompanyRoleCapability,
    Domain,
    Industry,
    IndustryDomain,
    Role,
    RoleCapability,
    RoleIndustry,
    Topic,
)
from app.seed import seed_sources
from app.seed_data import COMPANY_ROLE_CAPABILITIES, DOMAINS, INDUSTRIES, INDUSTRY_DOMAINS, load_taxonomy
from app.seed_data.mba import MBA_COMPANIES, MBA_ROLES, MBA_SKILLS


def sync_taxonomy(db: Session) -> dict[str, int]:
    tax = load_taxonomy()
    added = {"domains": 0, "industries": 0, "roles": 0, "capabilities": 0, "companies": 0, "topics": 0, "links": 0, "promoted": 0}

    domains = {d.slug: d for d in db.scalars(select(Domain))}
    for slug, (name, group) in DOMAINS.items():
        if slug not in domains:
            domains[slug] = Domain(name=name, slug=slug, group=group)
            db.add(domains[slug])
            added["domains"] += 1
    industries = {i.name: i for i in db.scalars(select(Industry))}
    by_key = {}
    for key, (name, aliases) in INDUSTRIES.items():
        if name not in industries:
            industries[name] = Industry(name=name, aliases=aliases)
            db.add(industries[name])
            added["industries"] += 1
        by_key[key] = industries[name]
    db.flush()

    # ---- capabilities ----
    caps = {(c.name, c.kind): c for c in db.scalars(select(Capability))}
    spec_caps: dict[str, Capability] = {}
    for spec in tax.capabilities:
        kind = CapabilityKind(spec.kind)
        cap = caps.get((spec.name, kind))
        domain_id = domains[spec.domain].id if spec.domain else None
        if cap is None:
            cap = Capability(
                name=spec.name, kind=kind, aliases=list(spec.aliases), blockers=list(spec.blockers),
                taggable=spec.taggable, source="curated", domain_id=domain_id, mba=spec.name in MBA_SKILLS,
            )
            db.add(cap)
            added["capabilities"] += 1
        else:
            if cap.source != "curated":
                cap.source, cap.taggable = "curated", spec.taggable
                added["promoted"] += 1
            # Blockers/aliases are data corrections (a false-positive tag found in production), so a
            # curated row already in the database still needs to pick these up on every sync.
            cap.aliases, cap.blockers, cap.domain_id = list(spec.aliases), list(spec.blockers), domain_id
        cap.mba = spec.name in MBA_SKILLS
        spec_caps[spec.name] = cap

    # ---- roles ----
    roles = {r.title: r for r in db.scalars(select(Role))}
    for spec in tax.roles:
        role = roles.get(spec.title)
        if role is None:
            role = Role(
                title=spec.title, aliases=list(spec.aliases), domain_id=domains[spec.domain].id,
                taggable=True, source="curated", mba=spec.title in MBA_ROLES,
            )
            db.add(role)
            roles[spec.title] = role
            added["roles"] += 1
        elif role.source != "curated":
            role.source, role.taggable, role.parent_id = "curated", True, None
            role.aliases, role.domain_id = list(spec.aliases), domains[spec.domain].id
            added["promoted"] += 1
        role.mba = spec.title in MBA_ROLES

    # ---- companies (an imported one with the same normalised name is promoted, not doubled) ----
    companies = {c.name: c for c in db.scalars(select(Company))}
    by_norm = {norm_company(c.name): c for c in companies.values()}
    for spec in tax.companies:
        company = companies.get(spec.name) or by_norm.get(norm_company(spec.name))
        industry_id = by_key[spec.industry].id
        if company is None:
            company = Company(
                name=spec.name, aliases=list(spec.aliases), blockers=list(spec.blockers),
                industry_id=industry_id, taggable=True, source="curated", mba=spec.name in MBA_COMPANIES,
            )
            db.add(company)
            added["companies"] += 1
        elif company.source != "curated":
            company.source, company.taggable, company.industry_id = "curated", True, industry_id
            company.aliases, company.blockers = list(spec.aliases), list(spec.blockers)
            added["promoted"] += 1
        company.mba = spec.name in MBA_COMPANIES
        companies[spec.name] = company

    # ---- topics ----
    topics = {t.name for t in db.scalars(select(Topic))}
    for spec in tax.topics:
        if spec.name not in topics:
            db.add(Topic(name=spec.name, aliases=list(spec.aliases), blockers=list(spec.blockers), domain_id=domains[spec.domain].id))
            added["topics"] += 1
    db.flush()

    # ---- links ----
    have_rc = set(db.execute(select(RoleCapability.role_id, RoleCapability.capability_id)).all())
    for spec in tax.roles:
        for name in spec.capabilities:
            pair = (roles[spec.title].id, spec_caps[name].id)
            if pair not in have_rc:
                db.add(RoleCapability(role_id=pair[0], capability_id=pair[1]))
                have_rc.add(pair)
                added["links"] += 1
    have_ri = set(db.execute(select(RoleIndustry.role_id, RoleIndustry.industry_id)).all())
    for spec in tax.roles:
        for key in spec.industries:
            pair = (roles[spec.title].id, by_key[key].id)
            if pair not in have_ri:
                db.add(RoleIndustry(role_id=pair[0], industry_id=pair[1]))
                have_ri.add(pair)
                added["links"] += 1
    have_id = set(db.execute(select(IndustryDomain.industry_id, IndustryDomain.domain_id)).all())
    for key, slugs in INDUSTRY_DOMAINS.items():
        for slug in slugs:
            pair = (by_key[key].id, domains[slug].id)
            if pair not in have_id:
                db.add(IndustryDomain(industry_id=pair[0], domain_id=pair[1]))
                have_id.add(pair)
                added["links"] += 1
    have_crc = set(
        db.execute(select(CompanyRoleCapability.company_id, CompanyRoleCapability.role_id, CompanyRoleCapability.capability_id)).all()
    )
    for (company, role), names in COMPANY_ROLE_CAPABILITIES.items():
        for name in names:
            triple = (companies[company].id, roles[role].id, spec_caps[name].id)
            if triple not in have_crc:
                db.add(CompanyRoleCapability(company_id=triple[0], role_id=triple[1], capability_id=triple[2]))
                have_crc.add(triple)
                added["links"] += 1

    seed_sources(db)
    db.commit()
    return added

