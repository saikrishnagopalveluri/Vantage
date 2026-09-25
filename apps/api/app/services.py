from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Capability,
    Company,
    Domain,
    Industry,
    Role,
    UserCapability,
    UserDomain,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)
from app.schemas import CapabilityRef, NamedRef, ProfileOut, RoleRef


def domain_ref(domain: Domain | None) -> NamedRef | None:
    return NamedRef(id=domain.id, name=domain.name) if domain else None


def role_ref(role: Role) -> RoleRef:
    parent = role.parent if role.parent_id else None
    return RoleRef(
        id=role.id,
        title=role.title,
        domain=domain_ref(role.domain),
        parent=NamedRef(id=parent.id, name=parent.title) if parent else None,
        mba=role.mba,
    )


def capability_ref(cap: Capability) -> CapabilityRef:
    return CapabilityRef(id=cap.id, name=cap.name, kind=cap.kind, domain=domain_ref(cap.domain), mba=cap.mba)


def resolve_industry(db: Session, company: Company, industry_id: str | None) -> Industry:
    if industry_id is not None:
        industry = db.get(Industry, industry_id)
        if industry is None:
            raise HTTPException(status_code=404, detail="Industry not found")
        return industry
    if company.industry is not None:
        return company.industry
    raise HTTPException(
        status_code=422,
        detail="Industry required: this company has no default industry on file",
    )


def current_state(profile: UserProfile) -> dict:
    company, industry = profile.current_company, profile.current_industry
    return {
        "user_id": profile.user_id,
        "name": profile.user.name if profile.user else None,
        "profile_status": profile.profile_status,
        "current_role": role_ref(profile.current_role) if profile.current_role else None,
        "current_company": NamedRef(id=company.id, name=company.name) if company else None,
        "current_industry": NamedRef(id=industry.id, name=industry.name) if industry else None,
        "placed_at": profile.placed_at,
        "current_role_started_at": profile.current_role_started_at,
    }


def profile_out(db: Session, profile: UserProfile) -> ProfileOut:
    user_id = profile.user_id
    domains = db.scalars(
        select(Domain)
        .join(UserDomain, UserDomain.domain_id == Domain.id)
        .where(UserDomain.user_id == user_id)
        .order_by(Domain.name)
    )
    roles = db.scalars(
        select(Role)
        .join(UserTargetRole, UserTargetRole.role_id == Role.id)
        .where(UserTargetRole.user_id == user_id)
        .order_by(Role.title)
    )
    companies = db.scalars(
        select(Company)
        .join(UserTargetCompany, UserTargetCompany.company_id == Company.id)
        .where(UserTargetCompany.user_id == user_id)
        .order_by(Company.name)
    )
    capabilities = db.scalars(
        select(Capability)
        .join(UserCapability, UserCapability.capability_id == Capability.id)
        .where(UserCapability.user_id == user_id)
        .order_by(Capability.kind, Capability.name)
    )
    return ProfileOut(
        **current_state(profile),
        domains=[NamedRef(id=d.id, name=d.name) for d in domains],
        target_roles=[role_ref(r) for r in roles],
        target_companies=[NamedRef(id=c.id, name=c.name) for c in companies],
        capabilities=[capability_ref(c) for c in capabilities],
    )


def unique_ids(ids: list[str]) -> list[str]:
    return list(dict.fromkeys(ids))


def missing_ids(db: Session, model, ids: list[str]) -> list[str]:
    if not ids:
        return []
    found = set(db.scalars(select(model.id).where(model.id.in_(ids))))
    return [i for i in ids if i not in found]


def unknown_target_ids(
    db: Session,
    role_ids: list[str],
    company_ids: list[str],
    capability_ids: list[str],
    domain_ids: list[str] | None = None,
) -> dict[str, list[str]]:
    unknown = {
        "domain_ids": missing_ids(db, Domain, domain_ids or []),
        "target_role_ids": missing_ids(db, Role, role_ids),
        "target_company_ids": missing_ids(db, Company, company_ids),
        "capability_ids": missing_ids(db, Capability, capability_ids),
    }
    return {field: ids for field, ids in unknown.items() if ids}
