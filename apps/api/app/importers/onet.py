"""Import O*NET occupations, reported job titles, tools and skills as roles and capabilities.

O*NET 31.0 (U.S. Department of Labor, CC BY 4.0). Each occupation becomes a canonical role and
every reported job title becomes a variant that points at it. Skills live on the canonical role,
and imported names never tag news (`taggable=False`), so curated matching stays precise.
"""

import csv
import io
import uuid
import zipfile
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.common import RAW_DIR, download, norm_title
from app.models import Capability, CapabilityKind, Domain, Role, RoleCapability

ONET_URL = "https://www.onetcenter.org/dl_files/database/db_31_0_text.zip"
ONET_ZIP = RAW_DIR / "onet.zip"
ATTRIBUTION = (
    'This product includes information from the O*NET 31.0 Database by the U.S. Department of '
    'Labor, Employment and Training Administration (USDOL/ETA), used under the CC BY 4.0 license.'
)
TOOLS_PER_ROLE = 12
SKILLS_PER_ROLE = 8

# Longest matching prefix of the SOC code decides the field.
SOC_DOMAIN = {
    "11": "operations", "11-2011": "marketing", "11-2021": "marketing", "11-2022": "sales",
    "11-2032": "marketing", "11-2033": "marketing", "11-3031": "finance", "11-3121": "hr",
    "11-3111": "hr", "11-3131": "hr", "11-3021": "software", "11-9111": "healthcare",
    "11-9033": "education", "11-9032": "education", "11-9013": "agriculture",
    "11-9021": "trades", "11-9041": "engineering", "11-9121": "science", "11-1": "operations",
    "13": "operations", "13-1161": "marketing", "13-1071": "hr", "13-1075": "hr",
    "13-1111": "consulting", "13-1151": "hr", "13-2": "finance", "13-1031": "finance",
    "15": "software", "15-2": "data-ai", "15-1212": "it-security", "15-1244": "it-security",
    "15-1241": "it-security", "15-1232": "it-security", "15-1255": "product-design",
    "17": "engineering", "19": "science", "19-3051": "public-services", "19-3011": "science",
    "21": "public-services", "23": "legal", "25": "education", "27": "creative-media",
    "27-1024": "product-design", "27-1021": "product-design", "27-1029": "product-design",
    "27-3031": "marketing", "27-3011": "creative-media", "29": "healthcare", "31": "healthcare",
    "33": "public-services", "35": "hospitality", "37": "trades", "39": "hospitality",
    "39-9032": "public-services", "41": "sales", "41-3011": "marketing", "43": "admin",
    "45": "agriculture", "47": "trades", "49": "trades", "49-2": "it-security",
    "51": "operations", "53": "operations", "55": "public-services",
}


def domain_for(soc: str) -> str:
    for size in range(len(soc), 1, -1):
        slug = SOC_DOMAIN.get(soc[:size])
        if slug:
            return slug
    return "operations"


def ensure_onet(path: Path = ONET_ZIP) -> Path:
    return download(ONET_URL, path)


def _table(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    member = next(n for n in zf.namelist() if n.endswith("/" + name) or n == name)
    with zf.open(member) as raw:
        return list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t"))


def _uid() -> str:
    return str(uuid.uuid4())


def import_onet(db: Session, zip_path: Path = ONET_ZIP) -> dict[str, int]:
    zf = zipfile.ZipFile(zip_path)
    occupations = _table(zf, "Occupation Data.txt")
    job_titles = _table(zf, "Job Titles.txt")
    reported = _table(zf, "Sample of Reported Titles.txt")
    software = _table(zf, "Software Skills.txt")
    essential = [r for r in _table(zf, "Essential Skills.txt") if r["Scale ID"] == "IM"]

    domains = {d.slug: d.id for d in db.scalars(select(Domain))}
    existing = list(db.scalars(select(Role)))
    by_norm: dict[str, Role] = {}
    for role in existing:
        by_norm[norm_title(role.title)] = role
        for alias in role.aliases or []:
            by_norm.setdefault(norm_title(alias), role)
    by_code = {r.onet_code: r for r in existing if r.onet_code and r.parent_id is None}

    stats = {"occupations": 0, "linked_to_curated": 0, "variants": 0, "tools": 0, "skills": 0, "role_skills": 0}
    canonical: dict[str, Role] = {}
    new_roles: list[dict] = []

    for row in occupations:
        code, title, description = row["O*NET-SOC Code"], row["Title"].strip(), row["Description"].strip()
        role = by_code.get(code) or by_norm.get(norm_title(title))
        if role is not None and role.parent is not None:
            role = role.parent
        if role is not None:
            if role.onet_code is None and role.source == "curated":
                role.onet_code = code
                stats["linked_to_curated"] += 1
            if not role.description:
                role.description = description
            canonical[code] = role
            by_code.setdefault(code, role)
            continue
        role = Role(
            id=_uid(), title=title, domain_id=domains[domain_for(code)], taggable=False,
            source="onet", onet_code=code, description=description,
        )
        new_roles.append(role)
        canonical[code] = role
        by_norm[norm_title(title)] = role
        stats["occupations"] += 1
    db.add_all(new_roles)
    db.flush()

    variants: list[dict] = []
    for row in [*job_titles, *(dict(r, **{"Job Title": r["Reported Job Title"]}) for r in reported)]:
        title = (row.get("Job Title") or "").strip()
        parent = canonical.get(row["O*NET-SOC Code"])
        key = norm_title(title)
        if not title or parent is None or key in by_norm:
            continue
        by_norm[key] = parent  # placeholder so later duplicates are skipped
        variants.append(
            {
                "id": _uid(), "title": title, "aliases": [], "blockers": [], "domain_id": parent.domain_id,
                "parent_id": parent.id, "taggable": False, "source": "onet",
                "onet_code": parent.onet_code or row["O*NET-SOC Code"],
            }
        )
    existing_titles = {r.title for r in existing} | {r.title for r in new_roles}
    variants = [v for v in variants if v["title"] not in existing_titles]
    seen: set[str] = set()
    unique = []
    for v in variants:
        if v["title"] in seen:
            continue
        seen.add(v["title"])
        unique.append(v)
    for start in range(0, len(unique), 5000):
        db.execute(Role.__table__.insert(), unique[start : start + 5000])
    stats["variants"] = len(unique)

    # Capabilities: shared skills and tools, matched to curated ones by name so nothing is doubled.
    caps: dict[tuple[str, CapabilityKind], str] = {}
    for cap in db.scalars(select(Capability)):
        caps[(cap.name.lower(), cap.kind)] = cap.id
        for alias in cap.aliases or []:
            caps.setdefault((alias.lower(), cap.kind), cap.id)
    new_caps: list[dict] = []

    def capability(name: str, kind: CapabilityKind) -> str:
        key = (name.lower(), kind)
        if key not in caps:
            caps[key] = _uid()
            new_caps.append(
                {
                    "id": caps[key], "name": name, "kind": kind, "aliases": [], "blockers": [],
                    "taggable": False, "source": "onet", "domain_id": None,
                }
            )
            stats["tools" if kind == CapabilityKind.TOOL else "skills"] += 1
        return caps[key]

    existing_links = {(l.role_id, l.capability_id) for l in db.scalars(select(RoleCapability))}
    links: dict[tuple[str, str], None] = {}

    def link(code: str, capability_id: str) -> None:
        role = canonical.get(code)
        if role is not None and role.source == "onet" and (role.id, capability_id) not in existing_links:
            links[(role.id, capability_id)] = None

    tools_by_code: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in software:
        rank = (row["Hot Technology"] != "Y") * 2 + (row["In Demand"] != "Y")
        tools_by_code[row["O*NET-SOC Code"]].append((rank, row["Workplace Example"].strip()))
    for code, tools in tools_by_code.items():
        chosen: list[str] = []
        for _, name in sorted(tools):
            if name and name not in chosen:
                chosen.append(name)
            if len(chosen) == TOOLS_PER_ROLE:
                break
        for name in chosen:
            link(code, capability(name, CapabilityKind.TOOL))

    skills_by_code: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for row in essential:
        skills_by_code[row["O*NET-SOC Code"]].append((-float(row["Data Value"]), row["Element Name"].strip()))
    for code, skills in skills_by_code.items():
        for _, name in sorted(skills)[:SKILLS_PER_ROLE]:
            link(code, capability(name, CapabilityKind.SKILL))

    if new_caps:
        db.execute(Capability.__table__.insert(), new_caps)
    if links:
        rows = [{"role_id": r, "capability_id": c} for r, c in links]
        for start in range(0, len(rows), 5000):
            db.execute(RoleCapability.__table__.insert(), rows[start : start + 5000])
    stats["role_skills"] = len(links)
    db.commit()
    return stats
