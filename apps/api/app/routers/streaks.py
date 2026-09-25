from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_caller_id, get_db, require_self
from app.models import UserStreak
from app.schemas import StreakOut
from app.streaks import StreakState, apply_touch

router = APIRouter(prefix="/streaks", tags=["streaks"])


def _out(streak: UserStreak | None, today) -> StreakOut:
    if streak is None:
        return StreakOut(current_streak=0, longest_streak=0, active_today=False)
    return StreakOut(current_streak=streak.current_streak, longest_streak=streak.longest_streak, active_today=streak.last_active_on == today)


@router.get("/{user_id}", response_model=StreakOut)
def get_streak(user_id: str, db: Session = Depends(get_db), caller_id: str = Depends(get_caller_id)) -> StreakOut:
    require_self(user_id, caller_id)
    today = datetime.now(timezone.utc).date()
    return _out(db.get(UserStreak, user_id), today)


@router.post("/{user_id}/touch", response_model=StreakOut)
def touch_streak(
    user_id: str,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> StreakOut:
    """Counts today as a visit. Safe to call on every page load: a second touch on the same day is a
    no-op, so nothing is lost by calling it more than once."""
    require_self(user_id, caller_id)
    today = datetime.now(timezone.utc).date()
    row = db.get(UserStreak, user_id)
    state = StreakState(
        current_streak=row.current_streak if row else 0,
        longest_streak=row.longest_streak if row else 0,
        last_active_on=row.last_active_on if row else None,
    )
    new_state, changed = apply_touch(state, today)
    if changed:
        if row is None:
            row = UserStreak(user_id=user_id)
            db.add(row)
        row.current_streak = new_state.current_streak
        row.longest_streak = new_state.longest_streak
        row.last_active_on = new_state.last_active_on
        db.commit()
    return _out(row, today)
