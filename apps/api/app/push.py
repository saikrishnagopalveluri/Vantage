"""Web Push: sending a notification, and the copy that goes in it.

Short, personal, a little playful — the way a good food-delivery app writes a notification, not the
way a corporate system does. Every category has several variants so the same trigger doesn't read
identically every time. Never guilt-trips, never fakes urgency that isn't real.
"""

import json
import os
import random
from dataclasses import dataclass
from datetime import date, datetime, timezone

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PushSubscription, UserStreak

CATEGORIES: dict[str, str] = {
    "streak": "Daily streak",
    "news": "News alerts",
    "games": "Games calling",
    "role_update": "Role updates",
    "company_update": "Company updates",
}


def vapid_config() -> tuple[str, str, str] | None:
    public_key = os.getenv("VAPID_PUBLIC_KEY")
    private_key = os.getenv("VAPID_PRIVATE_KEY")
    subject = os.getenv("VAPID_SUBJECT") or "mailto:hello@example.com"
    if not public_key or not private_key:
        return None
    return public_key, private_key, subject


@dataclass(frozen=True)
class Notification:
    title: str
    body: str
    url: str  # where a tap on the notification should land, relative to the site root


def send(db: Session, subscription: PushSubscription, notification: Notification) -> bool:
    """Sends one notification. Returns whether it went through. A 404/410 means the browser dropped
    the subscription (uninstalled, permission revoked) — the caller should delete that row; anything
    else is transient and worth trying again next time."""
    config = vapid_config()
    if config is None:
        return False
    public_key, private_key, subject = config
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps({"title": notification.title, "body": notification.body, "url": notification.url}),
            vapid_private_key=private_key,
            vapid_claims={"sub": subject},
        )
        return True
    except WebPushException as e:
        status = e.response.status_code if e.response is not None else None
        if status in (404, 410):
            db.delete(subscription)
            db.commit()
        return False


# ---- copy bank ---------------------------------------------------------------------------------

_STREAK_AT_RISK = [
    "Your {n}-day streak is hanging by a thread. One tap keeps it alive.",
    "{n} days in. Don't let today be the day it ends.",
    "The streak is watching you not open the app right now.",
    "Quick one — your {n}-day streak needs 10 seconds of your time today.",
]
_STREAK_MILESTONE = [
    "{n} days straight. That's not luck, that's a habit.",
    "{n}-day streak. Somebody's actually consistent for once.",
    "{n} days in a row. Keep going, this is the fun part.",
]
_NEWS_CRITICAL = [
    "{headline} — this one's got your name on it.",
    "You're gonna want to see this: {headline}",
    "{company} just did something you should know about.",
]
_GAMES_NUDGE = [
    "Your Word Drop streak called. It misses you.",
    "60 seconds. That's all Speed Round needs from you right now.",
    "Someone just beat your Match the Field score. Rude, honestly.",
]
_ROLE_UPDATE = [
    "New {role} openings just landed at companies you follow.",
    "{company} is hiring for {role}. You called this.",
]
_COMPANY_UPDATE = [
    "{company}'s in the news again. Get the full story.",
    "Something's brewing at {company}.",
]


def streak_at_risk(n: int) -> Notification:
    body = random.choice(_STREAK_AT_RISK).format(n=n)
    return Notification(title="Keep the streak alive 🔥", body=body, url="/feed")


def streak_milestone(n: int) -> Notification:
    body = random.choice(_STREAK_MILESTONE).format(n=n)
    return Notification(title=f"{n} days 🔥", body=body, url="/feed")


def news_critical(headline: str, company: str | None) -> Notification:
    body = random.choice(_NEWS_CRITICAL).format(headline=headline, company=company or "A company you follow")
    return Notification(title="Read this one", body=body, url="/feed")


def games_nudge() -> Notification:
    return Notification(title="Games are calling 🎮", body=random.choice(_GAMES_NUDGE), url="/games")


def role_update(role: str, company: str | None) -> Notification:
    body = random.choice(_ROLE_UPDATE).format(role=role, company=company or "A company you follow")
    return Notification(title="Role you'd want", body=body, url="/explore")


def company_update(company: str) -> Notification:
    body = random.choice(_COMPANY_UPDATE).format(company=company)
    return Notification(title=company, body=body, url="/feed")


# ---- dispatch -----------------------------------------------------------------------------------


def send_streak_reminders(db: Session, today: date) -> int:
    """One nudge per subscribed device, for anyone with an active streak they haven't touched yet
    today. Sent at most once a day by the scheduler; a subscription without the "streak" category
    is skipped entirely, not just silenced client-side."""
    at_risk = db.scalars(
        select(UserStreak).where(UserStreak.current_streak > 0, UserStreak.last_active_on != today)
    ).all()
    sent = 0
    for streak in at_risk:
        subs = db.scalars(
            select(PushSubscription).where(PushSubscription.user_id == streak.user_id)
        ).all()
        for sub in subs:
            if "streak" not in sub.categories:
                continue
            if send(db, sub, streak_at_risk(streak.current_streak)):
                sub.last_sent_at = datetime.now(timezone.utc)
                sent += 1
    if sent:
        db.commit()
    return sent
