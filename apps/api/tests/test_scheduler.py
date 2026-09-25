from datetime import date, datetime, timedelta, timezone

from app.models import Article, ArticleTag, IngestRun, InteractionAction, NotificationRun, PushSubscription, Source, UserInteraction, UserStreak
from app.scheduler import STALE_AFTER, Scheduler, is_due, prune_articles, run_job, run_streak_reminders

UTC = timezone.utc
NOW = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)


def fake_ingest(added=3):
    calls = []

    def ingest(db):
        calls.append(1)
        return {"Marketing Dive": added, "Adweek": 0}

    ingest.calls = calls
    return ingest


def test_hourly_job_runs_when_due_and_not_again_within_the_hour(session_factory):
    ingest = fake_ingest()
    scheduler = Scheduler(session_factory, every_minutes=60, daily_hour=3, ingest=ingest)
    assert scheduler.tick(NOW) == ["daily"]  # past 03:00 UTC and never run today: the daily job also ingests
    assert scheduler.tick(NOW + timedelta(minutes=20)) == []
    assert scheduler.tick(NOW + timedelta(minutes=61)) == ["hourly"]
    assert len(ingest.calls) == 2
    with session_factory() as db:
        runs = db.query(IngestRun).order_by(IngestRun.started_at).all()
        assert [r.kind for r in runs] == ["daily", "hourly"]
        assert runs[0].articles_added == 3 and runs[0].finished_at is not None and runs[0].error is None


def test_daily_job_waits_for_its_hour_and_runs_once_a_day(session_factory):
    scheduler = Scheduler(session_factory, every_minutes=10_000, daily_hour=3, streak_reminder_hour=23, ingest=fake_ingest())
    early = datetime(2026, 9, 20, 1, 0, tzinfo=UTC)
    with session_factory() as db:
        assert is_due(db, "daily", early, daily_hour=3) is False
    assert scheduler.tick(datetime(2026, 9, 20, 3, 5, tzinfo=UTC)) == ["daily"]
    assert scheduler.tick(datetime(2026, 9, 20, 22, 0, tzinfo=UTC)) == []
    assert scheduler.tick(datetime(2026, 9, 21, 3, 5, tzinfo=UTC)) == ["daily"]


def test_streak_reminder_waits_for_its_hour_runs_once_a_day_and_reaches_an_at_risk_streak(session_factory, monkeypatch):
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-private-key")
    sent: list[str] = []
    monkeypatch.setattr("app.push.webpush", lambda **kw: sent.append(kw["subscription_info"]["endpoint"]))

    scheduler = Scheduler(session_factory, every_minutes=10_000, daily_hour=23, streak_reminder_hour=14, ingest=fake_ingest())
    with session_factory() as db:
        db.add(UserStreak(user_id="u1", current_streak=5, longest_streak=5, last_active_on=date(2026, 9, 19)))
        db.add(PushSubscription(user_id="u1", endpoint="https://push.test/u1", p256dh="a", auth="b", categories=["streak"]))
        db.commit()

    assert "streak_reminder" not in scheduler.tick(datetime(2026, 9, 20, 10, 0, tzinfo=UTC))  # before the reminder hour
    assert scheduler.tick(datetime(2026, 9, 20, 14, 5, tzinfo=UTC)) == ["streak_reminder"]
    assert sent == ["https://push.test/u1"]
    assert scheduler.tick(datetime(2026, 9, 20, 20, 0, tzinfo=UTC)) == []  # not again the same day
    with session_factory() as db:
        run = db.query(NotificationRun).filter_by(kind="streak_reminder").one()
        assert run.sent == 1 and run.finished_at is not None


def test_two_processes_never_send_streak_reminders_at_once(session_factory):
    with session_factory() as db:
        db.add(NotificationRun(kind="streak_reminder", started_at=datetime.now(UTC)))
        db.commit()
    assert run_streak_reminders(session_factory) is None


def test_two_processes_never_ingest_at_once_but_a_crashed_run_does_not_block_forever(session_factory):
    ingest = fake_ingest()
    with session_factory() as db:
        db.add(IngestRun(kind="hourly", started_at=datetime.now(UTC)))
        db.commit()
    assert run_job(session_factory, "hourly", ingest) is None and ingest.calls == []

    with session_factory() as db:
        db.query(IngestRun).update({"started_at": datetime.now(UTC) - STALE_AFTER - timedelta(minutes=1)})
        db.commit()
    assert run_job(session_factory, "hourly", ingest) is not None
    with session_factory() as db:
        assert db.query(IngestRun).filter(IngestRun.error.like("Did not finish%")).count() == 1


def test_a_failing_ingest_is_recorded_and_does_not_raise(session_factory):
    def broken(db):
        raise RuntimeError("feeds are down")

    run = run_job(session_factory, "hourly", broken)
    assert run.error == "RuntimeError: feeds are down" and run.finished_at is not None


def test_prune_removes_old_stories_but_keeps_saved_ones(db, world):
    source = Source(name="S", feed_url="https://f.test/rss", authority=3)
    db.add(source)
    db.commit()
    old = datetime.now(UTC) - timedelta(days=90)
    keep, drop, fresh = (
        Article(source_id=source.id, title=t, url=f"https://x.test/{t}", published_at=when)
        for t, when in (("keep", old), ("drop", old), ("fresh", datetime.now(UTC)))
    )
    db.add_all([keep, drop, fresh])
    db.commit()
    db.add(UserInteraction(user_id="u1", article_id=keep.id, action=InteractionAction.SAVED))
    db.add(ArticleTag(article_id=drop.id, tag_type="topic", ref_id="t"))
    db.commit()

    assert prune_articles(db) == 1
    assert {a.title for a in db.query(Article)} == {"keep", "fresh"}
    assert db.query(ArticleTag).count() == 0


def test_health_reports_the_last_ingest(client, session_factory):
    assert client.get("/health").json() == {"status": "ok", "scheduler": "off", "last_ingest": None}
    run_job(session_factory, "hourly", fake_ingest(5))
    body = client.get("/health").json()
    assert body["last_ingest"]["articles_added"] == 5 and body["last_ingest"]["kind"] == "hourly"
