from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.badges import compute_badges
from app.deps import get_caller_id, get_db, require_self
from app.models import InteractionAction, UserEngagement, UserInteraction, UserStreak
from app.schemas import BadgeOut, BadgesOut, TimeIn

router = APIRouter(prefix="/badges", tags=["badges"])


def _badges_out(db: Session, user_id: str) -> BadgesOut:
    streak = db.get(UserStreak, user_id)
    engagement = db.get(UserEngagement, user_id)
    articles_read = db.scalar(
        select(func.count()).select_from(UserInteraction).where(
            UserInteraction.user_id == user_id, UserInteraction.action == InteractionAction.READ
        )
    ) or 0
    states = compute_badges(
        longest_streak=streak.longest_streak if streak else 0,
        articles_read=articles_read,
        active_seconds=engagement.active_seconds if engagement else 0,
    )
    return BadgesOut(badges=[BadgeOut(**vars(s)) for s in states])


@router.get("/{user_id}", response_model=BadgesOut)
def get_badges(user_id: str, db: Session = Depends(get_db), caller_id: str = Depends(get_caller_id)) -> BadgesOut:
    require_self(user_id, caller_id)
    return _badges_out(db, user_id)


@router.post("/{user_id}/time", response_model=BadgesOut)
def log_time(
    user_id: str,
    body: TimeIn,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> BadgesOut:
    """A heartbeat from the feed page while it's visible. Clamped per-call (see TimeIn) so a stray or
    replayed request can't inflate the total by much."""
    require_self(user_id, caller_id)
    row = db.get(UserEngagement, user_id)
    if row is None:
        row = UserEngagement(user_id=user_id, active_seconds=0)
        db.add(row)
    row.active_seconds += body.seconds
    db.commit()
    return _badges_out(db, user_id)
