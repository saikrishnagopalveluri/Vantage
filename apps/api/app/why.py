"""Retrieval-then-generate "why this matters" + "what to do", template-based.

The text is composed only from things the tagger and scorer already matched, plus the kind of story
the headline states (see app/story.py), so it can never claim something about the article or the
reader that the data doesn't support. The "why" says how the story connects to the reader and why
that kind of story is worth their time; the action is one concrete thing to do with it.
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
    gap_kinds: dict[str, str] = field(default_factory=dict)  # skill name -> "tool" or "skill"


# Why a kind of story is worth the reader's time, for someone job hunting and for someone working.
_WHY_TARGETING = {
    "leadership": "Leadership changes make good interview material because they show you follow the company.",
    "deal": "Deals and funding rounds come up in case rounds and finance interviews.",
    "results": "Results are a common way for interviewers to start, so know what moved.",
    "hiring": "Hiring and pay news shows what the market is paying for right now.",
    "policy": "Regulation shapes a whole industry, which makes it a good group-discussion topic.",
    "launch": "Launches and campaigns are common marketing and strategy examples.",
    "expansion": "Expansion news hints at where teams will hire next.",
    "tech": "Technology stories show which skills employers are starting to ask for.",
    "markets": "This is a market story, so read it for the reason behind the price move and skip the rest.",
}
_WHY_PLACED = {
    "leadership": "A leadership change can shift priorities in your function.",
    "deal": "Deals often change team structures and budgets.",
    "results": "Results usually set the targets your team is working toward.",
    "hiring": "Hiring and pay news affects your own market value.",
    "policy": "Regulation can change how your team works.",
    "launch": "Launches and campaigns show where competitors are placing their bets.",
    "expansion": "Expansion news shows where competitors are investing.",
    "tech": "Technology stories show what your peers are adopting.",
    "markets": "This is a market story, so read it for the reason behind the move.",
}

# What to do about a story on a company, by kind. {c} is the company.
_DO_TARGETING = {
    "leadership": "Note the name and background of the new leader. It is a strong line to bring up in an interview at {c}.",
    "deal": "Write down why {c} made this move and what it could change. It doubles as a ready case-interview example.",
    "results": "Write down two numbers from this story and what caused them. Use them the next time someone asks what you know about {c}.",
    "hiring": "Check {c}'s careers page this week for roles linked to this news.",
    "policy": "Write two lines on how this affects {c}. It works well as a group-discussion point.",
    "launch": "Note who the product is for and how it differs from what {c} sold before, then bring it up in your interview.",
    "expansion": "Look up where {c} is expanding and check whether roles are open there.",
    "tech": "See what the story says {c} is building, then check whether your skills list covers it.",
    "markets": "Note the one reason analysts give for the price view. It is a quick way to sound informed about {c}.",
}
_DO_PLACED = {
    "leadership": "Find out how this changes who you report to or work with, and adjust your plans.",
    "deal": "Ask your manager how this could affect your team's budget or priorities.",
    "results": "Compare it with your team's targets and share one takeaway at your next check-in.",
    "hiring": "Check what this means for your own pay and growth path.",
    "policy": "Ask your compliance or strategy team whether this changes anything you do.",
    "launch": "Look at how the launch is positioned and whether your team can learn from it.",
    "expansion": "Look for new roles or projects this opens up at {c}.",
    "tech": "Look at which tools this mentions and whether your team already uses them.",
    "markets": "Skim it and move on unless it changes {c}'s plans.",
}


def _join(names: list[str], limit: int = 2) -> str:
    shown = names[:limit]
    if len(names) > limit:
        shown.append(f"{len(names) - limit} more")
    return ", ".join(shown[:-1]) + f" and {shown[-1]}" if len(shown) > 1 else shown[0]


def _skill_action(m: Matched, targeting: bool) -> str:
    skill = m.gap_capabilities[0]
    done = "add it to your profile" if targeting else "use it on your next task"
    if m.gap_kinds.get(skill) == "tool":
        return f"Spend 30 minutes in {skill} this week and build one small example, then {done}."
    return f"Read up on {skill} this week and write down one real example of using it, then {done}."


def _action(status: ProfileStatus, m: Matched, kind: str | None, company: str | None) -> str:
    targeting = status == ProfileStatus.TARGETING
    if company and kind:
        return (_DO_TARGETING if targeting else _DO_PLACED)[kind].format(c=company)
    if m.gap_capabilities:
        return _skill_action(m, targeting)
    if company:
        return (
            f"Save this under {company} and reread it before your interview."
            if targeting
            else f"Share it with your team if it changes how you work at {company}."
        )
    role = m.current_role or (m.target_roles[0] if m.target_roles else None)
    if role:
        return (
            f"Add one line about this to your notes for {role} interviews."
            if targeting
            else f"Think about what this changes in your day as {role}."
        )
    if m.owned_capabilities:
        skill = m.owned_capabilities[0]
        return (
            f"Prepare one line on how you have used {skill}, and use this story as the example."
            if targeting
            else f"Note one way you could use {skill} on your next project."
        )
    field_name = _join(m.topics or m.domains or m.industries, 1)
    return (
        f"Save it if you want a talking point for {field_name} conversations."
        if targeting
        else "Save it for your next planning conversation."
    )


def explain(status: ProfileStatus, m: Matched, kind: str | None = None) -> tuple[str, str] | None:
    """(why, action), or None when nothing matched. `kind` is the kind of story from its headline."""
    reasons: list[str] = []
    targeting = status == ProfileStatus.TARGETING

    tracked = [c for c in m.target_companies if c != m.current_company]
    if m.current_company:
        reasons.append(f"It covers {m.current_company}, where you work.")
    if tracked:
        names = _join(tracked)
        verb = "is one of your target companies" if len(tracked) == 1 else "are among your target companies"
        reasons.append(f"{names} {verb}." if targeting else f"It covers {names}, a company you're tracking.")
    if m.current_role:
        reasons.append(f"It mentions {m.current_role}, your role.")
    elif m.target_roles:
        reasons.append(f"It mentions {_join(m.target_roles)}, a role you're targeting.")
    if m.gap_capabilities:
        names = _join(m.gap_capabilities)
        where = "roles you're targeting" if targeting else "your role"
        plural = len(m.gap_capabilities) > 1
        reasons.append(
            f"{names} {'show' if plural else 'shows'} up in requirements for {where}, "
            f"and {'they aren' if plural else 'it isn'}'t on your profile yet."
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
    parts = reasons[:2]
    if kind:
        parts.append((_WHY_TARGETING if targeting else _WHY_PLACED)[kind])
    company = m.current_company or (tracked[0] if tracked else None)
    return " ".join(parts), _action(status, m, kind, company)
