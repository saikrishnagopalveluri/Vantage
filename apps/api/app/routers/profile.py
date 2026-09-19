from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.deps import get_caller_id, get_db, require_self
from app.models import (
    JD,
    Capability,
    Company,
    CompanyRoleCapability,
    JDCapability,
    ProfileEvent,
    ProfileStatus,
    Role,
    RoleCapability,
    UserCapability,
    UserDomain,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)
from app.schemas import (
    CapabilityGap,
    PlacementIn,
    PlacementOut,
    ProfileOut,
    RoleGaps,
    SkillGapsOut,
    TargetsIn,
)
from app.hiring import canonical, company_hires_role
from app.services import (
    current_state,
    profile_out,
    resolve_industry,
    unique_ids,
    unknown_target_ids,
)

router = APIRouter(prefix="/profile", tags=["profile"])

SOURCE_RANK = {"taxonomy": 0, "company": 1, "jd": 2}


def _load_profile(db: Session, user_id: str) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/{user_id}", response_model=ProfileOut)
def get_profile(
    user_id: str,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> ProfileOut:
    require_self(user_id, caller_id)
    return profile_out(db, _load_profile(db, user_id))


@router.put("/{user_id}/targets", response_model=ProfileOut)
def replace_targets(
    user_id: str,
    body: TargetsIn,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> ProfileOut:
    """Replace the user's target roles, target companies and owned capabilities wholesale."""
    require_self(user_id, caller_id)
    profile = _load_profile(db, user_id)
    domain_ids = unique_ids(body.domain_ids)
    role_ids = unique_ids(body.target_role_ids)
    company_ids = unique_ids(body.target_company_ids)
    capability_ids = unique_ids(body.capability_ids)
    unknown = unknown_target_ids(db, role_ids, company_ids, capability_ids, domain_ids)
    if unknown:
        raise HTTPException(status_code=422, detail={"unknown_ids": unknown})

    for table in (UserDomain, UserTargetRole, UserTargetCompany, UserCapability):
        db.execute(delete(table).where(table.user_id == user_id))
    db.add_all(UserDomain(user_id=user_id, domain_id=i) for i in domain_ids)
    db.add_all(UserTargetRole(user_id=user_id, role_id=i) for i in role_ids)
    db.add_all(UserTargetCompany(user_id=user_id, company_id=i) for i in company_ids)
    db.add_all(UserCapability(user_id=user_id, capability_id=i) for i in capability_ids)
    db.commit()
    return profile_out(db, profile)


@router.post("/{user_id}/placement", response_model=PlacementOut)
def mark_placement(
    user_id: str,
    body: PlacementIn,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> PlacementOut:
    """First call is a placement; later calls with a different company/role are job changes."""
    require_self(user_id, caller_id)
    profile = _load_profile(db, user_id)

    company = db.get(Company, body.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    role = db.get(Role, body.role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    industry = resolve_industry(db, company, body.industry_id)

    if profile.profile_status == ProfileStatus.TARGETING:
        event_type = "placed"
    elif (profile.current_company_id, profile.current_role_id) != (company.id, role.id):
        event_type = "role_changed"
    else:
        return PlacementOut(**current_state(profile), event_type="unchanged")

    now = datetime.now(timezone.utc)
    if event_type == "placed":
        # Written once, on the placed transition only: "time to first job" must survive later
        # job changes, and must stay empty for people who onboarded already employed.
        profile.placed_at = (
            datetime.combine(body.placed_on, time.min, tzinfo=timezone.utc)
            if body.placed_on
            else now
        )
    db.add(
        ProfileEvent(
            user_id=user_id,
            event_type=event_type,
            payload={
                "old_role_id": profile.current_role_id,
                "old_company_id": profile.current_company_id,
                "new_role_id": role.id,
                "new_company_id": company.id,
            },
        )
    )
    profile.current_role_id = role.id
    profile.current_company_id = company.id
    profile.current_industry_id = industry.id
    profile.current_role_started_at = now
    profile.profile_status = ProfileStatus.PLACED

    if body.clear_targets:
        db.execute(delete(UserTargetRole).where(UserTargetRole.user_id == user_id))
        db.execute(delete(UserTargetCompany).where(UserTargetCompany.user_id == user_id))

    db.commit()
    db.refresh(profile)
    return PlacementOut(**current_state(profile), event_type=event_type)


def _capabilities_for_pair(
    db: Session, user_id: str, company_id: str, role: Role, base: Role
) -> tuple[set[str], str] | None:
    """Most specific capability source wins: the user's own job description for this role (at this
    company, or not tied to a company), then company-specific data, then the role's general list."""
    jd_caps = set(
        db.scalars(
            select(JDCapability.capability_id)
            .join(JD, JD.id == JDCapability.jd_id)
            .where(
                JD.user_id == user_id,
                JD.role_id.in_([role.id, base.id]),
                or_(JD.company_id == company_id, JD.company_id.is_(None)),
            )
        )
    )
    if jd_caps:
        return jd_caps, "jd"
    company_caps = set(
        db.scalars(
            select(CompanyRoleCapability.capability_id).where(
                CompanyRoleCapability.company_id == company_id,
                CompanyRoleCapability.role_id == base.id,
            )
        )
    )
    if company_caps:
        return company_caps, "company"
    role_caps = set(
        db.scalars(select(RoleCapability.capability_id).where(RoleCapability.role_id == base.id))
    )
    if role_caps:
        return role_caps, "taxonomy"
    return None


@router.get("/{user_id}/skill-gaps", response_model=SkillGapsOut)
def skill_gaps(
    user_id: str,
    role_id: str | None = None,
    gaps_only: bool = False,
    min_ratio: float = Query(default=0.0, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> SkillGapsOut:
    require_self(user_id, caller_id)
    _load_profile(db, user_id)

    target_role_ids = set(
        db.scalars(select(UserTargetRole.role_id).where(UserTargetRole.user_id == user_id))
    )
    if role_id is not None:
        if role_id not in target_role_ids:
            raise HTTPException(status_code=404, detail="Role is not one of the user's targets")
        target_role_ids = {role_id}
    target_company_ids = set(
        db.scalars(select(UserTargetCompany.company_id).where(UserTargetCompany.user_id == user_id))
    )
    target_companies = list(db.scalars(select(Company).where(Company.id.in_(target_company_ids))))
    user_capability_ids = set(
        db.scalars(select(UserCapability.capability_id).where(UserCapability.user_id == user_id))
    )
    roles = db.scalars(select(Role).where(Role.id.in_(target_role_ids)).order_by(Role.title)).all()

    result: list[RoleGaps] = []
    for role in roles:
        # Companies that don't hire for this role aren't part of the denominator.
        base = canonical(db, role)
        hiring_company_ids = sorted(c.id for c in target_companies if company_hires_role(db, c.industry_id, role))
        counts: dict[str, int] = {}
        best_source: dict[str, str] = {}
        considered = no_data = 0
        for company_id in hiring_company_ids:
            resolved = _capabilities_for_pair(db, user_id, company_id, role, base)
            if resolved is None:
                no_data += 1
                continue
            considered += 1
            caps, source = resolved
            for cap_id in caps:
                counts[cap_id] = counts.get(cap_id, 0) + 1
                if SOURCE_RANK[source] > SOURCE_RANK.get(best_source.get(cap_id, ""), -1):
                    best_source[cap_id] = source

        capabilities = {
            c.id: c for c in db.scalars(select(Capability).where(Capability.id.in_(counts)))
        }
        rows = [
            CapabilityGap(
                capability_id=cap_id,
                name=capabilities[cap_id].name,
                kind=capabilities[cap_id].kind,
                required_by_count=count,
                required_by_total=considered,
                gap_ratio=round(count / considered, 4),
                user_has_it=cap_id in user_capability_ids,
                source=best_source[cap_id],
            )
            for cap_id, count in counts.items()
        ]
        rows = [
            r
            for r in rows
            if r.gap_ratio >= min_ratio and not (gaps_only and r.user_has_it)
        ]
        rows.sort(key=lambda r: (-r.required_by_count, r.name))
        result.append(
            RoleGaps(
                role_id=role.id,
                role_title=role.title,
                companies_considered=considered,
                companies_with_no_data=no_data,
                capabilities=rows,
            )
        )
    return SkillGapsOut(user_id=user_id, target_roles=result)
