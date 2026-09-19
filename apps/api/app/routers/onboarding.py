from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import get_caller_id, get_db
from app.legal import record_consent
from app.models import (
    Account,
    Company,
    ProfileStatus,
    Role,
    User,
    UserCapability,
    UserDomain,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)
from app.schemas import OnboardingIn, ProfileOut
from app.services import profile_out, resolve_industry, unique_ids, unknown_target_ids

router = APIRouter(tags=["onboarding"])


@router.post("/onboarding", response_model=ProfileOut, status_code=201)
def onboard(
    body: OnboardingIn,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_caller_id),
) -> ProfileOut:
    """Create the caller's user + profile in one transaction.

    Students send targets only. Someone already working also sends `current`, which starts
    them as `placed` (with no `placed_at`: they were never placed through Vantage).
    """
    if db.get(User, user_id) is not None:
        raise HTTPException(status_code=409, detail="User is already onboarded")

    domain_ids = unique_ids(body.domain_ids)
    role_ids = unique_ids(body.target_role_ids)
    company_ids = unique_ids(body.target_company_ids)
    capability_ids = unique_ids(body.capability_ids)

    unknown = unknown_target_ids(db, role_ids, company_ids, capability_ids, domain_ids)
    current_company = current_role = None
    if body.current is not None:
        current_company = db.get(Company, body.current.company_id)
        current_role = db.get(Role, body.current.role_id)
        if current_company is None:
            unknown["current.company_id"] = [body.current.company_id]
        if current_role is None:
            unknown["current.role_id"] = [body.current.role_id]
    unknown = {field: ids for field, ids in unknown.items() if ids}
    if unknown:
        raise HTTPException(status_code=422, detail={"unknown_ids": unknown})

    profile = UserProfile(user_id=user_id, profile_status=ProfileStatus.TARGETING)
    if body.current is not None:
        industry = resolve_industry(db, current_company, body.current.industry_id)
        profile.profile_status = ProfileStatus.PLACED
        profile.current_role_id = current_role.id
        profile.current_company_id = current_company.id
        profile.current_industry_id = industry.id

    if db.get(Account, user_id) is None:
        record_consent(db, user_id, body.consent, "guest")
    db.add(User(id=user_id))
    db.flush()
    db.add(profile)
    db.add_all(UserDomain(user_id=user_id, domain_id=i) for i in domain_ids)
    db.add_all(UserTargetRole(user_id=user_id, role_id=i) for i in role_ids)
    db.add_all(UserTargetCompany(user_id=user_id, company_id=i) for i in company_ids)
    db.add_all(UserCapability(user_id=user_id, capability_id=i) for i in capability_ids)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # lost a race with a concurrent onboarding of the same user
        raise HTTPException(status_code=409, detail="User is already onboarded")
    db.refresh(profile)
    return profile_out(db, profile)
