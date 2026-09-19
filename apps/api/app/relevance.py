"""Rule-based relevance scoring (no ML). Weights are keyed by profile status, so the
scoring function never asks "is this a student?": it asks what the status says to weight.

A dimension's match is a strength in [0, 1]: 1.0 when the entity is named in the headline,
lower when only the teaser names it. The score is the weighted strength over the dimensions the
profile has data for, so a user with no targets isn't capped by dimensions they can't match.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass

from app.models import ProfileStatus

WEIGHTS: dict[ProfileStatus, dict[str, int]] = {
    ProfileStatus.TARGETING: {
        "target_role": 30,
        "target_company": 25,
        "target_industry": 15,
        "current_role": 0,
        "current_company": 0,
        "current_industry": 0,
        "capability": 20,
        "domain": 10,
    },
    ProfileStatus.PLACED: {
        "current_role": 30,
        "current_company": 25,
        "current_industry": 15,
        "target_role": 10,
        "target_company": 8,
        "target_industry": 5,
        "capability": 20,
        "domain": 10,
    },
}

RECENCY_HALF_LIFE_DAYS = 7.0
RECENCY_FLOOR = 0.5

# An id -> strength map, or a plain set of ids (every member counts as strength 1.0).
Tags = Mapping[str, float] | Collection[str]


@dataclass(frozen=True)
class ProfileTags:
    current_role: str | None = None
    current_company: str | None = None
    current_industry: str | None = None
    target_roles: frozenset[str] = frozenset()
    target_companies: frozenset[str] = frozenset()
    target_industries: frozenset[str] = frozenset()
    capabilities: frozenset[str] = frozenset()
    domains: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ArticleTags:
    roles: Tags = frozenset()
    companies: Tags = frozenset()
    industries: Tags = frozenset()
    capabilities: Tags = frozenset()
    domains: Tags = frozenset()


def recency_multiplier(age_days: float) -> float:
    decay = 0.5 ** (max(age_days, 0.0) / RECENCY_HALF_LIFE_DAYS)
    return RECENCY_FLOOR + (1 - RECENCY_FLOOR) * decay


def _strength(tags: Tags, wanted: Collection[str]) -> float:
    if isinstance(tags, Mapping):
        return max((tags.get(i, 0.0) for i in wanted), default=0.0)
    return 1.0 if any(i in tags for i in wanted) else 0.0


def _matches(profile: ProfileTags, article: ArticleTags) -> dict[str, float | None]:
    """Strength per dimension; None when the profile has no data for it."""

    def single(value: str | None, tags: Tags) -> float | None:
        return None if value is None else _strength(tags, [value])

    def multi(values: frozenset[str], tags: Tags) -> float | None:
        return None if not values else _strength(tags, values)

    return {
        "current_role": single(profile.current_role, article.roles),
        "current_company": single(profile.current_company, article.companies),
        "current_industry": single(profile.current_industry, article.industries),
        "target_role": multi(profile.target_roles, article.roles),
        "target_company": multi(profile.target_companies, article.companies),
        "target_industry": multi(profile.target_industries, article.industries),
        "capability": multi(profile.capabilities, article.capabilities),
        "domain": multi(profile.domains, article.domains),
    }


def score_article(
    profile: ProfileTags, article: ArticleTags, status: ProfileStatus, age_days: float
) -> float:
    """0-100."""
    matches = _matches(profile, article)
    applicable = {
        dim: weight
        for dim, weight in WEIGHTS[status].items()
        if weight > 0 and matches[dim] is not None
    }
    if not applicable:
        return 0.0
    earned = sum(w * (matches[dim] or 0.0) for dim, w in applicable.items())
    base = 100 * earned / sum(applicable.values())
    return round(base * recency_multiplier(age_days), 1)
