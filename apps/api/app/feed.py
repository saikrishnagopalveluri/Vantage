"""Builds a user's relevance context and ranks articles against it."""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    JD,
    Article,
    ArticleTag,
    Capability,
    Company,
    CompanyRoleCapability,
    Domain,
    Industry,
    InteractionAction,
    JDCapability,
    ProfileStatus,
    Role,
    RoleCapability,
    TagType,
    Topic,
    UserCapability,
    UserDomain,
    UserInteraction,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)
from app.relevance import ArticleTags, ProfileTags, score_article
from app.hiring import canonical
from app.why import Matched, explain

Lens = Literal["for_you", "companies", "skills"]
Tier = Literal["critical", "relevant", "explore"]

WINDOW_DAYS = 45
MAX_CANDIDATES = 600
CRITICAL_MIN = 70.0
RELEVANT_MIN = 40.0
# Below this an article is noise for this reader, however many things it loosely touches.
MIN_SCORE = 12.0

# Behavioural learning: what a reader saves, opens and dismisses nudges similar stories.
SAVED_SIGNAL = 1.0
READ_SIGNAL = 0.4
BOOST_PER_SIGNAL = 2.0
BOOST_CAP = 8.0
PENALTY_PER_SIGNAL = 6.0
PENALTY_CAP = 20.0
LEARNED_TAG_TYPES = (TagType.COMPANY, TagType.CAPABILITY, TagType.TOPIC)

# Two headlines this similar (within a few days) are the same story from different outlets.
DUPLICATE_JACCARD = 0.5
DUPLICATE_WINDOW_DAYS = 4
_STOPWORDS = frozenset(
    "a an the of to in on for and or with by at as from is are be it its this that after over new says say "
    "will its into amid than more how why what who".split()
)


def tier_for(score: float) -> Tier:
    return "critical" if score >= CRITICAL_MIN else "relevant" if score >= RELEVANT_MIN else "explore"


def title_tokens(title: str) -> frozenset[str]:
    return frozenset(t for t in re.findall(r"[a-z0-9]+", title.lower()) if t not in _STOPWORDS and len(t) > 1)


def is_duplicate(a: frozenset[str], b: frozenset[str]) -> bool:
    if len(a) < 4 or len(b) < 4:
        return False
    return len(a & b) / len(a | b) >= DUPLICATE_JACCARD


@dataclass
class Context:
    status: ProfileStatus
    tags: ProfileTags
    owned: frozenset[str]
    wanted: frozenset[str]
    company_ids: frozenset[str]  # target + current companies
    target_company_ids: frozenset[str]
    names: dict[str, str]  # id -> display name, for every entity that can be matched
    domain_of: dict[str, str] = field(default_factory=dict)  # role/capability/topic id -> domain id
    signals: Counter = field(default_factory=Counter)  # (TagType, ref_id) -> +liked / -disliked


def load_context(db: Session, profile: UserProfile) -> Context:
    user_id = profile.user_id
    target_roles = set(db.scalars(select(UserTargetRole.role_id).where(UserTargetRole.user_id == user_id)))
    target_companies = set(
        db.scalars(select(UserTargetCompany.company_id).where(UserTargetCompany.user_id == user_id))
    )
    owned = set(db.scalars(select(UserCapability.capability_id).where(UserCapability.user_id == user_id)))
    followed_domains = set(db.scalars(select(UserDomain.domain_id).where(UserDomain.user_id == user_id)))

    role_ids = set(target_roles)
    if profile.current_role_id:
        role_ids.add(profile.current_role_id)
    # Skills live on the role a title belongs to, so a variant title asks for its parent's skills.
    role_rows = list(db.scalars(select(Role).where(Role.id.in_(role_ids)))) if role_ids else []
    skill_role_ids = {r.parent_id or r.id for r in role_rows}
    wanted = set(db.scalars(select(RoleCapability.capability_id).where(RoleCapability.role_id.in_(skill_role_ids))))
    wanted |= set(
        db.scalars(
            select(CompanyRoleCapability.capability_id).where(
                CompanyRoleCapability.role_id.in_(skill_role_ids),
                CompanyRoleCapability.company_id.in_(target_companies),
            )
        )
    )
    wanted |= set(
        db.scalars(
            select(JDCapability.capability_id).join(JD, JD.id == JDCapability.jd_id).where(JD.user_id == user_id)
        )
    )

    current_ids = {profile.current_company_id} - {None}
    company_rows = list(db.scalars(select(Company).where(Company.id.in_(target_companies | current_ids))))
    target_industries = {c.industry_id for c in company_rows if c.id in target_companies and c.industry_id}

    names: dict[str, str] = {}
    domain_of: dict[str, str] = {}
    for domain in db.scalars(select(Domain)):
        names[domain.id] = domain.name
    for role in role_rows:
        names[role.id] = role.title
        if role.domain_id or role.parent_id:
            domain_of[role.id] = role.domain_id or db.get(Role, role.parent_id).domain_id
    for company in company_rows:
        names[company.id] = company.name

    # The domains a reader cares about: those they follow, plus those of the roles they want or hold.
    domains = set(followed_domains) | {domain_of[r] for r in role_ids if r in domain_of}

    tags = ProfileTags(
        current_role=profile.current_role_id,
        current_company=profile.current_company_id,
        current_industry=profile.current_industry_id,
        target_roles=frozenset(target_roles),
        target_companies=frozenset(target_companies),
        target_industries=frozenset(i for i in target_industries if i),
        capabilities=frozenset(wanted | owned),
        domains=frozenset(domains),
    )
    return Context(
        status=profile.profile_status,
        tags=tags,
        owned=frozenset(owned),
        wanted=frozenset(wanted),
        company_ids=frozenset(target_companies | current_ids),
        target_company_ids=frozenset(target_companies),
        names=names,
        domain_of=domain_of,
        signals=_behaviour_signals(db, user_id),
    )


def hydrate(db: Session, ctx: "Context", ids: set[str]) -> None:
    """Fetch display names (and fields of work) for just the entities a request touches."""
    missing = [i for i in ids if i not in ctx.names]
    for start in range(0, len(missing), 500):  # stay well under SQLite's bound-variable limit
        chunk = missing[start : start + 500]
        for model, attr in ((Company, "name"), (Capability, "name"), (Topic, "name"), (Role, "title"), (Industry, "name")):
            for row in db.scalars(select(model).where(model.id.in_(chunk))):
                ctx.names[row.id] = getattr(row, attr)
                if model in (Role, Capability, Topic) and row.domain_id:
                    ctx.domain_of[row.id] = row.domain_id


def _behaviour_signals(db: Session, user_id: str) -> Counter:
    """+ for tags on stories the reader saved or opened, - for tags on stories they dismissed."""
    rows = db.execute(
        select(UserInteraction.article_id, UserInteraction.action)
        .where(UserInteraction.user_id == user_id)
        .order_by(UserInteraction.created_at.desc())
        .limit(300)
    ).all()
    if not rows:
        return Counter()
    value = {
        InteractionAction.SAVED: SAVED_SIGNAL,
        InteractionAction.READ: READ_SIGNAL,
        InteractionAction.DISMISSED: -1.0,
    }
    per_article: dict[str, float] = {}
    for article_id, action in rows:
        per_article[article_id] = per_article.get(article_id, 0.0) + value[action]
    signals: Counter = Counter()
    for tag in db.scalars(
        select(ArticleTag).where(
            ArticleTag.article_id.in_(per_article), ArticleTag.tag_type.in_(LEARNED_TAG_TYPES)
        )
    ):
        signals[(tag.tag_type, tag.ref_id)] += per_article[tag.article_id]
    return signals


@dataclass
class RankedArticle:
    article: Article
    published: datetime  # timezone-aware
    score: float
    tier: Tier
    why: str
    action: str
    matched: dict[str, list[str]]
    domains: list[str]
    also_covered_by: list[str] = field(default_factory=list)


def _tags_for(db: Session, article_ids: list[str]) -> dict[str, dict[TagType, dict[str, float]]]:
    grouped: dict[str, dict[TagType, dict[str, float]]] = {i: {t: {} for t in TagType} for i in article_ids}
    for tag in db.scalars(select(ArticleTag).where(ArticleTag.article_id.in_(article_ids))):
        grouped[tag.article_id][tag.tag_type][tag.ref_id] = tag.weight
    return grouped


def _article_domains(ctx: Context, tags: dict[TagType, dict[str, float]]) -> dict[str, float]:
    """A story belongs to the domains of the roles, skills and topics it names."""
    domains: dict[str, float] = {}
    for tag_type in (TagType.ROLE, TagType.CAPABILITY, TagType.TOPIC):
        for ref_id, weight in tags[tag_type].items():
            domain = ctx.domain_of.get(ref_id)
            if domain:
                domains[domain] = max(domains.get(domain, 0.0), weight)
    return domains


def _behaviour_adjustment(ctx: Context, tags: dict[TagType, dict[str, float]], protected: bool) -> float:
    liked = disliked = 0.0
    for tag_type in LEARNED_TAG_TYPES:
        for ref_id in tags[tag_type]:
            signal = ctx.signals.get((tag_type, ref_id), 0.0)
            if signal > 0:
                liked += signal
            elif signal < 0:
                disliked += -signal
    boost = min(BOOST_CAP, BOOST_PER_SIGNAL * liked)
    # A company the reader explicitly targets or works for is never buried by a past dismissal.
    penalty = min(PENALTY_CAP, PENALTY_PER_SIGNAL * disliked) * (0.25 if protected else 1.0)
    return boost - penalty


def rank(
    db: Session,
    profile: UserProfile,
    ctx: Context,
    lens: Lens,
    now: datetime | None = None,
    domain_id: str | None = None,
) -> list[RankedArticle]:
    now = now or datetime.now(timezone.utc)
    dismissed = set(
        db.scalars(
            select(UserInteraction.article_id).where(
                UserInteraction.user_id == profile.user_id,
                UserInteraction.action == InteractionAction.DISMISSED,
            )
        )
    )
    articles = db.scalars(
        select(Article)
        .where(Article.published_at >= now - timedelta(days=WINDOW_DAYS))
        .order_by(Article.published_at.desc())
        .limit(MAX_CANDIDATES)
    ).all()
    tag_map = _tags_for(db, [a.id for a in articles])
    hydrate(db, ctx, {ref for by_type in tag_map.values() for refs in by_type.values() for ref in refs} | set(ctx.tags.target_industries))
    gaps = ctx.wanted - ctx.owned
    cur = ctx.tags

    def names(ids) -> list[str]:
        return sorted(ctx.names[i] for i in ids if i in ctx.names)

    ranked: list[RankedArticle] = []
    for article in articles:
        if article.id in dismissed:
            continue
        t = tag_map[article.id]
        if lens == "companies" and not (t[TagType.COMPANY].keys() & ctx.company_ids):
            continue
        if lens == "skills" and not (t[TagType.CAPABILITY].keys() & gaps):
            continue
        article_domains = _article_domains(ctx, t)
        if domain_id and domain_id not in article_domains:
            continue

        published = article.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        score = score_article(
            cur,
            ArticleTags(
                roles=t[TagType.ROLE],
                companies=t[TagType.COMPANY],
                industries=t[TagType.INDUSTRY],
                capabilities=t[TagType.CAPABILITY],
                domains=article_domains,
            ),
            ctx.status,
            (now - published).total_seconds() / 86400,
        )
        if score <= 0:
            continue
        protected = bool(t[TagType.COMPANY].keys() & ctx.company_ids)
        score = round(min(100.0, max(0.0, score + _behaviour_adjustment(ctx, t, protected))), 1)
        if score < MIN_SCORE:
            continue

        matched = Matched(
            current_company=ctx.names.get(cur.current_company) if cur.current_company in t[TagType.COMPANY] else None,
            current_role=ctx.names.get(cur.current_role) if cur.current_role in t[TagType.ROLE] else None,
            target_companies=names(t[TagType.COMPANY].keys() & ctx.target_company_ids),
            target_roles=names(t[TagType.ROLE].keys() & cur.target_roles),
            gap_capabilities=names(t[TagType.CAPABILITY].keys() & gaps),
            owned_capabilities=names(t[TagType.CAPABILITY].keys() & ctx.owned),
            industries=names(t[TagType.INDUSTRY].keys() & (cur.target_industries | ({cur.current_industry} - {None}))),
            topics=names(t[TagType.TOPIC].keys() & {i for i in t[TagType.TOPIC] if ctx.domain_of.get(i) in cur.domains}),
            domains=names(article_domains.keys() & cur.domains),
        )
        explained = explain(ctx.status, matched)
        if explained is None:
            continue
        why, action = explained
        top_domains = sorted(article_domains, key=article_domains.get, reverse=True)[:2]
        ranked.append(
            RankedArticle(
                article=article,
                published=published,
                score=score,
                tier=tier_for(score),
                why=why,
                action=action,
                matched={
                    "companies": names(t[TagType.COMPANY]),
                    "roles": names(t[TagType.ROLE]),
                    "industries": names(t[TagType.INDUSTRY]),
                    "capabilities": names(t[TagType.CAPABILITY]),
                    "topics": names(t[TagType.TOPIC]),
                },
                domains=names(top_domains),
            )
        )
    ranked.sort(key=lambda r: (-r.score, -r.article.source.authority, -r.published.timestamp()))
    return collapse_duplicates(ranked)


def collapse_duplicates(ranked: list[RankedArticle]) -> list[RankedArticle]:
    """Keep the best-ranked copy of each story and record who else covered it."""
    leaders: list[tuple[RankedArticle, frozenset[str]]] = []
    for item in ranked:
        tokens = title_tokens(item.article.title)
        for leader, leader_tokens in leaders:
            close_in_time = abs((leader.published - item.published).days) <= DUPLICATE_WINDOW_DAYS
            if close_in_time and is_duplicate(tokens, leader_tokens):
                other = item.article.source.name
                if other != leader.article.source.name and other not in leader.also_covered_by:
                    leader.also_covered_by.append(other)
                break
        else:
            leaders.append((item, tokens))
    return [leader for leader, _ in leaders]


@dataclass
class SearchHit:
    article: Article
    published: datetime
    tags: dict[str, list[str]]


def article_hits(db: Session, articles: list[Article]) -> list[SearchHit]:
    """Attach readable tag names to articles, for listings that aren't personalised."""
    if not articles:
        return []
    tag_map = _tags_for(db, [a.id for a in articles])
    wanted = {ref for a in articles for by_type in tag_map[a.id].values() for ref in by_type}
    labels: dict[str, str] = {}
    for model, attr in ((Company, "name"), (Capability, "name"), (Topic, "name")):
        for row in db.scalars(select(model).where(model.id.in_(wanted))):
            labels[row.id] = getattr(row, attr)
    hits = []
    for article in articles:
        published = article.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        t = tag_map[article.id]
        hits.append(
            SearchHit(
                article,
                published,
                {
                    "companies": sorted(labels[i] for i in t[TagType.COMPANY] if i in labels),
                    "capabilities": sorted(labels[i] for i in t[TagType.CAPABILITY] if i in labels),
                    "topics": sorted(labels[i] for i in t[TagType.TOPIC] if i in labels),
                },
            )
        )
    return hits


def search_articles(db: Session, q: str, limit: int = 30) -> list[SearchHit]:
    """Plain text search over headlines and teasers: every word must appear. Not personalised."""
    words = [w for w in re.findall(r"\w+", q.lower()) if len(w) > 1][:6]
    if not words:
        return []
    stmt = select(Article).order_by(Article.published_at.desc()).limit(limit)
    for word in words:
        like = f"%{word}%"
        stmt = stmt.where(Article.title.ilike(like) | Article.summary.ilike(like))
    return article_hits(db, list(db.scalars(stmt)))
