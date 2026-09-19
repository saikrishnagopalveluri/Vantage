"""Data rights: download everything held about you, or delete it. Serves the access, portability and
erasure rights in the GDPR and the access and erasure rights in India's DPDP Act."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import auth
from app.deps import get_caller_id, get_db
from app.models import (
    JD,
    Account,
    Article,
    Base,
    Capability,
    Company,
    Consent,
    Domain,
    Industry,
    JDCapability,
    ProfileEvent,
    Role,
    User,
    UserCapability,
    UserDomain,
    UserInteraction,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)

router = APIRouter(prefix="/privacy", tags=["privacy"])


class DeleteIn(BaseModel):
    password: str | None = Field(default=None, max_length=auth.MAX_PASSWORD)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def collect(db: Session, user_id: str) -> dict:
    """Everything stored about one person, in words rather than ids."""

    def names(model, attr, ids):
        return sorted(getattr(r, attr) for r in db.scalars(select(model).where(model.id.in_(list(ids)))))

    account = db.get(Account, user_id)
    profile = db.get(UserProfile, user_id)
    consents = db.scalars(select(Consent).where(Consent.user_id == user_id).order_by(Consent.given_at)).all()
    ids = lambda model, col: {  # noqa: E731
        getattr(r, col) for r in db.scalars(select(model).where(model.user_id == user_id))
    }

    jds = []
    for jd in db.scalars(select(JD).where(JD.user_id == user_id).order_by(JD.created_at)):
        skill_ids = {c for c in db.scalars(select(JDCapability.capability_id).where(JDCapability.jd_id == jd.id))}
        jds.append(
            {
                "title": jd.title,
                "company": jd.company.name if jd.company else jd.company_name,
                "role": jd.role.title if jd.role else None,
                "text": jd.raw_text,
                "skills_found": names(Capability, "name", skill_ids),
                "added_at": _iso(jd.created_at),
            }
        )

    interactions = []
    for it in db.scalars(select(UserInteraction).where(UserInteraction.user_id == user_id).order_by(UserInteraction.created_at)):
        article = db.get(Article, it.article_id)
        interactions.append(
            {
                "action": it.action.value,
                "story": article.title if article else None,
                "link": article.url if article else None,
                "at": _iso(it.created_at),
            }
        )

    return {
        "exported_at": _iso(datetime.now(timezone.utc)),
        "about_this_file": "Everything Vantage stores about you. Passwords are never included, only kept as a salted hash.",
        "user_id": user_id,
        "account": None if account is None else {"email": account.email, "created_at": _iso(account.created_at)},
        "consents": [
            {
                "terms_version": c.terms_version,
                "privacy_version": c.privacy_version,
                "confirmed_18_or_older": c.over_18,
                "how": c.source,
                "at": _iso(c.given_at),
            }
            for c in consents
        ],
        "profile": None
        if profile is None
        else {
            "status": profile.profile_status.value,
            "current_role": profile.current_role.title if profile.current_role else None,
            "current_company": profile.current_company.name if profile.current_company else None,
            "current_industry": profile.current_industry.name if profile.current_industry else None,
            "placed_at": _iso(profile.placed_at),
            "current_role_started_at": _iso(profile.current_role_started_at),
        },
        "fields_followed": names(Domain, "name", ids(UserDomain, "domain_id")),
        "target_roles": names(Role, "title", ids(UserTargetRole, "role_id")),
        "target_companies": names(Company, "name", ids(UserTargetCompany, "company_id")),
        "skills_and_tools_you_have": names(Capability, "name", ids(UserCapability, "capability_id")),
        "story_activity": interactions,
        "job_descriptions": jds,
        "profile_history": [
            {"event": e.event_type, "details": e.payload, "at": _iso(e.created_at)}
            for e in db.scalars(select(ProfileEvent).where(ProfileEvent.user_id == user_id).order_by(ProfileEvent.created_at))
        ],
        "industries_named_in_profile": names(Industry, "name", {profile.current_industry_id} if profile and profile.current_industry_id else set()),
    }


@router.get("/export")
def export_my_data(user_id: str = Depends(get_caller_id), db: Session = Depends(get_db)) -> JSONResponse:
    return JSONResponse(
        collect(db, user_id),
        headers={"Content-Disposition": 'attachment; filename="vantage-my-data.json"', "Cache-Control": "no-store"},
    )


def erase(db: Session, user_id: str) -> None:
    """Delete every row that belongs to this person. Any table with a `user_id` column is covered,
    so a table added later can't be forgotten."""
    jd_ids = list(db.scalars(select(JD.id).where(JD.user_id == user_id)))
    if jd_ids:
        db.execute(delete(JDCapability).where(JDCapability.jd_id.in_(jd_ids)))
    for table in reversed(Base.metadata.sorted_tables):
        if "user_id" in table.c and table.name != "users":
            db.execute(delete(table).where(table.c.user_id == user_id))
    db.execute(delete(User).where(User.id == user_id))
    db.commit()


@router.delete("/account", status_code=204)
def delete_my_data(
    request: Request,
    response: Response,
    body: DeleteIn | None = None,
    user_id: str = Depends(get_caller_id),
    db: Session = Depends(get_db),
) -> None:
    account = db.get(Account, user_id)
    if account is not None:
        # Deleting is permanent, so an account has to prove it is the owner again, not just hold a cookie.
        key = f"delete:{account.email}"
        wait = auth.throttle.retry_after(key)
        if wait:
            raise HTTPException(status_code=429, detail="Too many tries. Wait a few minutes and try again.", headers={"Retry-After": str(wait)})
        if not body or not body.password or not auth.verify_password(body.password, account.password_hash):
            auth.throttle.fail(key)
            raise HTTPException(status_code=403, detail="Enter your password to confirm.")
        auth.throttle.clear(key)
    erase(db, user_id)
    response.delete_cookie(auth.COOKIE_NAME, path="/")
