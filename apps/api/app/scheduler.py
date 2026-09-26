"""Scheduled ingestion: feeds are pulled every hour, and once a day old stories are pruned. Also
runs the push notification jobs — streak reminders, news alerts, role/company update alerts, and a
games nudge — each on its own schedule and its own table row so none of them ever wait on an ingest
or on each other.

Two ways to run it, and both are safe to use together:
  * inside the API process (on by default; set VANTAGE_SCHEDULER=0 to turn it off), or
  * as its own process: `python -m app.scheduler`.
Runs are recorded in `ingest_runs` (feeds) and `notification_runs` (push), so a restart doesn't
repeat a run that just happened and two processes never do the same work twice.

  VANTAGE_INGEST_EVERY_MINUTES     how often to pull the feeds (default 60)
  VANTAGE_DAILY_HOUR_UTC           hour of the day for the daily clean-up (default 3)
  VANTAGE_STREAK_REMINDER_HOUR_UTC hour of the day for the streak-at-risk push (default 14)
  VANTAGE_NEWS_ALERT_HOUR_UTC      hour of the day for the best-critical-story push (default 15)
  VANTAGE_ENTITY_UPDATES_HOUR_UTC  hour of the day for the role/company update push (default 16)
  VANTAGE_GAMES_NUDGE_EVERY_DAYS   how often to check for inactive players to nudge (default 3)
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
from app.models import Article, ArticleTag, Base, IngestRun, NotificationRun, Source, UserInteraction
from app.push import send_entity_updates, send_games_nudges, send_news_alerts, send_streak_reminders

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


def _claim_notification(db: Session, kind: str, now: datetime) -> NotificationRun | None:
    """Same shape as _claim, for notification jobs — their own table, so a slow ingest run never
    blocks a reminder (or the other way round)."""
    running = db.scalars(select(NotificationRun).where(NotificationRun.finished_at.is_(None))).all()
    if any(now - _utc(r.started_at) < STALE_AFTER for r in running):
        return None
    for r in running:
        r.finished_at, r.error = now, "Did not finish (process stopped)"
    run = NotificationRun(kind=kind, started_at=now)
    db.add(run)
    db.commit()
    return run


def is_notification_due(db: Session, kind: str, now: datetime, hour: int) -> bool:
    if now.hour < hour:
        return False
    last = _utc(
        db.scalar(select(NotificationRun.started_at).where(NotificationRun.kind == kind).order_by(NotificationRun.started_at.desc()).limit(1))
    )
    return last is None or last.date() < now.date()


def is_notification_due_every(db: Session, kind: str, now: datetime, every: timedelta) -> bool:
    """Like is_notification_due, for a job that runs on a rolling cadence (e.g. every 3 days) rather
    than once at a fixed hour each day — the games nudge, which would be spammy sent daily."""
    last = _utc(
        db.scalar(select(NotificationRun.started_at).where(NotificationRun.kind == kind).order_by(NotificationRun.started_at.desc()).limit(1))
    )
    return last is None or now - last >= every


def run_streak_reminders(session_factory: sessionmaker, now: datetime | None = None) -> NotificationRun | None:
    """Once a day, nudge anyone with an active streak they haven't touched yet today."""
    now = now or datetime.now(timezone.utc)
    with session_factory() as db:
        run = _claim_notification(db, "streak_reminder", now)
        if run is None:
            log.info("skipping streak_reminder run: another run is in progress")
            return None
        try:
            run.sent = send_streak_reminders(db, now.date())
        except Exception as exc:  # noqa: BLE001 - the scheduler must outlive any one bad run
            db.rollback()
            run.error = f"{type(exc).__name__}: {exc}"[:500]
            log.exception("streak reminder run failed")
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        log.info("streak reminders: %s sent", run.sent)
        return run


def run_news_alerts(session_factory: sessionmaker, now: datetime | None = None) -> NotificationRun | None:
    """Once a day, the single best new critical-tier story for anyone subscribed to 'news'."""
    now = now or datetime.now(timezone.utc)
    with session_factory() as db:
        run = _claim_notification(db, "news_alert", now)
        if run is None:
            log.info("skipping news_alert run: another run is in progress")
            return None
        try:
            run.sent = send_news_alerts(db, now)
        except Exception as exc:  # noqa: BLE001 - the scheduler must outlive any one bad run
            db.rollback()
            run.error = f"{type(exc).__name__}: {exc}"[:500]
            log.exception("news alert run failed")
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        log.info("news alerts: %s sent", run.sent)
        return run


def run_entity_updates(session_factory: sessionmaker, now: datetime | None = None) -> NotificationRun | None:
    """Once a day, new stories about a targeted role or company, for role_update/company_update."""
    now = now or datetime.now(timezone.utc)
    with session_factory() as db:
        run = _claim_notification(db, "entity_updates", now)
        if run is None:
            log.info("skipping entity_updates run: another run is in progress")
            return None
        try:
            run.sent = send_entity_updates(db, now)
        except Exception as exc:  # noqa: BLE001 - the scheduler must outlive any one bad run
            db.rollback()
            run.error = f"{type(exc).__name__}: {exc}"[:500]
            log.exception("entity updates run failed")
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        log.info("entity updates: %s sent", run.sent)
        return run


def run_games_nudges(session_factory: sessionmaker, now: datetime | None = None) -> NotificationRun | None:
    """Every few days, a nudge for anyone subscribed to 'games' who's gone quiet."""
    now = now or datetime.now(timezone.utc)
    with session_factory() as db:
        run = _claim_notification(db, "games_nudge", now)
        if run is None:
            log.info("skipping games_nudge run: another run is in progress")
            return None
        try:
            run.sent = send_games_nudges(db, now)
        except Exception as exc:  # noqa: BLE001 - the scheduler must outlive any one bad run
            db.rollback()
            run.error = f"{type(exc).__name__}: {exc}"[:500]
            log.exception("games nudge run failed")
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        log.info("games nudges: %s sent", run.sent)
        return run


class Scheduler:
    """Checks every 30 seconds whether the hourly or daily job is due."""

    def __init__(
        self,
        session_factory: sessionmaker = SessionLocal,
        *,
        every_minutes: int | None = None,
        daily_hour: int | None = None,
        streak_reminder_hour: int | None = None,
        news_alert_hour: int | None = None,
        entity_updates_hour: int | None = None,
        games_nudge_every_days: int | None = None,
        ingest: Callable[[Session], dict[str, int]] = run_all,
    ) -> None:
        self.session_factory = session_factory
        self.every = timedelta(minutes=every_minutes or int(os.getenv("VANTAGE_INGEST_EVERY_MINUTES", "60")))
        self.daily_hour = daily_hour if daily_hour is not None else int(os.getenv("VANTAGE_DAILY_HOUR_UTC", "3"))
        # Default 14:00 UTC ~= 7:30pm IST: late enough that "you haven't opened it today" is true and
        # relevant, early enough that it isn't a middle-of-the-night ping for the app's India-hours base.
        self.streak_reminder_hour = (
            streak_reminder_hour if streak_reminder_hour is not None else int(os.getenv("VANTAGE_STREAK_REMINDER_HOUR_UTC", "14"))
        )
        # Spread the other daily pushes across the evening so a reader isn't pinged four times back to back.
        self.news_alert_hour = news_alert_hour if news_alert_hour is not None else int(os.getenv("VANTAGE_NEWS_ALERT_HOUR_UTC", "15"))
        self.entity_updates_hour = (
            entity_updates_hour if entity_updates_hour is not None else int(os.getenv("VANTAGE_ENTITY_UPDATES_HOUR_UTC", "16"))
        )
        self.games_nudge_every = timedelta(days=games_nudge_every_days or int(os.getenv("VANTAGE_GAMES_NUDGE_EVERY_DAYS", "3")))
        self.ingest = ingest
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def tick(self, now: datetime | None = None) -> list[str]:
        """Run whatever is due. The daily job includes an ingest, so it replaces that hour's run."""
        now = now or datetime.now(timezone.utc)
        with self.session_factory() as db:
            daily = is_due(db, "daily", now, daily_hour=self.daily_hour)
            hourly = is_due(db, "hourly", now, every=self.every)
            streak_reminder = is_notification_due(db, "streak_reminder", now, self.streak_reminder_hour)
            news_alert = is_notification_due(db, "news_alert", now, self.news_alert_hour)
            entity_updates = is_notification_due(db, "entity_updates", now, self.entity_updates_hour)
            games_nudge = is_notification_due_every(db, "games_nudge", now, self.games_nudge_every)
        ran = []
        for kind, due in (("daily", daily), ("hourly", hourly and not daily)):
            if due and run_job(self.session_factory, kind, self.ingest, now) is not None:
                ran.append(kind)
        for kind, due, runner in (
            ("streak_reminder", streak_reminder, run_streak_reminders),
            ("news_alert", news_alert, run_news_alerts),
            ("entity_updates", entity_updates, run_entity_updates),
            ("games_nudge", games_nudge, run_games_nudges),
        ):
            if due and runner(self.session_factory, now) is not None:
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
            log.info(
                "scheduler started: feeds every %s, daily clean-up at %02d:00 UTC, "
                "streak reminders at %02d:00, news alerts at %02d:00, entity updates at %02d:00 UTC, games nudge every %s",
                self.every,
                self.daily_hour,
                self.streak_reminder_hour,
                self.news_alert_hour,
                self.entity_updates_hour,
                self.games_nudge_every,
            )

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
        notification_runners = {
            "streak_reminder": run_streak_reminders,
            "news_alert": run_news_alerts,
            "entity_updates": run_entity_updates,
            "games_nudge": run_games_nudges,
        }
        if kind in notification_runners:
            # Same due-check tick() uses, so a workflow re-run (retry, manual dispatch the same
            # day) can't double-send — --once used to skip straight to sending, unconditionally.
            now = datetime.now(timezone.utc)
            hour_env = {
                "streak_reminder": "VANTAGE_STREAK_REMINDER_HOUR_UTC",
                "news_alert": "VANTAGE_NEWS_ALERT_HOUR_UTC",
                "entity_updates": "VANTAGE_ENTITY_UPDATES_HOUR_UTC",
            }
            with SessionLocal() as db:
                if kind == "games_nudge":
                    due = is_notification_due_every(db, kind, now, timedelta(days=int(os.getenv("VANTAGE_GAMES_NUDGE_EVERY_DAYS", "3"))))
                else:
                    default_hour = {"streak_reminder": "14", "news_alert": "15", "entity_updates": "16"}[kind]
                    due = is_notification_due(db, kind, now, int(os.getenv(hour_env[kind], default_hour)))
            if not due:
                print(f"{kind}: not due yet")
            else:
                reminder_run = notification_runners[kind](SessionLocal, now)
                print(reminder_run and {"sent": reminder_run.sent})
        else:
            result = run_job(SessionLocal, kind)
            print(result and {"added": result.articles_added, "failed": result.sources_failed, "pruned": result.articles_pruned})
    else:
        scheduler = Scheduler()
        scheduler.start()
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            scheduler.stop()
