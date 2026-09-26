"""Web Push: sending a notification, and the copy that goes in it.

Short, personal, a little playful — the way a good food-delivery app writes a notification, not the
way a corporate system does. Every category has several variants so the same trigger doesn't read
identically every time. Never guilt-trips, never fakes urgency that isn't real.
"""

import json
import os
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.feed import load_context, rank
from app.models import (
    Article,
    ArticleTag,
    Company,
    PushSubscription,
    Role,
    TagType,
    UserProfile,
    UserStreak,
    UserTargetCompany,
    UserTargetRole,
)

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
    "Your {n}-day streak is one bad decision away from zero. Don't do this to yourself.",
    "{n} days of showing up, about to be undone by you closing this notification. We see you.",
    "POV: you let a {n}-day streak die today. Plot twist, you don't have to.",
    "The streak is currently in its flop era. You have the power to fix this.",
    "{n} days in a row and you're really about to no-show today? Bold choice.",
]
_STREAK_MILESTONE = [
    "{n} days straight. That's not luck, that's discipline arc.",
    "{n}-day streak. Certified consistent behavior, actually.",
    "{n} days in a row. Main character energy, keep it going.",
    "{n} days. You're basically unbothered at this point. Respect.",
]
_NEWS_CRITICAL = [
    "{headline} — this one has your name written all over it, no cap.",
    "Drop everything, you need to see this: {headline}",
    "{company} just did something and your future self needs to know.",
    "Not us gatekeeping this from you: {headline}",
]
_GAMES_NUDGE = [
    "Word Drop texted. It's asking if you're okay because you ghosted it.",
    "60 seconds. Speed Round is not asking for much here.",
    "Someone beat your Match the Field score. The audacity. Go fix that.",
    "Your games are sitting there, untouched, judging you quietly.",
]
_ROLE_UPDATE = [
    "New {role} openings just dropped at companies you follow. Manifesting, but make it actionable.",
    "{company} is hiring for {role}. This is basically fate texting you.",
    "{role} roles just opened up. Your era might be starting.",
]
_COMPANY_UPDATE = [
    "{company}'s in the news again. Main character behavior over there.",
    "Something's brewing at {company} and you should probably know about it.",
    "{company} said 'let them know' — so here we are.",
]


def streak_at_risk(n: int) -> Notification:
    body = random.choice(_STREAK_AT_RISK).format(n=n)
    return Notification(title="Keep the streak alive 🔥", body=body, url="/feed")


def streak_milestone(n: int) -> Notification:
    body = random.choice(_STREAK_MILESTONE).format(n=n)
    return Notification(title=f"{n} days 🔥", body=body, url="/feed")


def news_critical(headline: str, company: str | None) -> Notification:
    body = random.choice(_NEWS_CRITICAL).format(headline=headline, company=company or "A company you follow")
    return Notification(title="Okay you need to see this 👀", body=body, url="/feed")


def games_nudge() -> Notification:
    return Notification(title="Games miss you 🎮", body=random.choice(_GAMES_NUDGE), url="/games")


def role_update(role: str, company: str | None) -> Notification:
    body = random.choice(_ROLE_UPDATE).format(role=role, company=company or "A company you follow")
    return Notification(title="This one's for you ✨", body=body, url="/explore")


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


def _subs_by_category(db: Session, category: str) -> dict[str, list[PushSubscription]]:
    grouped: dict[str, list[PushSubscription]] = {}
    for sub in db.scalars(select(PushSubscription)):
        if category in sub.categories:
            grouped.setdefault(sub.user_id, []).append(sub)
    return grouped


def send_news_alerts(db: Session, now: datetime) -> int:
    """Once a day: the single best new CRITICAL-tier story published since this time yesterday, for
    anyone subscribed to 'news'. Reuses the same ranker the feed itself uses, so "critical" means
    exactly what it means on the feed page — no separate notion of newsworthiness to keep in sync."""
    since = now - timedelta(hours=24)
    sent = 0
    for user_id, subs in _subs_by_category(db, "news").items():
        profile = db.get(UserProfile, user_id)
        if profile is None:
            continue
        ctx = load_context(db, profile)
        ranked = rank(db, profile, ctx, "for_you", now)
        best = next((r for r in ranked if r.tier == "critical" and r.published >= since), None)
        if best is None:
            continue
        company = best.matched["companies"][0] if best.matched["companies"] else None
        notification = news_critical(best.article.title, company)
        for sub in subs:
            if send(db, sub, notification):
                sub.last_sent_at = now
                sent += 1
    if sent:
        db.commit()
    return sent


def send_entity_updates(db: Session, now: datetime) -> int:
    """Once a day: the newest article tagged with a role or company the reader targets, published
    since this time yesterday. role_update and company_update are the same mechanism against a
    different tag type and target set, so they're handled together here."""
    since = now - timedelta(hours=24)
    sent = 0
    role_subs = _subs_by_category(db, "role_update")
    company_subs = _subs_by_category(db, "company_update")
    for user_id in role_subs.keys() | company_subs.keys():
        if user_id in role_subs:
            target_role_ids = set(db.scalars(select(UserTargetRole.role_id).where(UserTargetRole.user_id == user_id)))
            hit = None
            if target_role_ids:
                hit = db.execute(
                    select(ArticleTag.ref_id)
                    .join(Article, Article.id == ArticleTag.article_id)
                    .where(ArticleTag.tag_type == TagType.ROLE, ArticleTag.ref_id.in_(target_role_ids), Article.published_at >= since)
                    .order_by(Article.published_at.desc())
                    .limit(1)
                ).first()
            if hit is not None:
                role = db.get(Role, hit[0])
                notification = role_update(role.title if role else "A role you follow", None)
                for sub in role_subs[user_id]:
                    if send(db, sub, notification):
                        sub.last_sent_at = now
                        sent += 1

        if user_id in company_subs:
            target_company_ids = set(db.scalars(select(UserTargetCompany.company_id).where(UserTargetCompany.user_id == user_id)))
            hit = None
            if target_company_ids:
                hit = db.execute(
                    select(ArticleTag.ref_id)
                    .join(Article, Article.id == ArticleTag.article_id)
                    .where(ArticleTag.tag_type == TagType.COMPANY, ArticleTag.ref_id.in_(target_company_ids), Article.published_at >= since)
                    .order_by(Article.published_at.desc())
                    .limit(1)
                ).first()
            if hit is not None:
                company = db.get(Company, hit[0])
                notification = company_update(company.name if company else "A company you follow")
                for sub in company_subs[user_id]:
                    if send(db, sub, notification):
                        sub.last_sent_at = now
                        sent += 1
    if sent:
        db.commit()
    return sent


def send_games_nudges(db: Session, now: datetime, inactive_days: int = 3) -> int:
    """Nudges anyone subscribed to 'games' who hasn't opened Vantage in a while. The caller decides
    the cadence (see scheduler.py) — this only decides who, given that it's due."""
    cutoff = (now - timedelta(days=inactive_days)).date()
    sent = 0
    for user_id, subs in _subs_by_category(db, "games").items():
        streak = db.get(UserStreak, user_id)
        if streak is None or streak.last_active_on is None or streak.last_active_on >= cutoff:
            continue
        notification = games_nudge()
        for sub in subs:
            if send(db, sub, notification):
                sub.last_sent_at = now
                sent += 1
    if sent:
        db.commit()
    return sent
