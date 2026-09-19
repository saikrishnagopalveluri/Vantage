"""Numbers and headlines for the home page. Public: nothing here is about a user."""

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import legal
from app.deps import get_db
from app.models import (
    Article,
    ArticleTag,
    Capability,
    Company,
    Domain,
    IngestRun,
    Role,
    TagType,
    Topic,
)

router = APIRouter(prefix="/public", tags=["public"])

CACHE_SECONDS = 60
HEADLINES = 6


class Headline(BaseModel):
    title: str
    url: str
    source: str
    field: str | None
    published_at: datetime


class Pulse(BaseModel):
    job_titles: int
    companies: int
    skills_and_tools: int
    fields: int
    stories_today: int
    stories_total: int
    sources: int
    updated_at: datetime | None
    headlines: list[Headline]


class LegalInfo(BaseModel):
    terms_version: str
    privacy_version: str
    operator_name: str | None
    contact_email: str | None
    grievance_officer: str | None
    grievance_email: str | None
    postal_address: str | None
    hosting_region: str | None


@router.get("/legal", response_model=LegalInfo)
def legal_info() -> LegalInfo:
    """Which versions of the terms and privacy policy are current, and who to contact."""
    return LegalInfo(terms_version=legal.TERMS_VERSION, privacy_version=legal.PRIVACY_VERSION, **legal.operator())


_cache: dict[str, tuple[float, Pulse]] = {}


def _utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def _field_names(db: Session, article_ids: list[str]) -> dict[str, str]:
    """A story's field of work, but only when a curated topic names it. A skill or role mention alone
    is too loose to label a headline with, so those stories simply get no label."""
    tags = db.execute(
        select(ArticleTag.article_id, ArticleTag.ref_id)
        .where(ArticleTag.article_id.in_(article_ids), ArticleTag.tag_type == TagType.TOPIC)
        .order_by(ArticleTag.weight.desc())
    ).all()
    domain_of = dict(db.execute(select(Topic.id, Topic.domain_id).where(Topic.id.in_({ref for _, ref in tags}))).all())
    names = {d.id: d.name for d in db.scalars(select(Domain))}
    out: dict[str, str] = {}
    for article_id, ref in tags:
        if article_id not in out and domain_of.get(ref):
            out[article_id] = names[domain_of[ref]]
    return out


@router.get("/pulse", response_model=Pulse)
def pulse(db: Session = Depends(get_db)) -> Pulse:
    now = time.monotonic()
    hit = _cache.get("pulse")
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]

    count = lambda model: db.scalar(select(func.count()).select_from(model)) or 0  # noqa: E731
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = list(db.scalars(select(Article).order_by(Article.published_at.desc()).limit(60)))
    picked, seen_sources = [], set()
    for article in recent:  # a mix of publishers, newest first
        if article.source_id not in seen_sources and not article.source.name.endswith("(placeholder)"):
            seen_sources.add(article.source_id)
            picked.append(article)
        if len(picked) == HEADLINES:
            break
    fields = _field_names(db, [a.id for a in picked])
    updated = db.scalar(select(func.max(IngestRun.finished_at)))

    result = Pulse(
        job_titles=count(Role),
        companies=count(Company),
        skills_and_tools=count(Capability),
        fields=count(Domain),
        stories_today=db.scalar(select(func.count()).select_from(Article).where(Article.published_at >= since)) or 0,
        stories_total=count(Article),
        sources=db.scalar(select(func.count(func.distinct(Article.source_id)))) or 0,
        updated_at=_utc(updated),
        headlines=[
            Headline(
                title=a.title,
                url=a.url,
                source=a.source.name,
                field=fields.get(a.id),
                published_at=_utc(a.published_at),
            )
            for a in picked
        ],
    )
    _cache["pulse"] = (now, result)
    return result
