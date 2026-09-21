"""Feed ingestion: official RSS/Atom feeds only. Stores title, link, publisher, a short teaser and
up to a page of the feed's own text for the brief; never the full article. Articles that match
nothing in the taxonomy are dropped."""

import html
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import feedparser
import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app.models import Article, ArticleTag, Base, Source, TagType, UserInteraction
from app.seed_data.sources import NEWSLETTER_NAMES
from app.summarize import build_brief
from app.tagging import TagIndex, build_index, is_relevant_enough, tag_article

SUMMARY_MAX_CHARS = 300
BODY_MAX_CHARS = 1600
# Some feeds serve their whole archive; the feed only ever looks back this far, so store no more.
MAX_ENTRY_AGE_DAYS = 60
USER_AGENT = "VantageBot/0.1 (+personal research; respects robots.txt)"


@dataclass(frozen=True)
class FeedEntry:
    title: str
    url: str
    summary: str
    published_at: datetime
    body: str = ""


def _plain(raw: str | None) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    return re.sub(r"\s+", " ", text).strip()


def clean_summary(raw: str | None) -> str:
    text = _plain(raw)
    if len(text) <= SUMMARY_MAX_CHARS:
        return text
    return text[: SUMMARY_MAX_CHARS - 1].rsplit(" ", 1)[0] + "…"


def clean_body(raw: str | None) -> str:
    text = _plain(raw)
    return text if len(text) <= BODY_MAX_CHARS else text[:BODY_MAX_CHARS].rsplit(" ", 1)[0]


def parse_feed(content: str | bytes) -> list[FeedEntry]:
    entries = []
    now = datetime.now(timezone.utc)
    parsed = feedparser.parse(content)
    site = (parsed.feed.get("link") or "").strip()
    for item in parsed.entries:
        title = (item.get("title") or "").strip()
        url = (item.get("link") or "").strip()
        if not url and site and item.get("id") and item.get("enclosures"):
            # A podcast feed: episodes have audio but no page of their own, so link to the show's site
            # and keep the episode id in the fragment, which keeps each episode's address unique.
            url = f"{site.rstrip('/')}/#{item['id']}"
        # The link is rendered as <a href>; a feed must not be able to smuggle in javascript: or data: URLs.
        if not title or not url or urlparse(url).scheme not in ("http", "https"):
            continue
        stamp = item.get("published_parsed") or item.get("updated_parsed")
        published = datetime(*stamp[:6], tzinfo=timezone.utc) if stamp else now
        blocks = item.get("content") or []
        full = blocks[0].get("value") if blocks else None
        entries.append(
            FeedEntry(
                title=_plain(title),
                url=url,
                summary=clean_summary(item.get("summary")),
                published_at=min(published, now),
                body=clean_body(full or item.get("summary")),
            )
        )
    return entries


def tag_story(index: TagIndex, source_name: str, title: str, summary: str, body: str = "") -> tuple[dict, bool]:
    """Tags for a story, and whether it is relevant enough to keep. A newsletter essay often has a
    metaphorical headline and a one-line teaser, so it is read on its opening text too, and a single real
    match is enough. News keeps the stricter rule."""
    letter = source_name in NEWSLETTER_NAMES
    tags = tag_article(index, title, f"{summary} {body[:1200]}" if letter else summary)
    keep = is_relevant_enough(tags) or (letter and any(tag[0] != TagType.INDUSTRY for tag in tags))
    return tags, keep


def ingest_entries(
    db: Session, source: Source, entries: list[FeedEntry], index: TagIndex | None = None
) -> int:
    """Store new, taxonomy-relevant entries. Returns how many articles were added."""
    index = index or build_index(db)
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_ENTRY_AGE_DAYS)
    entries = [e for e in entries if e.published_at >= cutoff]
    known = set(db.scalars(select(Article.url).where(Article.url.in_([e.url for e in entries]))))
    added = 0
    for entry in entries:
        if entry.url in known:
            continue
        tags, keep = tag_story(index, source.name, entry.title, entry.summary, entry.body)
        if not keep:
            continue
        known.add(entry.url)
        article = Article(
            source_id=source.id,
            title=entry.title,
            url=entry.url,
            summary=entry.summary,
            body=entry.body,
            brief=build_brief(entry.title, entry.body or entry.summary),
            published_at=entry.published_at,
        )
        db.add(article)
        db.flush()
        db.add_all(
            ArticleTag(article_id=article.id, tag_type=t, ref_id=ref, weight=weight)
            for (t, ref), weight in tags.items()
        )
        added += 1
    db.commit()
    return added


def retag_all(db: Session) -> dict[str, int]:
    """Re-run tagging over stored articles after the taxonomy changed. Articles that no longer
    pass the relevance gate are removed unless somebody saved or read them."""
    index = build_index(db)
    touched = {i for i in db.scalars(select(UserInteraction.article_id))}
    kept = removed = 0
    for article in db.scalars(select(Article)):
        tags, keep = tag_story(index, article.source.name, article.title, article.summary, article.body or "")
        if not keep and article.id not in touched:
            db.execute(delete(ArticleTag).where(ArticleTag.article_id == article.id))
            db.delete(article)
            removed += 1
            continue
        db.execute(delete(ArticleTag).where(ArticleTag.article_id == article.id))
        db.add_all(ArticleTag(article_id=article.id, tag_type=t, ref_id=ref, weight=w) for (t, ref), w in tags.items())
        article.brief = build_brief(article.title, article.body or article.summary)
        article.title = _plain(article.title)
        kept += 1
    db.commit()
    return {"kept": kept, "removed": removed}


def apply_result(
    db: Session, source: Source, content: bytes | None, error: Exception | None, index: TagIndex
) -> int:
    """Record one fetch on its source. A failing source is noted on the source, never raised."""
    try:
        if error is not None:
            raise error
        added = ingest_entries(db, source, parse_feed(content or b""), index)
        source.last_error = None
    except Exception as exc:  # noqa: BLE001 - one bad feed must not stop the others
        db.rollback()
        source.last_error = f"{type(exc).__name__}: {exc}"[:500]
        added = 0
    source.last_fetched_at = datetime.now(timezone.utc)
    db.commit()
    return added


def fetch_source(db: Session, source: Source, client: httpx.Client, index: TagIndex) -> int:
    """Fetch one source and ingest it."""
    try:
        response = client.get(source.feed_url)
        response.raise_for_status()
        content, error = response.content, None
    except Exception as exc:  # noqa: BLE001
        content, error = None, exc
    return apply_result(db, source, content, error, index)


FETCH_WORKERS = 8


def run_all(db: Session, client: httpx.Client | None = None) -> dict[str, int]:
    """Fetch every feed concurrently (the slow part), then tag and store them one at a time."""
    index = build_index(db)
    owns_client = client is None
    client = client or httpx.Client(
        timeout=15, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    )

    def get(target: tuple[str, str]) -> tuple[str, bytes | None, Exception | None]:
        source_id, url = target
        try:
            response = client.get(url)
            response.raise_for_status()
            return source_id, response.content, None
        except Exception as exc:  # noqa: BLE001
            return source_id, None, exc

    try:
        sources = list(db.scalars(select(Source).where(Source.feed_url.like("http%"))))
        targets = [(s.id, s.feed_url) for s in sources]
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
            fetched = {sid: (content, error) for sid, content, error in pool.map(get, targets)}
        return {s.name: apply_result(db, s, *fetched[s.id], index) for s in sources}
    finally:
        if owns_client:
            client.close()


if __name__ == "__main__":
    import sys

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if "--retag" in sys.argv:
            print(retag_all(session))
            raise SystemExit
        for name, count in run_all(session).items():
            print(f"{name}: +{count}")
        for source in session.scalars(select(Source).where(Source.last_error.is_not(None))):
            print(f"FAILED {source.name}: {source.last_error}")
