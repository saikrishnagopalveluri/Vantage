from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.deps import get_caller_id, get_db, require_self
from app.feed import Lens, load_context, rank
from app.summarize import build_brief
from app.models import Article, InteractionAction, UserInteraction, UserProfile
from app.schemas import (
    Brief,
    FeedItem,
    FeedOut,
    FeedSummary,
    InteractionIn,
    InteractionOut,
    SavedItem,
    SourceRef,
)

router = APIRouter(prefix="/feed", tags=["feed"])

ACTION_TO_INTERACTION = {
    "save": (InteractionAction.SAVED, True),
    "unsave": (InteractionAction.SAVED, False),
    "dismiss": (InteractionAction.DISMISSED, True),
    "undismiss": (InteractionAction.DISMISSED, False),
    "read": (InteractionAction.READ, True),
}


def _profile(db: Session, user_id: str) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


_MATCH_LABELS = {"companies": "Companies", "roles": "Roles", "capabilities": "Skills and tools", "industries": "Industries", "topics": "Topics"}


def brief_for(article: Article, matched: dict[str, list[str]]) -> Brief:
    """The stored brief, or one built now for articles ingested before briefs existed."""
    data = article.brief or build_brief(article.title, article.body or article.summary)
    pointers = list(data["pointers"])
    if not pointers:  # a very short excerpt: at least say what it is about, from the taxonomy match
        pointers = [
            f"{_MATCH_LABELS.get(kind, kind)}: {', '.join(names[:4])}"
            for kind, names in matched.items()
            if names
        ][:3]
    return Brief(paragraphs=data["paragraphs"], pointers=pointers, note=data.get("note"))


def _has(db: Session, user_id: str, article_id: str, action: InteractionAction) -> bool:
    return db.get(UserInteraction, (user_id, article_id, action)) is not None


@router.get("/{user_id}", response_model=FeedOut)
def get_feed(
    user_id: str,
    lens: Lens = "for_you",
    domain_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    as_of: datetime | None = None,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> FeedOut:
    """`as_of` pins ranking and candidate selection to a moment in time. The first page of a
    session leaves it out and gets today's ranking back in the response; every later page of
    that same scroll echoes it back, so a story ingested (or re-scored) mid-scroll can't shift
    the ranked order under the reader's feet and reappear as a "new" story a few pages later."""
    require_self(user_id, caller_id)
    profile = _profile(db, user_id)
    now = as_of.astimezone(timezone.utc) if as_of else datetime.now(timezone.utc)
    ranked = rank(db, profile, load_context(db, profile), lens, now=now, domain_id=domain_id)

    page = ranked[offset : offset + limit]
    saved = set(
        db.scalars(
            select(UserInteraction.article_id).where(
                UserInteraction.user_id == user_id,
                UserInteraction.action == InteractionAction.SAVED,
                UserInteraction.article_id.in_([r.article.id for r in page]),
            )
        )
    )
    count = lambda tier: sum(1 for r in ranked if r.tier == tier)  # noqa: E731
    return FeedOut(
        lens=lens,
        summary=FeedSummary(
            total=len(ranked),
            critical=count("critical"),
            relevant=count("relevant"),
            explore=count("explore"),
        ),
        items=[
            FeedItem(
                id=r.article.id,
                title=r.article.title,
                url=r.article.url,
                summary=r.article.summary,
                brief=brief_for(r.article, r.matched),
                source=SourceRef(name=r.article.source.name, authority=r.article.source.authority),
                also_covered_by=r.also_covered_by,
                published_at=r.published,
                score=r.score,
                tier=r.tier,
                why_this_matters=r.why,
                action=r.action,
                matched=r.matched,
                domains=r.domains,
                newsletter=r.newsletter,
                saved=r.article.id in saved,
            )
            for r in page
        ],
        offset=offset,
        has_more=offset + limit < len(ranked),
        as_of=now,
    )


@router.post("/{user_id}/interaction", response_model=InteractionOut)
def record_interaction(
    user_id: str,
    body: InteractionIn,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> InteractionOut:
    require_self(user_id, caller_id)
    _profile(db, user_id)
    if db.get(Article, body.article_id) is None:
        raise HTTPException(status_code=404, detail="Article not found")

    action, present = ACTION_TO_INTERACTION[body.action]
    exists = _has(db, user_id, body.article_id, action)
    if present and not exists:
        db.add(UserInteraction(user_id=user_id, article_id=body.article_id, action=action))
    elif not present and exists:
        db.execute(
            delete(UserInteraction).where(
                UserInteraction.user_id == user_id,
                UserInteraction.article_id == body.article_id,
                UserInteraction.action == action,
            )
        )
    db.commit()
    return InteractionOut(
        article_id=body.article_id,
        saved=_has(db, user_id, body.article_id, InteractionAction.SAVED),
        dismissed=_has(db, user_id, body.article_id, InteractionAction.DISMISSED),
    )


@router.get("/{user_id}/saved", response_model=list[SavedItem])
def get_saved(
    user_id: str,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> list[SavedItem]:
    require_self(user_id, caller_id)
    _profile(db, user_id)
    rows = db.execute(
        select(Article, UserInteraction.created_at)
        .join(UserInteraction, UserInteraction.article_id == Article.id)
        .where(
            UserInteraction.user_id == user_id,
            UserInteraction.action == InteractionAction.SAVED,
        )
        .order_by(UserInteraction.created_at.desc())
    ).all()
    return [
        SavedItem(
            id=a.id,
            title=a.title,
            url=a.url,
            summary=a.summary,
            source=SourceRef(name=a.source.name, authority=a.source.authority),
            published_at=a.published_at,
            saved_at=saved_at,
        )
        for a, saved_at in rows
    ]
