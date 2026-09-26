"""The achievement catalog: streak, articles-read and time-spent milestones. Kept free of the
database, the same way streaks.py and why.py are, so the thresholds can be tested on their own.
"""

from dataclasses import dataclass
from typing import Literal

BadgeKind = Literal["streak", "articles", "time"]


@dataclass(frozen=True)
class BadgeDef:
    id: str
    kind: BadgeKind
    label: str
    description: str
    threshold: int  # days / articles / seconds, depending on kind


CATALOG: list[BadgeDef] = [
    BadgeDef("streak_3", "streak", "On a Roll", "3 days in a row", 3),
    BadgeDef("streak_7", "streak", "Week Streak", "7 days in a row", 7),
    BadgeDef("streak_30", "streak", "Month Streak", "30 days in a row", 30),
    BadgeDef("streak_100", "streak", "Century Streak", "100 days in a row", 100),
    BadgeDef("articles_10", "articles", "Getting Started", "10 articles read", 10),
    BadgeDef("articles_50", "articles", "Well Read", "50 articles read", 50),
    BadgeDef("articles_200", "articles", "News Hound", "200 articles read", 200),
    BadgeDef("articles_1000", "articles", "Industry Insider", "1,000 articles read", 1000),
    BadgeDef("time_3600", "time", "First Hour", "1 hour on Vantage", 3600),
    BadgeDef("time_18000", "time", "Regular", "5 hours on Vantage", 5 * 3600),
    BadgeDef("time_72000", "time", "Dedicated", "20 hours on Vantage", 20 * 3600),
    BadgeDef("time_360000", "time", "Power User", "100 hours on Vantage", 100 * 3600),
]


@dataclass(frozen=True)
class BadgeState:
    id: str
    kind: BadgeKind
    label: str
    description: str
    threshold: int
    current: int
    achieved: bool


def compute_badges(longest_streak: int, articles_read: int, active_seconds: int) -> list[BadgeState]:
    current_by_kind = {"streak": longest_streak, "articles": articles_read, "time": active_seconds}
    return [
        BadgeState(
            id=b.id,
            kind=b.kind,
            label=b.label,
            description=b.description,
            threshold=b.threshold,
            current=current_by_kind[b.kind],
            achieved=current_by_kind[b.kind] >= b.threshold,
        )
        for b in CATALOG
    ]
