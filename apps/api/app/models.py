import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _enum(cls: type[enum.Enum]) -> Enum:
    return Enum(cls, native_enum=False, values_callable=lambda e: [m.value for m in e])


class Base(DeclarativeBase):
    pass


class ProfileStatus(str, enum.Enum):
    TARGETING = "targeting"
    PLACED = "placed"


class CapabilityKind(str, enum.Enum):
    SKILL = "skill"
    TOOL = "tool"


# ---- Taxonomy -------------------------------------------------------------


class Domain(Base):
    """A career category (Marketing, Finance, Software Engineering, ...)."""

    __tablename__ = "domains"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True)
    slug: Mapped[str] = mapped_column(String, unique=True)
    group: Mapped[str] = mapped_column(String, default="")


class Industry(Base):
    __tablename__ = "industries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, unique=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    domain_id: Mapped[str | None] = mapped_column(ForeignKey("domains.id"), index=True)
    domain: Mapped["Domain | None"] = relationship()
    parent: Mapped["Role | None"] = relationship(remote_side="Role.id", foreign_keys="Role.parent_id")
    # A job title that is a variant of another role points at it; skills live on the parent.
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"), index=True)
    # Only hand-curated roles tag news; 45,000 imported titles ("Manager") would tag everything.
    taggable: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String, default="curated")
    onet_code: Mapped[str | None] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    # Shown first to management students (MBA, PGDM), Vantage's first audience.
    mba: Mapped[bool] = mapped_column(default=False, index=True)


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    industry_id: Mapped[str | None] = mapped_column(ForeignKey("industries.id"), index=True)
    industry: Mapped[Industry | None] = relationship()
    # Curated companies and distinctive imported names tag news; the long tail is for picking and browsing.
    taggable: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String, default="curated")
    ticker: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    external_id: Mapped[str | None] = mapped_column(String, index=True)
    mba: Mapped[bool] = mapped_column(default=False, index=True)


class Capability(Base):
    """A skill or a tool. One table so gap analysis ranks both in a single list."""

    __tablename__ = "capabilities"
    __table_args__ = (UniqueConstraint("name", "kind"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    kind: Mapped[CapabilityKind] = mapped_column(_enum(CapabilityKind))
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    # Generic skills ("Communication") matter for gap analysis but are too vague to tag news with.
    taggable: Mapped[bool] = mapped_column(default=True)
    source: Mapped[str] = mapped_column(String, default="curated")
    mba: Mapped[bool] = mapped_column(default=False, index=True)
    domain_id: Mapped[str | None] = mapped_column(ForeignKey("domains.id"), index=True)
    domain: Mapped["Domain | None"] = relationship()


class Topic(Base):
    """A theme news is about (Interest Rates, Layoffs, ...). Ties untargeted news to a domain."""

    __tablename__ = "topics"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    domain_id: Mapped[str] = mapped_column(ForeignKey("domains.id"), index=True)
    domain: Mapped[Domain] = relationship()


class IndustryDomain(Base):
    """Which fields of work a company in this industry hires for. Hiring is derived from this,
    never stored per company: 15,000 companies x thousands of roles would be millions of rows."""

    __tablename__ = "industry_domains"
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"), primary_key=True)
    domain_id: Mapped[str] = mapped_column(ForeignKey("domains.id"), primary_key=True)


class RoleIndustry(Base):
    """Optional: restrict a role to certain industries (an Actuarial Analyst works in insurance)."""

    __tablename__ = "role_industries"
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"), primary_key=True)


class RoleCapability(Base):
    """Generic taxonomy: what this role typically requires, at any company."""

    __tablename__ = "role_capabilities"
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    capability_id: Mapped[str] = mapped_column(ForeignKey("capabilities.id"), primary_key=True, index=True)


class CompanyRoleCapability(Base):
    """Company-specific override of RoleCapability (e.g. from placement reports)."""

    __tablename__ = "company_role_capabilities"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    capability_id: Mapped[str] = mapped_column(ForeignKey("capabilities.id"), primary_key=True)


# ---- Users & profile (ADR-01) --------------------------------------------


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str | None] = mapped_column(String, unique=True)
    name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Account(Base):
    """A sign-in for a user. The user row itself is created at onboarding, so `user_id` is just an id."""

    __tablename__ = "accounts"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Consent(Base):
    """Proof that someone agreed to the terms and privacy policy, and which versions. Removed with the user's data."""

    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True)  # no FK: an account consents before its user row exists
    terms_version: Mapped[str] = mapped_column(String)
    privacy_version: Mapped[str] = mapped_column(String)
    over_18: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String)  # signup | guest
    given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    profile_status: Mapped[ProfileStatus] = mapped_column(
        _enum(ProfileStatus), default=ProfileStatus.TARGETING
    )
    current_role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"))
    current_company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"))
    current_industry_id: Mapped[str | None] = mapped_column(ForeignKey("industries.id"))
    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_role_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    current_role: Mapped[Role | None] = relationship(foreign_keys=[current_role_id])
    current_company: Mapped[Company | None] = relationship(foreign_keys=[current_company_id])
    current_industry: Mapped[Industry | None] = relationship(foreign_keys=[current_industry_id])
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class UserTargetRole(Base):
    __tablename__ = "user_target_roles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)


class UserDomain(Base):
    """A career category the user follows."""

    __tablename__ = "user_domains"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    domain_id: Mapped[str] = mapped_column(ForeignKey("domains.id"), primary_key=True)


class UserTargetCompany(Base):
    __tablename__ = "user_target_companies"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), primary_key=True)


class UserCapability(Base):
    """Capabilities the user already has (self-declared for now)."""

    __tablename__ = "user_capabilities"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    capability_id: Mapped[str] = mapped_column(ForeignKey("capabilities.id"), primary_key=True)


class ProfileEvent(Base):
    """Append-only log of profile transitions ('placed', 'role_changed')."""

    __tablename__ = "profile_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserStreak(Base):
    """How many days in a row a user has opened Vantage. Touched at most once per calendar day (UTC);
    a same-day touch is a no-op, so any page that wants to count today's visit can call it freely."""

    __tablename__ = "user_streaks"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    current_streak: Mapped[int] = mapped_column(default=0)
    longest_streak: Mapped[int] = mapped_column(default=0)
    last_active_on: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


# ---- Job descriptions -----------------------------------------------------


class JD(Base):
    """A job description the user pasted in. Link it to a company and role, or neither."""

    __tablename__ = "jds"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str | None] = mapped_column(String)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"))
    role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"))
    company_name: Mapped[str | None] = mapped_column(String)
    raw_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    company: Mapped["Company | None"] = relationship()
    role: Mapped["Role | None"] = relationship()


class JDCapability(Base):
    """Capabilities extracted from a JD."""

    __tablename__ = "jd_capabilities"
    jd_id: Mapped[str] = mapped_column(ForeignKey("jds.id"), primary_key=True)
    capability_id: Mapped[str] = mapped_column(ForeignKey("capabilities.id"), primary_key=True)


# ---- Content ---------------------------------------------------------------


class IngestRun(Base):
    """One scheduled or manual pull of the feeds. The scheduler reads these to decide what is due
    and to avoid two processes ingesting at once."""

    __tablename__ = "ingest_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String, index=True)  # hourly | daily | manual
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    articles_added: Mapped[int] = mapped_column(default=0)
    articles_pruned: Mapped[int] = mapped_column(default=0)
    sources_ok: Mapped[int] = mapped_column(default=0)
    sources_failed: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)


class Source(Base):
    """A curated feed. Authority is a 1-5 editorial score used to break ties, not a ranker input yet."""

    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True)
    feed_url: Mapped[str] = mapped_column(String, unique=True)
    authority: Mapped[int] = mapped_column(default=3)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class Article(Base):
    """Metadata + a short publisher teaser only. We link out; we never store full text."""

    __tablename__ = "articles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String, unique=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    # A little more of the publisher's own feed text, used only to build the expandable brief.
    body: Mapped[str] = mapped_column(Text, default="")
    brief: Mapped[dict | None] = mapped_column(JSON)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    source: Mapped[Source] = relationship()


class TagType(str, enum.Enum):
    ROLE = "role"
    COMPANY = "company"
    INDUSTRY = "industry"
    CAPABILITY = "capability"
    TOPIC = "topic"


class ArticleTag(Base):
    __tablename__ = "article_tags"
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    tag_type: Mapped[TagType] = mapped_column(_enum(TagType), primary_key=True)
    ref_id: Mapped[str] = mapped_column(String, primary_key=True)
    # 1.0 when the entity is named in the headline, lower when only the teaser mentions it.
    weight: Mapped[float] = mapped_column(default=1.0)


class InteractionAction(str, enum.Enum):
    SAVED = "saved"
    DISMISSED = "dismissed"
    READ = "read"


class UserInteraction(Base):
    __tablename__ = "user_interactions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    action: Mapped[InteractionAction] = mapped_column(_enum(InteractionAction), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
