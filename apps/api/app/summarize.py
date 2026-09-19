"""Extractive briefs: pick the most informative sentences from the publisher's own feed text.

Nothing is generated, so nothing can be invented. The brief is one or two short paragraphs plus a
few quick pointers, shown only when a reader expands a story.
"""

import re

MAX_PARAGRAPH_CHARS = 420
MAX_POINTER_CHARS = 130
MAX_POINTERS = 4
SHORT_NOTE = "The publisher's feed shared only a short excerpt. Open the article for the full story."

_BOILERPLATE = re.compile(
    r"appeared first on|read more|continue reading|click here|subscribe|sign up|newsletter|"
    r"all rights reserved|follow us|the post\b|view (the )?original",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]?\s+(?=[\"'(\[]?[A-Z0-9])")
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "at", "by", "from", "is", "are",
    "was", "were", "be", "as", "it", "its", "that", "this", "these", "those", "has", "have", "had", "will",
    "new", "says", "say", "after", "over", "into", "than", "their", "his", "her", "they", "he", "she",
}
_FACT = re.compile(r"\d|%|\$|₹|€|£|\b(million|billion|crore|lakh|per cent|percent)\b", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 2}


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _paragraph(sents: list[str]) -> str:
    """Whole sentences up to the limit. Only a single over-long sentence is cut short."""
    out = ""
    for s in sents:
        joined = f"{out} {s}".strip()
        if len(joined) > MAX_PARAGRAPH_CHARS:
            break
        out = joined
    return out or _clip(sents[0], MAX_PARAGRAPH_CHARS)


def sentences(text: str) -> list[str]:
    out = []
    for raw in _SENTENCE_SPLIT.split(re.sub(r"\s+", " ", text).strip()):
        s = raw.strip()
        if len(s) >= 35 and not _BOILERPLATE.search(s):
            out.append(s)
    return out


def _rank(title: str, sents: list[str]) -> list[int]:
    title_words = _tokens(title)
    scored = []
    for i, s in enumerate(sents):
        words = _tokens(s)
        overlap = len(words & title_words) / (len(title_words) or 1)
        score = 1.0 / (1 + 0.35 * i) + 1.5 * overlap + (0.4 if _FACT.search(s) else 0)
        if not 50 <= len(s) <= 260:
            score -= 0.3
        scored.append((score, i))
    return [i for _, i in sorted(scored, reverse=True)]


def build_brief(title: str, text: str) -> dict:
    """Returns {"paragraphs": [...], "pointers": [...], "note": str | None}."""
    sents = sentences(text)
    if len(sents) < 2:
        only = _clip(sents[0], MAX_PARAGRAPH_CHARS) if sents else ""
        return {"paragraphs": [only] if only else [], "pointers": [], "note": SHORT_NOTE}

    order = _rank(title, sents)
    first = sorted(order[:2])
    paragraphs = [_paragraph([sents[i] for i in first])]
    if len(sents) >= 5:
        second = sorted(order[2:4])
        paragraphs.append(_paragraph([sents[i] for i in second]))
        used = set(first) | set(second)
    else:
        used = set(first)

    # Pointers: what is left, facts first, each cut down to a line.
    rest = [i for i in order if i not in used]
    rest = [
        i
        for _, i in sorted(
            enumerate(rest),
            key=lambda pair: (len(sents[pair[1]]) > MAX_POINTER_CHARS, not _FACT.search(sents[pair[1]]), pair[0]),
        )
    ]
    pointers = [_clip(sents[i], MAX_POINTER_CHARS) for i in rest[:MAX_POINTERS]]
    return {"paragraphs": paragraphs, "pointers": pointers, "note": None if len(sents) >= 4 else SHORT_NOTE}
