from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.legal import ConsentIn
from app.models import CapabilityKind, ProfileStatus
from app.push import CATEGORIES as _PUSH_CATEGORY_LABELS

MAX_FIELDS = 4  # fields of work a person can follow at once
_PUSH_CATEGORIES = frozenset(_PUSH_CATEGORY_LABELS)


def _as_utc(value: datetime | None) -> datetime | None:
    # SQLite hands back naive datetimes; everything we store is UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class NamedRef(BaseModel):
    id: str
    name: str


class DomainOut(BaseModel):
    id: str
    name: str
    slug: str
    group: str = ""
    role_count: int = 0  # every job title
    family_count: int = 0  # distinct roles, not counting title variants


class RoleRef(BaseModel):
    id: str
    title: str
    domain: NamedRef | None = None
    parent: NamedRef | None = None  # set when this title is a variant of another role
    mba: bool = False  # popular with management students


class CapabilityRef(BaseModel):
    id: str
    name: str
    kind: CapabilityKind
    domain: NamedRef | None = None
    mba: bool = False


class CompanyOut(BaseModel):
    id: str
    name: str
    industry: NamedRef | None
    mba: bool = False


class CurrentState(BaseModel):
    user_id: str
    name: str | None = None
    profile_status: ProfileStatus
    current_role: RoleRef | None
    current_company: NamedRef | None
    current_industry: NamedRef | None
    placed_at: datetime | None
    current_role_started_at: datetime | None

    @field_validator("placed_at", "current_role_started_at")
    @classmethod
    def _utc(cls, v: datetime | None) -> datetime | None:
        return _as_utc(v)


class PlacementIn(BaseModel):
    company_id: str
    role_id: str
    industry_id: str | None = None
    placed_on: date | None = None
    clear_targets: bool = False


class PlacementOut(CurrentState):
    event_type: Literal["placed", "role_changed", "unchanged"]


class CurrentIn(BaseModel):
    company_id: str
    role_id: str
    industry_id: str | None = None


class TargetsIn(BaseModel):
    domain_ids: list[str] = Field(default_factory=list, max_length=MAX_FIELDS)
    target_role_ids: list[str] = Field(default_factory=list, max_length=50)
    target_company_ids: list[str] = Field(default_factory=list, max_length=50)
    capability_ids: list[str] = Field(default_factory=list, max_length=100)


class OnboardingIn(TargetsIn):
    # The app's own form always asks for this; optional here so older/test clients still work.
    name: str | None = Field(default=None, max_length=120)
    # Set for someone who already works; leave out for a student.
    current: CurrentIn | None = None
    # A guest agrees to the terms and privacy policy here. An account already did when it signed up.
    consent: ConsentIn | None = None


class ProfileOut(CurrentState):
    domains: list[NamedRef]
    target_roles: list[RoleRef]
    target_companies: list[NamedRef]
    capabilities: list[CapabilityRef]


class CapabilityGap(BaseModel):
    capability_id: str
    name: str
    kind: CapabilityKind
    required_by_count: int
    required_by_total: int
    gap_ratio: float
    user_has_it: bool
    source: Literal["jd", "company", "taxonomy"]


class RoleGaps(BaseModel):
    role_id: str
    role_title: str
    companies_considered: int
    companies_with_no_data: int
    capabilities: list[CapabilityGap]


class SkillGapsOut(BaseModel):
    user_id: str
    target_roles: list[RoleGaps]


# ---- Explore -----------------------------------------------------------------


class RelatedRole(BaseModel):
    role: RoleRef
    shared_capabilities: list[str]
    similarity: float


class RoleDetail(BaseModel):
    id: str
    title: str
    domain: NamedRef | None
    description: str | None = None
    canonical: NamedRef | None = None  # the role whose skills this title shares
    aliases: list[str]
    variants: list[str] = []
    capabilities: list[CapabilityRef]
    companies: list[CompanyOut]
    companies_total: int = 0
    related_roles: list[RelatedRole]


class DomainRoles(BaseModel):
    domain: NamedRef | None
    roles: list[RoleRef]
    total: int = 0


class SourceRef(BaseModel):
    name: str
    authority: int


class ArticleBrief(BaseModel):
    id: str
    title: str
    url: str
    summary: str
    source: SourceRef
    published_at: datetime
    tags: dict[str, list[str]]

    @field_validator("published_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _as_utc(v)


class CompanyDetail(BaseModel):
    id: str
    name: str
    industry: NamedRef | None
    website: str | None = None
    roles_by_domain: list[DomainRoles]
    articles: list[ArticleBrief]


class SearchOut(BaseModel):
    query: str
    roles: list[RoleRef]
    companies: list[CompanyOut]
    capabilities: list[CapabilityRef]
    articles: list[ArticleBrief]


# ---- Feed -------------------------------------------------------------------


class Brief(BaseModel):
    """Shown only when a reader expands a story. Built from the publisher's own feed text."""

    paragraphs: list[str]
    pointers: list[str]
    note: str | None = None


class FeedItem(BaseModel):
    id: str
    title: str
    url: str
    summary: str
    brief: Brief | None = None
    source: SourceRef
    also_covered_by: list[str]
    published_at: datetime
    score: float
    tier: Literal["critical", "relevant", "explore"]
    why_this_matters: str
    action: str
    matched: dict[str, list[str]]
    domains: list[str]
    saved: bool
    newsletter: bool = False  # from a newsletter rather than a news site

    @field_validator("published_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _as_utc(v)


class FeedSummary(BaseModel):
    total: int
    critical: int
    relevant: int
    explore: int


class FeedOut(BaseModel):
    lens: Literal["for_you", "companies", "skills", "newsletters"]
    summary: FeedSummary
    items: list[FeedItem]
    offset: int
    has_more: bool
    as_of: datetime


class InteractionIn(BaseModel):
    article_id: str
    action: Literal["save", "unsave", "dismiss", "undismiss", "read"]


class InteractionOut(BaseModel):
    article_id: str
    saved: bool
    dismissed: bool


class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    active_today: bool


class BadgeOut(BaseModel):
    id: str
    kind: Literal["streak", "articles", "time"]
    label: str
    description: str
    threshold: int
    current: int
    achieved: bool


class BadgesOut(BaseModel):
    badges: list[BadgeOut]


class TimeIn(BaseModel):
    seconds: int = Field(ge=1, le=120)


class PushKeysIn(BaseModel):
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=100)


class PushSubscribeIn(BaseModel):
    """The browser's own PushSubscription.toJSON() shape, plus which categories to send."""

    endpoint: str = Field(min_length=1, max_length=2000)
    keys: PushKeysIn
    categories: list[str] = Field(default_factory=list, max_length=len(_PUSH_CATEGORIES))

    @field_validator("categories")
    @classmethod
    def _known_categories(cls, v: list[str]) -> list[str]:
        unknown = set(v) - _PUSH_CATEGORIES
        if unknown:
            raise ValueError(f"Unknown categories: {sorted(unknown)}")
        return v


class PushCategoriesIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2000)
    categories: list[str] = Field(default_factory=list, max_length=len(_PUSH_CATEGORIES))

    @field_validator("categories")
    @classmethod
    def _known_categories(cls, v: list[str]) -> list[str]:
        unknown = set(v) - _PUSH_CATEGORIES
        if unknown:
            raise ValueError(f"Unknown categories: {sorted(unknown)}")
        return v


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2000)


class PushSubscriptionOut(BaseModel):
    id: str
    endpoint: str
    categories: list[str]


class SavedItem(BaseModel):
    id: str
    title: str
    url: str
    summary: str
    source: SourceRef
    published_at: datetime
    saved_at: datetime

    @field_validator("published_at", "saved_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _as_utc(v)


# ---- Job descriptions --------------------------------------------------------


class JDIn(BaseModel):
    title: str | None = Field(default=None, max_length=140)
    company_id: str | None = None
    role_id: str | None = None
    company_name: str | None = Field(default=None, max_length=140)
    text: str = Field(min_length=40, max_length=30_000)


class JDSkill(BaseModel):
    capability_id: str
    name: str
    kind: CapabilityKind
    user_has_it: bool


class JDOut(BaseModel):
    id: str
    title: str | None
    company: NamedRef | None
    role: RoleRef | None
    company_name: str | None
    created_at: datetime
    skills: list[JDSkill]
    coverage: int  # percent of this job's skills the reader already has

    @field_validator("created_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _as_utc(v)


class JDPatch(BaseModel):
    title: str | None = Field(default=None, max_length=140)
    company_id: str | None = None
    role_id: str | None = None
    company_name: str | None = Field(default=None, max_length=140)


class JDGap(BaseModel):
    capability_id: str
    name: str
    kind: CapabilityKind
    jd_count: int
    jd_total: int
    user_has_it: bool


class JDGapsOut(BaseModel):
    jd_count: int
    coverage: int
    skills: list[JDGap]


class WebResultOut(BaseModel):
    title: str
    snippet: str
    url: str


class SuggestIn(BaseModel):
    query: str = Field(min_length=1, max_length=140)
    website: str | None = Field(default=None, max_length=300)  # companies only; ignored for roles


class RoleSuggestOut(BaseModel):
    matches: list[RoleRef]
    web_results: list[WebResultOut]


class CompanySuggestOut(BaseModel):
    matches: list[CompanyOut]
    web_results: list[WebResultOut]
    site_meta: WebResultOut | None = None


class AddRoleIn(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    domain_id: str | None = None
    description: str | None = Field(default=None, max_length=500)


class AddCompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    website: str | None = Field(default=None, max_length=300)
