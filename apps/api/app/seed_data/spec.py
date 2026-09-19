"""Compact text format for the taxonomy, plus the parsers that turn it into typed specs.

One entity per line, fields separated by " | ", list values separated by ";".

  capability:  Name | T(tool) or S(skill) | aliases | flags
  role:        Title | aliases | capability names | industry keys (empty = every industry)
  company:     Name | industry key | aliases | flags
  topic:       Name | aliases | flags

A leading "~" on a capability name marks it not taggable: it exists for gap analysis but is too
generic to tag news with ("~Communication"). A flag "avoid:REGEX" vetoes a tag when that pattern
appears in the text (for example Amazon with "rainforest").
"""

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    kind: str  # "tool" | "skill"
    domain: str | None
    aliases: tuple[str, ...] = ()
    taggable: bool = True
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoleSpec:
    title: str
    domain: str
    aliases: tuple[str, ...]
    capabilities: tuple[str, ...]
    industries: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompanySpec:
    name: str
    industry: str
    aliases: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class TopicSpec:
    name: str
    domain: str
    aliases: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


@dataclass
class Taxonomy:
    capabilities: list[CapabilitySpec] = field(default_factory=list)
    roles: list[RoleSpec] = field(default_factory=list)
    companies: list[CompanySpec] = field(default_factory=list)
    topics: list[TopicSpec] = field(default_factory=list)


def _lines(text: str):
    for number, raw in enumerate(text.strip().splitlines(), start=1):
        line = raw.strip()
        if line and not line.startswith("#"):
            # Whitespace-tolerant so an empty field ("a | | b") stays an empty field.
            yield number, [part.strip() for part in re.split(r"\s*\|\s*", line)]


def _list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(";") if item.strip())


def _blockers(value: str) -> tuple[str, ...]:
    return tuple(item[len("avoid:"):] for item in _list(value) if item.startswith("avoid:"))


def _pad(fields: list[str], size: int) -> list[str]:
    return fields + [""] * (size - len(fields))


def parse_capabilities(text: str, domain: str | None) -> list[CapabilitySpec]:
    specs = []
    for number, fields in _lines(text):
        name, kind, aliases, flags = _pad(fields, 4)[:4]
        if kind not in ("T", "S"):
            raise ValueError(f"capability line {number}: kind must be T or S, got {kind!r} ({name})")
        taggable = not name.startswith("~")
        blockers = _blockers(flags)
        specs.append(
            CapabilitySpec(
                name=name.lstrip("~"),
                kind="tool" if kind == "T" else "skill",
                domain=domain,
                aliases=_list(aliases),
                taggable=taggable,
                blockers=blockers,
            )
        )
    return specs


def parse_roles(text: str, domain: str) -> list[RoleSpec]:
    specs = []
    for number, fields in _lines(text):
        title, aliases, capabilities, industries = _pad(fields, 4)[:4]
        if not _list(capabilities):
            raise ValueError(f"role line {number}: {title} has no capabilities")
        specs.append(RoleSpec(title, domain, _list(aliases), _list(capabilities), _list(industries)))
    return specs


def parse_companies(text: str) -> list[CompanySpec]:
    specs = []
    for _, fields in _lines(text):
        name, industry, aliases, flags = _pad(fields, 4)[:4]
        specs.append(CompanySpec(name, industry, _list(aliases), _blockers(flags)))
    return specs


def parse_topics(text: str, domain: str) -> list[TopicSpec]:
    specs = []
    for _, fields in _lines(text):
        name, aliases, flags = _pad(fields, 3)[:3]
        specs.append(TopicSpec(name, domain, _list(aliases), _blockers(flags)))
    return specs
