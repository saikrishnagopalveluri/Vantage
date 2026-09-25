from datetime import date, timedelta

from app.models import PushSubscription, UserStreak
from app.push import Notification, send, send_streak_reminders
from tests.conftest import as_user

SUB = {"endpoint": "https://push.test/abc", "keys": {"p256dh": "p256dh-value", "auth": "auth-value"}}


def set_vapid(monkeypatch) -> None:
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-private-key")


def test_subscribing_creates_a_row_and_resubscribing_the_same_endpoint_updates_it(client, world):
    res = client.post("/push/u1/subscribe", json={**SUB, "categories": ["streak", "news"]}, headers=as_user("u1"))
    assert res.status_code == 201
    body = res.json()
    assert body["categories"] == ["streak", "news"]
    assert body["endpoint"] == SUB["endpoint"]  # the frontend matches "this device's" row by endpoint

    again = client.post("/push/u1/subscribe", json={**SUB, "categories": ["games"]}, headers=as_user("u1"))
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]  # same row, not a duplicate
    assert again.json()["categories"] == ["games"]

    listed = client.get("/push/u1", headers=as_user("u1")).json()
    assert len(listed) == 1


def test_an_unknown_category_is_rejected(client, world):
    res = client.post("/push/u1/subscribe", json={**SUB, "categories": ["not-a-real-category"]}, headers=as_user("u1"))
    assert res.status_code == 422


def test_categories_can_be_updated_and_unsubscribe_removes_the_row(client, world):
    client.post("/push/u1/subscribe", json={**SUB, "categories": ["streak"]}, headers=as_user("u1"))
    updated = client.put("/push/u1/categories", json={"endpoint": SUB["endpoint"], "categories": ["news", "games"]}, headers=as_user("u1"))
    assert updated.status_code == 200 and set(updated.json()["categories"]) == {"news", "games"}

    client.post("/push/u1/unsubscribe", json={"endpoint": SUB["endpoint"]}, headers=as_user("u1"))
    assert client.get("/push/u1", headers=as_user("u1")).json() == []


def test_another_user_cannot_subscribe_read_or_change_someone_elses_push_settings(client, world):
    client.post("/push/u1/subscribe", json={**SUB, "categories": ["streak"]}, headers=as_user("u1"))
    assert client.get("/push/u1", headers=as_user("u2")).status_code == 403
    assert client.post("/push/u1/subscribe", json=SUB, headers=as_user("u2")).status_code == 403
    assert client.put("/push/u1/categories", json={"endpoint": SUB["endpoint"], "categories": []}, headers=as_user("u2")).status_code == 403


def test_categories_lists_every_notification_kind_with_a_label(client):
    body = client.get("/push/categories").json()
    assert body["streak"] == "Daily streak"
    assert set(body) == {"streak", "news", "games", "role_update", "company_update"}


def test_send_streak_reminders_only_reaches_subscribed_devices_with_an_untouched_active_streak(db, world, monkeypatch):
    set_vapid(monkeypatch)
    today = date(2026, 9, 20)
    sent_to: list[str] = []
    monkeypatch.setattr("app.push.webpush", lambda **kw: sent_to.append(kw["subscription_info"]["endpoint"]))

    # u1: active streak, not touched today, subscribed to "streak" -> should be reached
    db.add(UserStreak(user_id="u1", current_streak=5, longest_streak=5, last_active_on=today - timedelta(days=1)))
    db.add(PushSubscription(user_id="u1", endpoint="https://push.test/u1", p256dh="a", auth="b", categories=["streak"]))
    # u2: active streak, not touched today, but did NOT opt into "streak" -> skipped
    db.add(UserStreak(user_id="u2", current_streak=3, longest_streak=3, last_active_on=today - timedelta(days=1)))
    db.add(PushSubscription(user_id="u2", endpoint="https://push.test/u2", p256dh="a", auth="b", categories=["news"]))
    # world's own u1/u2 profiles collide with these ids; use fresh ones instead
    db.commit()

    sent = send_streak_reminders(db, today)
    assert sent == 1
    assert sent_to == ["https://push.test/u1"]


def test_send_streak_reminders_skips_a_streak_already_touched_today_or_at_zero(db, monkeypatch):
    set_vapid(monkeypatch)
    today = date(2026, 9, 20)
    monkeypatch.setattr("app.push.webpush", lambda **kw: None)

    db.add(UserStreak(user_id="touched", current_streak=4, longest_streak=4, last_active_on=today))
    db.add(PushSubscription(user_id="touched", endpoint="https://push.test/touched", p256dh="a", auth="b", categories=["streak"]))
    db.add(UserStreak(user_id="zero", current_streak=0, longest_streak=2, last_active_on=today - timedelta(days=3)))
    db.add(PushSubscription(user_id="zero", endpoint="https://push.test/zero", p256dh="a", auth="b", categories=["streak"]))
    db.commit()

    assert send_streak_reminders(db, today) == 0


def test_a_send_failure_from_a_gone_subscription_deletes_the_row(db, monkeypatch):
    set_vapid(monkeypatch)
    import pywebpush

    class FakeResponse:
        status_code = 410

    def failing(**kw):
        raise pywebpush.WebPushException("gone", response=FakeResponse())

    monkeypatch.setattr("app.push.webpush", failing)
    sub = PushSubscription(user_id="u1", endpoint="https://push.test/gone", p256dh="a", auth="b", categories=["streak"])
    db.add(sub)
    db.commit()

    ok = send(db, sub, Notification(title="t", body="b", url="/feed"))
    assert ok is False
    assert db.get(PushSubscription, sub.id) is None


def test_send_does_nothing_without_vapid_keys_configured(db, monkeypatch):
    monkeypatch.delenv("VAPID_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    sub = PushSubscription(user_id="u1", endpoint="https://push.test/x", p256dh="a", auth="b", categories=["streak"])
    db.add(sub)
    db.commit()
    assert send(db, sub, Notification(title="t", body="b", url="/feed")) is False
