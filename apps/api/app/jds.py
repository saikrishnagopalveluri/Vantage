"""Find the skills and tools a job description actually names. Grounded: a capability is only
returned if its own name or alias appears in the text, so nothing can be invented."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Capability
from app.tagging import _pattern

MAX_JDS = 30


def _term_pattern(term: str, generic: bool) -> re.Pattern[str]:
    # Generic skills ("communication") are usually lower-case in a JD, so they match any case.
    # Tools and proper names keep the tagger's stricter rules ("Excel" is not "excel at").
    if generic and len(term) > 3:
        return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
    return _pattern(term)


def extract_skills(db: Session, text: str) -> list[Capability]:
    lowered = text.lower()
    found: list[Capability] = []
    for cap in db.scalars(select(Capability)):
        generic = not cap.taggable
        for term in {cap.name, *(cap.aliases or [])}:
            term = term.strip()
            if not term or term.lower() not in lowered:
                continue
            if _term_pattern(term, generic).search(text):
                if not any(re.search(b, text, re.IGNORECASE) for b in (cap.blockers or [])):
                    found.append(cap)
                break
    return found
