from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_caller_id, get_db, require_self
from app.quiz import make_questions

router = APIRouter(prefix="/quiz", tags=["quiz"])

MAX_EXCLUDED = 400


class QuizQuestion(BaseModel):
    id: str  # a stable key, so a player can ask for questions they have not seen
    kind: str
    prompt: str
    context: str | None = None  # a headline to read, when the question is about one
    options: list[str]
    answer: int  # index into options
    explain: str
    field: str | None = None
    level: int


class QuizBatch(BaseModel):
    level: int
    questions: list[QuizQuestion]


@router.get("/{user_id}", response_model=QuizBatch)
def next_questions(
    user_id: str,
    count: int = Query(default=8, ge=1, le=20),
    level: int = Query(default=1, ge=1, le=10),
    seed: int | None = None,
    exclude: str = Query(default="", max_length=6000),
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> QuizBatch:
    """A batch of pop-quiz questions at a level, leaving out the ones already seen. Works for anyone signed in or
    a guest, and leans on the player's own roles, companies and fields when they have set them."""
    require_self(user_id, caller_id)
    seen = {k for k in exclude.split(",") if k}
    seen = set(list(seen)[:MAX_EXCLUDED])
    questions = make_questions(db, user_id, count, level, seed, seen)
    return QuizBatch(level=level, questions=[QuizQuestion(**q.as_dict()) for q in questions])
