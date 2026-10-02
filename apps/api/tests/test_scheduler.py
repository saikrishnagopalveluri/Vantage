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
    scheduler = Scheduler(
        session_factory,
        every_minutes=60,
        daily_hour=3,
        streak_reminder_every_hours=999999,
        news_alert_every_hours=999999,
        games_nudge_every_days=9999,
        ingest=ingest,
    )
    # past 03:00 UTC and never run today: the daily job also ingests. streak_reminder, news_alert
    # and games_nudge have never run at all yet either, so — same as "daily" the first time — an
    # interval-gated check with no prior row is due immediately, regardless of how large its
    # interval is.
    assert scheduler.tick(NOW) == ["daily", "streak_reminder", "news_alert", "games_nudge"]
    assert scheduler.tick(NOW + timedelta(minutes=20)) == []
    assert scheduler.tick(NOW + timedelta(minutes=61)) == ["hourly"]
    assert len(ingest.calls) == 2
    with session_factory() as db:
        runs = db.query(IngestRun).order_by(IngestRun.started_at).all()
        assert [r.kind for r in runs] == ["daily", "hourly"]
        assert runs[0].articles_added == 3 and runs[0].finished_at is not None and runs[0].error is None


def test_daily_job_waits_for_its_hour_and_runs_once_a_day(session_factory):
    scheduler = Scheduler(
        session_factory,
        every_minutes=10_000,
        daily_hour=3,
        streak_reminder_every_hours=999999,
        news_alert_every_hours=999999,
        entity_updates_hour=23,
        games_nudge_every_days=9999,
        ingest=fake_ingest(),
    )
    early = datetime(2026, 9, 20, 1, 0, tzinfo=UTC)
    with session_factory() as db:
        assert is_due(db, "daily", early, daily_hour=3) is False
    # streak_reminder/news_alert/games_nudge all fire on this first-ever tick too, same reason.
    assert scheduler.tick(datetime(2026, 9, 20, 3, 5, tzinfo=UTC)) == ["daily", "streak_reminder", "news_alert", "games_nudge"]
    assert scheduler.tick(datetime(2026, 9, 20, 22, 0, tzinfo=UTC)) == []
    assert scheduler.tick(datetime(2026, 9, 21, 3, 5, tzinfo=UTC)) == ["daily"]


def test_streak_reminder_fires_every_gap_while_at_risk_and_stops_once_they_open_the_app(session_factory, monkeypatch):
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-private-key")
    sent: list[str] = []
    monkeypatch.setattr("app.push.webpush", lambda **kw: sent.append(kw["subscription_info"]["endpoint"]))

    scheduler = Scheduler(
        session_factory,
        every_minutes=10_000,
        daily_hour=23,
        streak_reminder_every_hours=4,
        news_alert_every_hours=999999,
        entity_updates_hour=23,
        games_nudge_every_days=9999,
        ingest=fake_ingest(),
    )
    # Prime daily/hourly/news_alert/games_nudge with a "just ran" row each, so this test's own
    # ticks stay about streak_reminder only — otherwise every interval-gated kind with no prior
    # row fires on first contact too, same as above.
    seed = datetime(2026, 9, 20, 0, 0, tzinfo=UTC)
    with session_factory() as db:
        db.add(IngestRun(kind="daily", started_at=seed, finished_at=seed))
        db.add(IngestRun(kind="hourly", started_at=seed, finished_at=seed))
        db.add(NotificationRun(kind="news_alert", started_at=seed, finished_at=seed, sent=0))
        db.add(NotificationRun(kind="games_nudge", started_at=seed, finished_at=seed, sent=0))
        db.add(UserStreak(user_id="u1", current_streak=5, longest_streak=5, last_active_on=date(2026, 9, 19)))
        db.add(PushSubscription(user_id="u1", endpoint="https://push.test/u1", p256dh="a", auth="b", categories=["streak"]))
        db.commit()

    # First real check of streak_reminder is immediately due (nothing to compare the gap against yet).
    assert scheduler.tick(datetime(2026, 9, 20, 4, 0, tzinfo=UTC)) == ["streak_reminder"]
    assert sent == ["https://push.test/u1"]
    # Still within the 4h gap: not due again.
    assert scheduler.tick(datetime(2026, 9, 20, 7, 0, tzinfo=UTC)) == []
    # Past the gap, and the reader still hasn't opened the app today: fires again, same user.
    assert scheduler.tick(datetime(2026, 9, 20, 9, 0, tzinfo=UTC)) == ["streak_reminder"]
    assert sent == ["https://push.test/u1", "https://push.test/u1"]
    with session_factory() as db:
        assert db.query(NotificationRun).filter_by(kind="streak_reminder").count() == 2

    # The reader opens the app: last_active_on moves to today, so even though the gap has elapsed
    # again, send_streak_reminders() no longer considers them at risk. The run still fires — it's
    # due by the clock, and tick() reports kinds that ran, not kinds that actually sent something —
    # but nobody gets pushed.
    with session_factory() as db:
        db.query(UserStreak).filter_by(user_id="u1").update({"last_active_on": date(2026, 9, 20)})
        db.commit()
    assert scheduler.tick(datetime(2026, 9, 20, 14, 0, tzinfo=UTC)) == ["streak_reminder"]
    assert sent == ["https://push.test/u1", "https://push.test/u1"]  # no third send
    with session_factory() as db:
        runs = db.query(NotificationRun).filter_by(kind="streak_reminder").order_by(NotificationRun.started_at).all()
        assert [r.sent for r in runs] == [1, 1, 0]


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
