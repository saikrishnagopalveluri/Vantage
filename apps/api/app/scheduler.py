"""Scheduled ingestion: feeds are pulled every hour, and once a day old stories are pruned.

Two ways to run it, and both are safe to use together:
  * inside the API process (on by default; set VANTAGE_SCHEDULER=0 to turn it off), or
  * as its own process: `python -m app.scheduler`.
Runs are recorded in `ingest_runs`, so a restart doesn't repeat a run that just happened and two
processes never ingest at the same time.

  VANTAGE_INGEST_EVERY_MINUTES   how often to pull the feeds (default 60)
  VANTAGE_DAILY_HOUR_UTC         hour of the day for the daily clean-up (default 3)
"""

import logging
import os
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import SessionLocal, engine
from app.ingest import MAX_ENTRY_AGE_DAYS, run_all
from app.models import Article, ArticleTag, Base, IngestRun, Source, UserInteraction

log = logging.getLogger("vantage.scheduler")

STALE_AFTER = timedelta(minutes=45)  # a run that never finished stops blocking others after this
TICK_SECONDS = 30


def _utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def prune_articles(db: Session) -> int:
    """Drop stories older than the feed's look-back window, unless somebody saved or opened them."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_ENTRY_AGE_DAYS)
    kept = select(UserInteraction.article_id)
    old = list(db.scalars(select(Article.id).where(Article.published_at < cutoff, Article.id.not_in(kept))))
    for start in range(0, len(old), 500):
        chunk = old[start : start + 500]
        db.execute(delete(ArticleTag).where(ArticleTag.article_id.in_(chunk)))
        db.execute(delete(Article).where(Article.id.in_(chunk)))
    db.commit()
    return len(old)


def _claim(db: Session, kind: str, now: datetime) -> IngestRun | None:
    """Start a run, unless another one is in flight."""
    running = db.scalars(select(IngestRun).where(IngestRun.finished_at.is_(None))).all()
    if any(now - _utc(r.started_at) < STALE_AFTER for r in running):
        return None
    for r in running:  # crashed earlier; close it so it doesn't linger
        r.finished_at, r.error = now, "Did not finish (process stopped)"
    run = IngestRun(kind=kind, started_at=now)
    db.add(run)
    db.commit()
    return run


def run_job(
    session_factory: sessionmaker,
    kind: str,
    ingest: Callable[[Session], dict[str, int]] = run_all,
    now: datetime | None = None,
) -> IngestRun | None:
    """Run one ingest (and, for the daily job, the clean-up). Returns None if another run is in flight."""
    with session_factory() as db:
        run = _claim(db, kind, now or datetime.now(timezone.utc))
        if run is None:
            log.info("skipping %s run: another run is in progress", kind)
            return None
        try:
            per_source = ingest(db)
            run.articles_added = sum(per_source.values())
            run.sources_failed = len(list(db.scalars(select(Source.id).where(Source.last_error.is_not(None)))))
            run.sources_ok = max(0, len(per_source) - run.sources_failed)
            if kind == "daily":
                run.articles_pruned = prune_articles(db)
        except Exception as exc:  # noqa: BLE001 - the scheduler must outlive any one bad run
            db.rollback()
            run.error = f"{type(exc).__name__}: {exc}"[:500]
            log.exception("%s ingest failed", kind)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        log.info("%s ingest: +%s stories, %s sources failing, %s pruned", kind, run.articles_added, run.sources_failed, run.articles_pruned)
        return run


def is_due(db: Session, kind: str, now: datetime, *, every: timedelta | None = None, daily_hour: int | None = None) -> bool:
    # Every kind of run pulls the feeds, so the hourly check looks at the latest run of any kind.
    query = select(IngestRun.started_at).order_by(IngestRun.started_at.desc()).limit(1)
    last = _utc(db.scalar(query if every is not None else query.where(IngestRun.kind == kind)))
    if every is not None:
        return last is None or now - last >= every
    assert daily_hour is not None
    if now.hour < daily_hour:
        return False
    return last is None or last.date() < now.date()


class Scheduler:
    """Checks every 30 seconds whether the hourly or daily job is due."""

    def __init__(
        self,
        session_factory: sessionmaker = SessionLocal,
        *,
        every_minutes: int | None = None,
        daily_hour: int | None = None,
        ingest: Callable[[Session], dict[str, int]] = run_all,
    ) -> None:
        self.session_factory = session_factory
        self.every = timedelta(minutes=every_minutes or int(os.getenv("VANTAGE_INGEST_EVERY_MINUTES", "60")))
        self.daily_hour = daily_hour if daily_hour is not None else int(os.getenv("VANTAGE_DAILY_HOUR_UTC", "3"))
        self.ingest = ingest
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def tick(self, now: datetime | None = None) -> list[str]:
        """Run whatever is due. The daily job includes an ingest, so it replaces that hour's run."""
        now = now or datetime.now(timezone.utc)
        with self.session_factory() as db:
            daily = is_due(db, "daily", now, daily_hour=self.daily_hour)
            hourly = is_due(db, "hourly", now, every=self.every)
        ran = []
        for kind, due in (("daily", daily), ("hourly", hourly and not daily)):
            if due and run_job(self.session_factory, kind, self.ingest, now) is not None:
                ran.append(kind)
        return ran

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                log.exception("scheduler tick failed")
            self._stop.wait(TICK_SECONDS)

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="vantage-scheduler", daemon=True)
            self._thread.start()
            log.info("scheduler started: feeds every %s, daily clean-up at %02d:00 UTC", self.every, self.daily_hour)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)


def enabled() -> bool:
    return os.getenv("VANTAGE_SCHEDULER", "1").lower() not in {"0", "false", "no", "off"}


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Base.metadata.create_all(bind=engine)
    if "--once" in sys.argv:
        kind = sys.argv[sys.argv.index("--once") + 1] if len(sys.argv) > sys.argv.index("--once") + 1 else "hourly"
        result = run_job(SessionLocal, kind)
        print(result and {"added": result.articles_added, "failed": result.sources_failed, "pruned": result.articles_pruned})
    else:
        scheduler = Scheduler()
        scheduler.start()
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            scheduler.stop()
