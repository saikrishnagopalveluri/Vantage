from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_caller_id, get_db, require_self
from app.models import PushSubscription
from app.push import CATEGORIES, vapid_config
from app.schemas import (
    PushCategoriesIn,
    PushSubscribeIn,
    PushSubscriptionOut,
    PushUnsubscribeIn,
)

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/categories")
def list_categories() -> dict[str, str]:
    """The category ids and their display labels — the source of truth the frontend's preference
    toggles are built from, so a new category only needs adding here."""
    return CATEGORIES


@router.get("/{user_id}/public-key")
def public_key(user_id: str, caller_id: str = Depends(get_caller_id)) -> dict[str, str | None]:
    require_self(user_id, caller_id)
    config = vapid_config()
    return {"public_key": config[0] if config else None}


@router.get("/{user_id}", response_model=list[PushSubscriptionOut])
def list_subscriptions(user_id: str, db: Session = Depends(get_db), caller_id: str = Depends(get_caller_id)) -> list[PushSubscription]:
    require_self(user_id, caller_id)
    return list(db.scalars(select(PushSubscription).where(PushSubscription.user_id == user_id)))


@router.post("/{user_id}/subscribe", response_model=PushSubscriptionOut, status_code=201)
def subscribe(
    user_id: str,
    body: PushSubscribeIn,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> PushSubscription:
    """Registering the same endpoint again (a browser re-subscribing) updates that row in place
    rather than duplicating it — the endpoint is the browser's own identity for this device."""
    require_self(user_id, caller_id)
    existing = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if existing is not None:
        if existing.user_id != user_id:
            raise HTTPException(status_code=409, detail="That device is already subscribed under a different profile.")
        existing.p256dh, existing.auth, existing.categories = body.keys.p256dh, body.keys.auth, body.categories
        db.commit()
        return existing
    sub = PushSubscription(user_id=user_id, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth, categories=body.categories)
    db.add(sub)
    db.commit()
    return sub


@router.put("/{user_id}/categories", response_model=PushSubscriptionOut)
def set_categories(
    user_id: str,
    body: PushCategoriesIn,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> PushSubscription:
    require_self(user_id, caller_id)
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint, PushSubscription.user_id == user_id))
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription for that device.")
    sub.categories = body.categories
    db.commit()
    return sub


@router.post("/{user_id}/unsubscribe", status_code=204)
def unsubscribe(
    user_id: str,
    body: PushUnsubscribeIn,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> None:
    require_self(user_id, caller_id)
    db.execute(
        PushSubscription.__table__.delete().where(PushSubscription.endpoint == body.endpoint, PushSubscription.user_id == user_id)
    )
    db.commit()
