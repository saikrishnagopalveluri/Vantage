"""Pop quiz questions, made from what Vantage already knows.

Roles, skills, companies and industries come from the taxonomy, headlines come from the stories in the
feed, and the basic concepts come from a hand-written bank. Questions lean towards the player's own
target roles, companies and fields when they have any, and get harder as the level goes up. The stream
never runs out: the players are asked for a batch at a time, and each question has a key so the ones
they have already seen can be left out.
"""

import hashlib
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hiring import canonical
from app.models import (
    Article,
    ArticleTag,
    Capability,
    Company,
    Domain,
    Industry,
    Role,
    RoleCapability,
    TagType,
    UserDomain,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)
from app.seed_data.quiz_concepts import CONCEPTS
from app.story import story_kind

# Only the kinds that are clear from a headline. "Technology" and "markets" overlap with the others (an AI deal is
# both), so a question about them could have two right answers.
KIND_LABELS = {
    "leadership": "A leadership change",
    "deal": "A deal or funding round",
    "results": "Company results",
    "hiring": "Hiring or pay",
    "policy": "Policy or regulation",
    "launch": "A launch or campaign",
    "expansion": "An expansion",
}
STORY_WINDOW_DAYS = 45
MAX_LEVEL = 10

# What to ask at each level. From level 3 up the mix stays the same and the wrong answers get closer to the right one.
WEIGHTS: dict[int, dict[str, int]] = {
    1: {"concept": 5, "company_industry": 3, "role_field": 2},
    2: {"concept": 3, "company_industry": 2, "industry_company": 2, "role_field": 2, "role_skill": 3, "headline_kind": 1},
    3: {"concept": 3, "industry_company": 2, "role_field": 1, "role_skill": 3, "headline_kind": 2, "headline_company": 3},
}


@dataclass
class Question:
    kind: str
    prompt: str
    options: list[str]
    answer: int
    explain: str
    level: int
    area: str | None = None  # the field of work, shown as a label
    context: str | None = None
    key: str = ""
    subject: str = ""  # the company, role or industry asked about, so a batch does not repeat one

    def as_dict(self) -> dict:
        return {
            "id": self.key, "kind": self.kind, "prompt": self.prompt, "context": self.context, "options": self.options,
            "answer": self.answer, "explain": self.explain, "field": self.area, "level": self.level,
        }


@dataclass
class Taste:
    """What the player follows, so the questions can be about their world."""

    role_ids: set[str] = field(default_factory=set)
    company_ids: set[str] = field(default_factory=set)
    domain_ids: set[str] = field(default_factory=set)
    slugs: set[str] = field(default_factory=set)


@dataclass
class Pool:
    companies: list[tuple[str, str, str, list[str], bool]]  # id, name, industry_id, aliases, management-student flag
    industries: dict[str, str]
    roles: list[tuple[str, str, str | None, bool]]  # id, title, domain_id, management-student flag
    domains: dict[str, tuple[str, str]]  # id -> (name, slug)


def build_taste(db: Session, user_id: str) -> Taste:
    taste = Taste()
    taste.role_ids = set(db.scalars(select(UserTargetRole.role_id).where(UserTargetRole.user_id == user_id)))
    taste.company_ids = set(db.scalars(select(UserTargetCompany.company_id).where(UserTargetCompany.user_id == user_id)))
    taste.domain_ids = set(db.scalars(select(UserDomain.domain_id).where(UserDomain.user_id == user_id)))
    profile = db.get(UserProfile, user_id)
    if profile is not None:
        if profile.current_role_id:
            taste.role_ids.add(profile.current_role_id)
        if profile.current_company_id:
            taste.company_ids.add(profile.current_company_id)
    for role in db.scalars(select(Role).where(Role.id.in_(taste.role_ids))) if taste.role_ids else []:
        base = canonical(db, role)
        if base.domain_id:
            taste.domain_ids.add(base.domain_id)
    if taste.domain_ids:
        taste.slugs = set(db.scalars(select(Domain.slug).where(Domain.id.in_(taste.domain_ids))))
    return taste


def load_pool(db: Session) -> Pool:
    companies = [
        (c.id, c.name, c.industry_id, list(c.aliases or []), bool(c.mba))
        for c in db.scalars(select(Company).where(Company.source == "curated", Company.industry_id.is_not(None)))
    ]
    roles = [
        (r.id, r.title, r.domain_id, bool(getattr(r, "mba", False)))
        for r in db.scalars(select(Role).where(Role.source == "curated", Role.parent_id.is_(None), Role.domain_id.is_not(None)))
    ]
    return Pool(
        companies=companies,
        industries={i.id: i.name for i in db.scalars(select(Industry))},
        roles=roles,
        domains={d.id: (d.name, d.slug) for d in db.scalars(select(Domain))},
    )


def _key(kind: str, *parts: str) -> str:
    return hashlib.sha1("|".join((kind, *parts)).encode()).hexdigest()[:12]


def _finish(rng: random.Random, kind: str, prompt: str, right: str, wrong: list[str], explain: str, level: int, *, field_name: str | None = None, context: str | None = None, key_parts: tuple[str, ...] = (), subject: str = "") -> Question | None:
    """Four distinct options in a random order, with the right one among them."""
    seen = {right.strip().lower()}
    options = [right]
    for w in wrong:
        if w.strip().lower() not in seen:
            seen.add(w.strip().lower())
            options.append(w)
    if len(options) < 4:
        return None
    options = options[:4]
    rng.shuffle(options)
    return Question(
        kind=kind, prompt=prompt, options=options, answer=options.index(right), explain=explain, level=level,
        area=field_name, context=context, key=_key(kind, prompt, context or "", right, *key_parts), subject=subject,
    )


def _lean(rng: random.Random, items: list, favoured: set[str], id_of, flagged=lambda x: False):
    """Pick from the player's own things about half the time, then management-student favourites, then anything."""
    mine = [i for i in items if id_of(i) in favoured]
    if mine and rng.random() < 0.55:
        return rng.choice(mine)
    firsts = [i for i in items if flagged(i)]
    if firsts and rng.random() < 0.6:
        return rng.choice(firsts)
    return rng.choice(items) if items else None


# ---- generators -------------------------------------------------------------------------------------------


def q_company_industry(db, rng, pool, taste, level):
    company = _lean(rng, pool.companies, taste.company_ids, lambda c: c[0], lambda c: c[4])
    if company is None or len(pool.industries) < 4:
        return None
    cid, name, industry_id, _, _ = company
    right = pool.industries.get(industry_id)
    if not right:
        return None
    others = [n for i, n in pool.industries.items() if i != industry_id]
    return _finish(rng, "company_industry", f"Which industry is {name} in?", right, rng.sample(others, min(3, len(others))),
                   f"{name} is listed under {right}.", level, subject=name)


def q_industry_company(db, rng, pool, taste, level):
    by_industry: dict[str, list] = {}
    for c in pool.companies:
        by_industry.setdefault(c[2], []).append(c)
    industries = [i for i, cs in by_industry.items() if len(cs) >= 1 and i in pool.industries]
    if len(industries) < 2:
        return None
    industry_id = rng.choice(industries)
    right = _lean(rng, by_industry[industry_id], taste.company_ids, lambda c: c[0], lambda c: c[4])
    wrong_pool = [c for c in pool.companies if c[2] != industry_id]
    if right is None or len(wrong_pool) < 3:
        return None
    wrong = [c[1] for c in rng.sample(wrong_pool, 3)]
    name = pool.industries[industry_id]
    return _finish(rng, "industry_company", f"Which of these is in {name}?", right[1], wrong, f"{right[1]} is listed under {name}.", level, subject=right[1])


def q_role_field(db, rng, pool, taste, level):
    role = _lean(rng, pool.roles, taste.role_ids, lambda r: r[0], lambda r: r[3])
    if role is None or len(pool.domains) < 4:
        return None
    _, title, domain_id, _ = role
    if domain_id not in pool.domains:
        return None
    right = pool.domains[domain_id][0]
    others = [n for i, (n, _) in pool.domains.items() if i != domain_id]
    return _finish(rng, "role_field", f"In Vantage, which field is {title} listed under?", right, rng.sample(others, min(3, len(others))),
                   f"{title} sits in {right}.", level, field_name=right, subject=title)


def q_role_skill(db, rng, pool, taste, level):
    role = _lean(rng, pool.roles, taste.role_ids, lambda r: r[0], lambda r: r[3])
    if role is None:
        return None
    rid, title, domain_id, _ = role
    linked = list(db.execute(select(Capability.id, Capability.name, Capability.domain_id).join(RoleCapability, RoleCapability.capability_id == Capability.id).where(RoleCapability.role_id == rid)))
    if not linked:
        return None
    right = rng.choice(linked)
    linked_ids = {c[0] for c in linked}
    # Skills used across every field (Excel, Communication) would be right for almost any role, so they are never wrong answers.
    candidates = [c for c in db.execute(select(Capability.id, Capability.name, Capability.domain_id).where(Capability.source == "curated", Capability.domain_id.is_not(None)))
                  if c[0] not in linked_ids]
    if level >= 3:
        near = [c for c in candidates if c[2] == domain_id]
        candidates = near if len(near) >= 3 else candidates
    else:
        far = [c for c in candidates if c[2] != domain_id]
        candidates = far if len(far) >= 3 else candidates
    if len(candidates) < 3:
        return None
    wrong = [c[1] for c in rng.sample(candidates, 3)]
    name = pool.domains.get(domain_id, ("", ""))[0] or None
    return _finish(rng, "role_skill", f"Which of these is listed as a skill for {title}?", right[1], wrong,
                   f"{right[1]} is one of the skills listed for {title}.", level, field_name=name, subject=title)


def _recent_articles(db: Session, want_company: bool, taste: Taste, rng: random.Random, limit: int = 60):
    since = datetime.now(timezone.utc) - timedelta(days=STORY_WINDOW_DAYS)
    stmt = select(Article).where(Article.published_at >= since).order_by(Article.published_at.desc()).limit(400)
    articles = list(db.scalars(stmt))
    rng.shuffle(articles)
    if want_company and taste.company_ids:
        tagged = set(db.scalars(select(ArticleTag.article_id).where(ArticleTag.tag_type == TagType.COMPANY, ArticleTag.ref_id.in_(taste.company_ids))))
        articles.sort(key=lambda a: 0 if a.id in tagged else 1)
    return articles[:limit]


def _mask(title: str, terms: list[str]) -> str | None:
    for term in sorted(terms, key=len, reverse=True):
        pattern = re.compile(rf"(?<![\w]){re.escape(term)}(?![\w])", re.IGNORECASE)
        if pattern.search(title):
            return pattern.sub("_____", title)
    return None


def q_headline_company(db, rng, pool, taste, level):
    by_id = {c[0]: c for c in pool.companies}
    for article in _recent_articles(db, True, taste, rng):
        tagged = list(db.scalars(select(ArticleTag.ref_id).where(ArticleTag.article_id == article.id, ArticleTag.tag_type == TagType.COMPANY)))
        for cid in tagged:
            company = by_id.get(cid)
            if company is None:
                continue
            masked = _mask(article.title, [company[1], *company[3]])
            if masked is None or masked.count("_____") > 1 and len(masked) > 160:
                continue
            same = [c for c in pool.companies if c[2] == company[2] and c[0] != cid and c[1].lower() not in article.title.lower()]
            other = [c for c in pool.companies if c[2] != company[2] and c[1].lower() not in article.title.lower()]
            wrong_pool = same if level >= 3 and len(same) >= 3 else (same[:2] + other if len(same) >= 2 else other)
            if len(wrong_pool) < 3:
                continue
            wrong = [c[1] for c in rng.sample(wrong_pool, 3)]
            return _finish(rng, "headline_company", "Which company is this story about?", company[1], wrong,
                           f"The story is about {company[1]}. It was reported by {article.source.name}.", level,
                           context=masked, key_parts=(article.id,), subject=company[1])
    return None


def q_headline_kind(db, rng, pool, taste, level):
    for article in _recent_articles(db, False, taste, rng):
        kind = story_kind(article.title)
        if kind not in KIND_LABELS or len(article.title.split()) < 5:
            continue
        others = [label for k, label in KIND_LABELS.items() if k != kind]
        return _finish(rng, "headline_kind", "What kind of story is this headline?", KIND_LABELS[kind], rng.sample(others, 3),
                       f"It reads as {KIND_LABELS[kind].lower()}.", level, context=article.title, key_parts=(article.id,))
    return None


def q_concept(db, rng, pool, taste, level):
    ceiling = 1 if level <= 1 else 2 if level == 2 else 3
    bank = [c for c in CONCEPTS if c[1] <= ceiling]
    weighted = [c for c in bank for _ in range(3 if c[0] in taste.slugs else 1)]
    slug, lvl, prompt, right, wrong, explain = rng.choice(weighted)
    label = next((n for n, s in pool.domains.values() if s == slug), None)
    return _finish(rng, "concept", prompt, right, list(wrong), explain, level, field_name=label)


GENERATORS = {
    "concept": q_concept, "company_industry": q_company_industry, "industry_company": q_industry_company, "role_field": q_role_field,
    "role_skill": q_role_skill, "headline_company": q_headline_company,
    "headline_kind": q_headline_kind,
}


def make_questions(db: Session, user_id: str, count: int, level: int, seed: int | None = None, exclude: set[str] | None = None) -> list[Question]:
    rng = random.Random(seed)
    level = max(1, min(MAX_LEVEL, level))
    weights = WEIGHTS[min(level, 3)]
    taste, pool = build_taste(db, user_id), load_pool(db)
    seen = set(exclude or ())
    subjects: set[str] = set()
    out: list[Question] = []
    kinds, mass = list(weights), list(weights.values())
    for _ in range(count * 14):
        if len(out) >= count:
            break
        q = GENERATORS[rng.choices(kinds, mass)[0]](db, rng, pool, taste, level)
        if q is None or q.key in seen or (q.subject and q.subject in subjects):
            continue
        seen.add(q.key)
        subjects.add(q.subject)
        out.append(q)
    if len(out) < count:  # the data ran thin (a fresh database): fall back to the concept bank, repeats allowed
        for _ in range(count * 6):
            if len(out) >= count:
                break
            q = q_concept(db, rng, pool, taste, level)
            if q is not None and q.key not in {o.key for o in out}:
                out.append(q)
    return out
