"""Deterministic taxonomy tagger: an article gets a tag only if the taxonomy's own name or
alias appears in its text. No model, so nothing can be tagged that the text doesn't say.

Accuracy levers, all explicit and testable (see tests/test_tagging_accuracy.py):
  * word-boundary matching, with case-sensitive matching for short / all-caps / single proper
    nouns ("SQL", "Excel") so ordinary words don't tag;
  * per-entity blockers: "Amazon" is vetoed next to "rainforest";
  * non-taggable capabilities: generic skills ("Communication") never tag news;
  * weights: an entity named in the headline counts fully, one only in the teaser counts less.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Capability, Company, Industry, Role, TagType, Topic

Tag = tuple[TagType, str]

TITLE_WEIGHT = 1.0
TEASER_WEIGHT = 0.6
IMPLIED_INDUSTRY_FACTOR = 0.8


@dataclass(frozen=True)
class _Entry:
    tag_type: TagType
    ref_id: str
    pattern: re.Pattern[str]
    blockers: tuple[re.Pattern[str], ...] = ()
    needle: str = ""  # the term, lower-cased: a cheap substring test before the regex


@dataclass(frozen=True)
class TagIndex:
    entries: tuple[_Entry, ...]
    company_industry: dict[str, str]


def _pattern(term: str) -> re.Pattern[str]:
    # Short, all-caps and single-word proper-noun terms (SQL, ITC, Excel, Python) are matched
    # case-sensitively so ordinary words ("excel at", "switch") don't tag. Multi-word
    # names ("Consumer Insights") are safe to match case-insensitively.
    single_proper_noun = " " not in term and term[:1].isupper()
    flags = 0 if (term.isupper() or len(term) <= 3 or single_proper_noun) else re.IGNORECASE
    return re.compile(rf"(?<![\w]){re.escape(term)}(?![\w])", flags)


def build_index(db: Session) -> TagIndex:
    entries: list[_Entry] = []

    def add(tag_type: TagType, ref_id: str, name: str, aliases: list[str] | None, blockers: list[str] | None = None):
        compiled = tuple(re.compile(b, re.IGNORECASE) for b in (blockers or []))
        for term in {name, *(aliases or [])}:
            if term.strip():
                entries.append(_Entry(tag_type, ref_id, _pattern(term.strip()), compiled, term.strip().lower()))

    for role in db.scalars(select(Role).where(Role.taggable.is_(True))):
        add(TagType.ROLE, role.id, role.title, role.aliases, role.blockers)
    for industry in db.scalars(select(Industry)):
        add(TagType.INDUSTRY, industry.id, industry.name, industry.aliases)
    companies = list(db.scalars(select(Company)))
    for company in companies:
        if not company.taggable:
            continue
        add(TagType.COMPANY, company.id, company.name, company.aliases, company.blockers)
    for capability in db.scalars(select(Capability).where(Capability.taggable.is_(True))):
        add(TagType.CAPABILITY, capability.id, capability.name, capability.aliases, capability.blockers)
    for topic in db.scalars(select(Topic)):
        add(TagType.TOPIC, topic.id, topic.name, topic.aliases, topic.blockers)
    return TagIndex(
        entries=tuple(entries),
        company_industry={c.id: c.industry_id for c in companies if c.industry_id},
    )


def tag_text(index: TagIndex, text: str) -> set[Tag]:
    """Every taxonomy entity named in `text`, minus vetoed ones, plus implied industries."""
    lowered = text.lower()
    tags = {
        (e.tag_type, e.ref_id)
        for e in index.entries
        if e.needle in lowered and e.pattern.search(text) and not any(b.search(text) for b in e.blockers)
    }
    # An article about a company is implicitly about that company's industry.
    for tag_type, ref_id in list(tags):
        if tag_type == TagType.COMPANY and ref_id in index.company_industry:
            tags.add((TagType.INDUSTRY, index.company_industry[ref_id]))
    return tags


def tag_article(index: TagIndex, title: str, summary: str) -> dict[Tag, float]:
    """Tag -> weight. Blockers are checked against headline and teaser together."""
    whole = f"{title}\n{summary}"
    in_title = tag_text(index, title)
    in_whole = tag_text(index, whole)
    weights: dict[Tag, float] = {}
    for tag in in_whole:
        weight = TITLE_WEIGHT if tag in in_title else TEASER_WEIGHT
        if tag[0] == TagType.INDUSTRY and tag not in in_title:
            # Implied from a teaser-only company mention: keep it proportional to that mention.
            weight = TEASER_WEIGHT * IMPLIED_INDUSTRY_FACTOR
        weights[tag] = weight
    return weights


def is_relevant_enough(weights: dict[Tag, float]) -> bool:
    """Ingest gate. Keep an article if its headline names anything in the taxonomy, or if the
    teaser names at least two distinct non-industry entities. A single incidental mention in the
    teaser is not enough to spend a reader's attention on."""
    if any(weight >= TITLE_WEIGHT for weight in weights.values()):
        return True
    teaser_entities = {tag for tag, w in weights.items() if tag[0] != TagType.INDUSTRY}
    return len(teaser_entities) >= 2
