"""Who hires whom, derived from data we hold rather than stored as company x role rows.

A company in industry I hires a role when the role's field is one of I's fields (IndustryDomain)
and, if the role is limited to certain industries (RoleIndustry), I is one of them. Variants of a
job title inherit all of this from the role they point at.
"""

from sqlalchemy import Select, exists, or_, select
from sqlalchemy.orm import Session

from app.models import Company, IndustryDomain, Role, RoleIndustry


def canonical(db: Session, role: Role) -> Role:
    """The role that owns the skills and hiring rules for this title."""
    return db.get(Role, role.parent_id) if role.parent_id else role


def company_hires_role(db: Session, industry_id: str | None, role: Role) -> bool:
    base = canonical(db, role)
    if not industry_id or not base.domain_id:
        return False
    in_field = db.scalar(
        select(
            exists().where(IndustryDomain.industry_id == industry_id, IndustryDomain.domain_id == base.domain_id)
        )
    )
    if not in_field:
        return False
    hints = set(db.scalars(select(RoleIndustry.industry_id).where(RoleIndustry.role_id == base.id)))
    return not hints or industry_id in hints


def companies_hiring_role(db: Session, role: Role) -> Select[tuple[Company]]:
    base = canonical(db, role)
    if not base.domain_id:
        return select(Company).where(False)
    industries = select(IndustryDomain.industry_id).where(IndustryDomain.domain_id == base.domain_id)
    hints = list(db.scalars(select(RoleIndustry.industry_id).where(RoleIndustry.role_id == base.id)))
    stmt = select(Company).where(Company.industry_id.in_(industries))
    return stmt.where(Company.industry_id.in_(hints)) if hints else stmt


def companies_hiring_domain(domain_id: str) -> Select[tuple[Company]]:
    industries = select(IndustryDomain.industry_id).where(IndustryDomain.domain_id == domain_id)
    return select(Company).where(Company.industry_id.in_(industries))


def roles_hired_by(company: Company) -> Select[tuple[Role]]:
    """Role families (not every title variant) this company's industry hires for."""
    if not company.industry_id:
        return select(Role).where(False)
    fields = select(IndustryDomain.domain_id).where(IndustryDomain.industry_id == company.industry_id)
    restricted = exists().where(RoleIndustry.role_id == Role.id)
    allowed_here = exists().where(RoleIndustry.role_id == Role.id, RoleIndustry.industry_id == company.industry_id)
    return select(Role).where(Role.parent_id.is_(None), Role.domain_id.in_(fields), or_(~restricted, allowed_here))
