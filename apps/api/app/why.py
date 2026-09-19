"""Retrieval-then-generate "why this matters" + action, template-based.

The sentence is composed only from entities the tagger and scorer already matched, so it can
never claim something about the article or the user that the data doesn't support.
"""

from dataclasses import dataclass, field

from app.models import ProfileStatus


@dataclass
class Matched:
    """Display names of the entities that overlap between this user and this article."""

    current_company: str | None = None
    current_role: str | None = None
    target_companies: list[str] = field(default_factory=list)
    target_roles: list[str] = field(default_factory=list)
    gap_capabilities: list[str] = field(default_factory=list)
    owned_capabilities: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)


def _join(names: list[str], limit: int = 2) -> str:
    shown = names[:limit]
    if len(names) > limit:
        shown.append(f"{len(names) - limit} more")
    return ", ".join(shown[:-1]) + f" and {shown[-1]}" if len(shown) > 1 else shown[0]


def explain(status: ProfileStatus, m: Matched) -> tuple[str, str] | None:
    """(why, action), or None when nothing matched."""
    reasons: list[str] = []
    action: str | None = None
    targeting = status == ProfileStatus.TARGETING

    if m.current_company:
        reasons.append(f"It covers {m.current_company}, where you work.")
        action = f"Keep this in mind for your work at {m.current_company}."
    if m.target_companies:
        names = _join(m.target_companies)
        verb = "is one of your target companies" if len(m.target_companies) == 1 else "are among your target companies"
        reasons.append(f"{names} {verb}." if targeting else f"It covers {names}, a company you're tracking.")
        action = action or (
            f"Note this for your {m.target_companies[0]} interviews."
            if targeting
            else f"Track how {m.target_companies[0]} is moving."
        )
    if m.current_role:
        reasons.append(f"It mentions {m.current_role}, your role.")
    elif m.target_roles:
        reasons.append(f"It mentions {_join(m.target_roles)}, a role you're targeting.")
    if m.gap_capabilities:
        names = _join(m.gap_capabilities)
        where = "roles you're targeting" if targeting else "your role"
        verb = "shows" if len(m.gap_capabilities) == 1 else "show"
        reasons.append(f"{names} {verb} up in requirements for {where}, and isn't on your profile yet.")
        action = (
            f"Try {m.gap_capabilities[0]} on a small task this week"
            + (" and add it to your prep." if targeting else ".")
        )
    elif m.owned_capabilities:
        reasons.append(f"It relates to {_join(m.owned_capabilities)}, which you already have.")
    if not reasons and m.topics:
        reasons.append(f"It's about {_join(m.topics)}, a theme in {_join(m.domains) if m.domains else 'a field'} you follow.")
    if not reasons and m.domains:
        reasons.append(f"It's in {_join(m.domains)}, a field you follow.")
    if not reasons and m.industries:
        reasons.append(
            f"It's about {_join(m.industries)}, "
            + ("an industry you're targeting." if targeting else "your industry.")
        )

    if not reasons:
        return None
    return " ".join(reasons[:2]), action or "Skim it and save it if it's useful."
