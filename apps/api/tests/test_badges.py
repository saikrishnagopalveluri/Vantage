from datetime import datetime, timezone

from app.badges import compute_badges
from app.models import Article, InteractionAction, Source, UserEngagement, UserInteraction, UserStreak
from tests.conftest import as_user


def test_nothing_earned_yet_reads_as_zero_and_unachieved():
    states = compute_badges(longest_streak=0, articles_read=0, active_seconds=0)
    assert all(s.current == 0 and s.achieved is False for s in states)
    assert len(states) == 12  # 4 streak + 4 articles + 4 time thresholds


def test_a_badge_is_achieved_exactly_at_its_threshold():
    states = {s.id: s for s in compute_badges(longest_streak=7, articles_read=9, active_seconds=3600)}
    assert states["streak_7"].achieved is True
    assert states["streak_30"].achieved is False
    assert states["articles_10"].achieved is False  # one short
    assert states["time_3600"].achieved is True


def test_current_reflects_the_raw_count_even_past_the_top_threshold():
    states = {s.id: s for s in compute_badges(longest_streak=500, articles_read=0, active_seconds=0)}
    assert states["streak_100"].current == 500 and states["streak_100"].achieved is True


# ---- the router ------------------------------------------------------------------------------------


def seed_reads(db, user_id: str, count: int) -> None:
    source = Source(name="S", feed_url=f"https://f-{user_id}.test", authority=3)
    db.add(source)
    db.flush()
    for i in range(count):
        article = Article(source_id=source.id, title=f"Story {i}", url=f"https://x.test/{user_id}/{i}", published_at=datetime.now(timezone.utc))
        db.add(article)
        db.flush()
        db.add(UserInteraction(user_id=user_id, article_id=article.id, action=InteractionAction.READ))
    db.commit()


def test_a_user_with_no_activity_sees_every_badge_unachieved(client, world):
    res = client.get("/badges/u1", headers=as_user("u1"))
    assert res.status_code == 200
    badges = res.json()["badges"]
    assert len(badges) == 12
    assert all(b["achieved"] is False for b in badges)


def test_reading_articles_unlocks_the_matching_badge(client, world, db):
    seed_reads(db, "u1", 10)
    body = client.get("/badges/u1", headers=as_user("u1")).json()
    by_id = {b["id"]: b for b in body["badges"]}
    assert by_id["articles_10"] == {
        "id": "articles_10", "kind": "articles", "label": "Getting Started",
        "description": "10 articles read", "threshold": 10, "current": 10, "achieved": True,
    }
    assert by_id["articles_50"]["achieved"] is False


def test_the_streak_badge_uses_the_longest_streak_not_the_current_one(client, world, db):
    db.add(UserStreak(user_id="u1", current_streak=1, longest_streak=7, last_active_on=None))
    db.commit()
    by_id = {b["id"]: b for b in client.get("/badges/u1", headers=as_user("u1")).json()["badges"]}
    assert by_id["streak_7"]["achieved"] is True
    assert by_id["streak_3"]["achieved"] is True  # 7 clears the lower bar too


def test_logging_time_accumulates_across_calls(client, world):
    client.post("/badges/u1/time", json={"seconds": 30}, headers=as_user("u1"))
    body = client.post("/badges/u1/time", json={"seconds": 45}, headers=as_user("u1")).json()
    time_badges = [b for b in body["badges"] if b["kind"] == "time"]
    assert all(b["current"] == 75 for b in time_badges)


def test_logging_time_past_the_bounds_is_rejected(client, world):
    assert client.post("/badges/u1/time", json={"seconds": 0}, headers=as_user("u1")).status_code == 422
    assert client.post("/badges/u1/time", json={"seconds": 121}, headers=as_user("u1")).status_code == 422


def test_a_user_cannot_read_or_log_time_for_someone_else(client, world):
    assert client.get("/badges/u2", headers=as_user("u1")).status_code == 403
    assert client.post("/badges/u2/time", json={"seconds": 10}, headers=as_user("u1")).status_code == 403
