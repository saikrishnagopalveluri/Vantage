from datetime import date, datetime, timedelta, timezone

from app.ingest import FeedEntry, ingest_entries
from app.models import PushSubscription, RoleCapability, Source, UserCapability, UserStreak
from app.push import send_entity_updates, send_games_nudges, send_news_alerts

NOW = datetime.now(timezone.utc)


def set_vapid(monkeypatch) -> None:
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-private-key")


def sub(db, user_id: str, category: str, endpoint: str | None = None) -> PushSubscription:
    s = PushSubscription(user_id=user_id, endpoint=endpoint or f"https://push.test/{user_id}/{category}", p256dh="a", auth="b", categories=[category])
    db.add(s)
    return s


def ingest(db, world, *entries: FeedEntry) -> None:
    """Runs the real ingest/tagging pipeline so articles get realistic ArticleTag rows, the same way
    test_feed.py's feed_world does — a hand-built ArticleTag would risk testing a fake shape."""
    for cap in (world.excel, world.insights, world.powerbi):
        db.add(RoleCapability(role_id=world.bm.id, capability_id=cap.id))
    db.add(UserCapability(user_id="u1", capability_id=world.excel.id))
    source = Source(name="Marketing Dive", feed_url="https://feed.test/rss", authority=4)
    db.add(source)
    db.commit()
    ingest_entries(db, source, list(entries))


# ---- news_alert -------------------------------------------------------------------------------


def test_send_news_alerts_reaches_a_subscriber_with_a_fresh_critical_story(db, world, monkeypatch):
    set_vapid(monkeypatch)
    sent_to: list[str] = []
    monkeypatch.setattr("app.push.webpush", lambda **kw: sent_to.append(kw["subscription_info"]["endpoint"]))
    ingest(db, world, FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "", NOW))
    sub(db, "u1", "news")
    db.commit()

    assert send_news_alerts(db, NOW + timedelta(hours=1)) == 1
    assert sent_to == ["https://push.test/u1/news"]


def test_send_news_alerts_ignores_a_story_published_before_the_lookback_window(db, world, monkeypatch):
    set_vapid(monkeypatch)
    monkeypatch.setattr("app.push.webpush", lambda **kw: None)
    ingest(db, world, FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "", NOW - timedelta(days=3)))
    sub(db, "u1", "news")
    db.commit()

    assert send_news_alerts(db, NOW) == 0


def test_send_news_alerts_skips_a_user_not_subscribed_to_news(db, world, monkeypatch):
    set_vapid(monkeypatch)
    monkeypatch.setattr("app.push.webpush", lambda **kw: None)
    ingest(db, world, FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "", NOW))
    sub(db, "u1", "games")
    db.commit()

    assert send_news_alerts(db, NOW + timedelta(hours=1)) == 0


# ---- entity_updates (role_update / company_update) --------------------------------------------


def test_send_entity_updates_reaches_a_role_subscriber_for_a_targeted_role(db, world, monkeypatch):
    set_vapid(monkeypatch)
    sent_to: list[str] = []
    monkeypatch.setattr("app.push.webpush", lambda **kw: sent_to.append(kw["subscription_info"]["endpoint"]))
    # world's u1 targets world.bm (Brand Manager); a headline naming that role tags it ROLE.
    ingest(db, world, FeedEntry("Consumer Insights join the Brand Manager toolkit", "https://x.test/bm", "", NOW))
    sub(db, "u1", "role_update")
    db.commit()

    assert send_entity_updates(db, NOW + timedelta(hours=1)) == 1
    assert sent_to == ["https://push.test/u1/role_update"]


def test_send_entity_updates_reaches_a_company_subscriber_for_a_targeted_company(db, world, monkeypatch):
    set_vapid(monkeypatch)
    sent_to: list[str] = []
    monkeypatch.setattr("app.push.webpush", lambda **kw: sent_to.append(kw["subscription_info"]["endpoint"]))
    # world's u1 targets world.hul among others.
    ingest(db, world, FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "", NOW))
    sub(db, "u1", "company_update")
    db.commit()

    assert send_entity_updates(db, NOW + timedelta(hours=1)) == 1
    assert sent_to == ["https://push.test/u1/company_update"]


def test_send_entity_updates_does_not_reach_someone_who_does_not_target_that_role_or_company(db, world, monkeypatch):
    set_vapid(monkeypatch)
    monkeypatch.setattr("app.push.webpush", lambda **kw: None)
    ingest(db, world, FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "", NOW))
    # u2 in `world` has no target roles/companies at all.
    sub(db, "u2", "company_update")
    db.commit()

    assert send_entity_updates(db, NOW + timedelta(hours=1)) == 0


# ---- games_nudge ---------------------------------------------------------------------------------


def test_send_games_nudges_reaches_someone_inactive_but_not_someone_active(db, monkeypatch):
    set_vapid(monkeypatch)
    sent_to: list[str] = []
    monkeypatch.setattr("app.push.webpush", lambda **kw: sent_to.append(kw["subscription_info"]["endpoint"]))
    today = date(2026, 9, 20)
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

    db.add(UserStreak(user_id="idle", current_streak=0, longest_streak=4, last_active_on=today - timedelta(days=5)))
    sub(db, "idle", "games")
    db.add(UserStreak(user_id="active", current_streak=2, longest_streak=2, last_active_on=today))
    sub(db, "active", "games")
    db.commit()

    assert send_games_nudges(db, now, inactive_days=3) == 1
    assert sent_to == ["https://push.test/idle/games"]


def test_send_games_nudges_skips_someone_with_no_streak_row_at_all(db, monkeypatch):
    set_vapid(monkeypatch)
    monkeypatch.setattr("app.push.webpush", lambda **kw: None)
    sub(db, "never-visited", "games")
    db.commit()

    assert send_games_nudges(db, datetime.now(timezone.utc)) == 0
