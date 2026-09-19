"""Import listed companies from SEC filings, the NSE equity list and Wikidata.

Curated companies always win: an imported name that matches one (ignoring "Inc", "Ltd" and the
like) is skipped, so nothing is doubled. Most imported names are browse-only. A company tags news
only if its name is distinctive enough that a match in a headline is almost certainly about it.
"""

import csv
import io
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers import sec, wikidata
from app.importers.common import RAW_DIR, download, norm_company
from app.importers.industry import industry_key
from app.models import Company, Industry
from app.seed_data import INDUSTRIES

NSE_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_FILE = RAW_DIR / "nse.csv"

_KEEP_UPPER_MAX = 3
_SHORT_WORDS = {
    "INC", "CORP", "CO", "LTD", "THE", "AND", "OF", "NEW", "FOR", "OLD", "ONE", "OUR", "ALL", "AIR",
    "OIL", "GAS", "BIO", "PRO", "TOP", "BIG", "RED", "SUN", "FIRST", "PLC", "LLC", "USA",
}
# Words that make a name too common to trust in a headline ("First Bank", "Global Energy").
_GENERIC = {
    "bank", "capital", "first", "american", "national", "united", "global", "international", "holdings",
    "group", "energy", "systems", "technologies", "technology", "financial", "partners", "trust", "fund",
    "acquisition", "industries", "enterprises", "resources", "services", "solutions", "pharma", "pharmaceuticals",
    "therapeutics", "biosciences", "bancorp", "bancshares", "properties", "realty", "investment", "investments",
    "ventures", "communications", "networks", "media", "entertainment", "foods", "health", "healthcare",
    "medical", "power", "gold", "mining", "oil", "gas", "petroleum", "steel", "motors", "airlines", "labs",
    "sciences", "digital", "software", "data", "china", "india", "asia", "pacific", "atlantic", "north",
    "south", "east", "west", "new", "general", "universal", "premier", "royal", "central", "alliance",
    "management", "wealth", "finance", "open", "insurance", "life", "markets", "market", "exchange", "commerce",
    "retail", "consumer", "brands", "brand", "business", "corporate", "corporation", "company", "limited",
    "private", "public", "sector", "capital", "credit", "money", "cloud", "cyber", "smart", "green", "blue",
    "red", "black", "white", "star", "sun", "sky", "earth", "world", "life", "time", "point", "link", "edge",
    "prime", "first", "one", "next", "future", "modern", "advanced", "applied", "creative", "dynamic",
}


@dataclass
class Record:
    name: str
    source: str
    ticker: str | None = None
    country: str | None = None
    industry: str | None = None
    external_id: str | None = None


def pretty(name: str) -> str:
    """SEC names arrive in capitals ("MICROSOFT CORP"). Turn them into something readable."""
    name = re.sub(r"\s+", " ", name).strip()
    if not name.isupper():
        return name
    out = []
    for token in name.split(" "):
        if len(token) <= _KEEP_UPPER_MAX and token in _SHORT_WORDS:
            out.append(token.capitalize() if token in {"INC", "CORP", "CO", "LTD", "THE", "AND", "OF", "NEW", "FOR"} else token)
        elif len(token) <= _KEEP_UPPER_MAX and token.isalpha():
            out.append(token)
        else:
            out.append(token.capitalize())
    text = " ".join(out)
    return re.sub(r"\b(Of|And|The|For)\b", lambda m: m.group(1).lower(), text).replace("/de", "").strip()


def is_distinctive(name: str) -> bool:
    words = norm_company(name).split()
    if len(words) < 2 or sum(len(w) for w in words) < 11:
        return False
    return not any(w in _GENERIC for w in words) and not any(w.isdigit() for w in words)


def sec_records(tickers: list[dict], sic: dict[int, dict]) -> list[Record]:
    seen: set[int] = set()
    out = []
    for row in tickers:
        if row["cik"] in seen or not row.get("name"):
            continue
        seen.add(row["cik"])
        info = sic.get(row["cik"], {})
        out.append(
            Record(
                name=pretty(row["name"]), source="sec", ticker=row.get("ticker"), country="US",
                industry=industry_key(info.get("desc"), row["name"]), external_id=f"cik:{row['cik']}",
            )
        )
    return out


def nse_records(text: str) -> list[Record]:
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        name = row.get("NAME OF COMPANY")
        if name:
            out.append(
                Record(
                    name=name, source="nse", ticker=row.get("SYMBOL"), country="IN",
                    industry=industry_key(name), external_id=row.get("ISIN NUMBER") or None,
                )
            )
    return out


def wikidata_records(rows: list[dict]) -> list[Record]:
    return [
        Record(name=r["name"], source="wikidata", country=r.get("country"), industry=industry_key(r.get("industry"), r["name"]))
        for r in rows
        if r.get("name") and not re.fullmatch(r"Q\d+", r["name"])
    ]


def insert_companies(db: Session, records: list[Record]) -> dict[str, int]:
    industries = {i.name: i.id for i in db.scalars(select(Industry))}
    industry_ids = {key: industries[name] for key, (name, _) in INDUSTRIES.items() if name in industries}

    existing = list(db.scalars(select(Company)))
    taken_names = {c.name.lower() for c in existing}
    taken_keys = {norm_company(c.name) for c in existing}
    for company in existing:
        taken_keys.update(norm_company(a) for a in company.aliases or [])

    rows: list[dict] = []
    stats = {"added": 0, "duplicates": 0, "with_industry": 0, "taggable": 0}
    for rec in records:
        key = norm_company(rec.name)
        if len(key) < 2 or key in taken_keys or rec.name.lower() in taken_names:
            stats["duplicates"] += 1
            continue
        taken_keys.add(key)
        taken_names.add(rec.name.lower())
        taggable = is_distinctive(rec.name)
        rows.append(
            {
                "id": str(uuid.uuid4()), "name": rec.name, "aliases": [], "blockers": [],
                "industry_id": industry_ids.get(rec.industry) if rec.industry else None,
                "taggable": taggable, "source": rec.source, "ticker": rec.ticker,
                "country": rec.country, "external_id": rec.external_id,
            }
        )
        stats["added"] += 1
        stats["with_industry"] += rows[-1]["industry_id"] is not None
        stats["taggable"] += taggable
    for start in range(0, len(rows), 5000):
        db.execute(Company.__table__.insert(), rows[start : start + 5000])
    db.commit()
    return stats


def recompute_taggable(db: Session) -> int:
    """Apply the current distinctiveness rule to every imported company. Curated ones are never touched."""
    changed = 0
    for company in db.scalars(select(Company).where(Company.source != "curated")):
        want = is_distinctive(company.name)
        if company.taggable != want:
            company.taggable = want
            changed += 1
    db.commit()
    return changed


def import_companies(db: Session, *, wikidata_rows: list[dict] | None = None) -> dict[str, int]:
    """SEC first (it has real industry codes), then NSE, then Wikidata for everything else."""
    records = sec_records(sec.load_tickers(), sec.load_sic())
    records += nse_records(download(NSE_URL, NSE_FILE, headers={"User-Agent": "Mozilla/5.0"}).read_text(encoding="utf-8"))
    rows = wikidata_rows if wikidata_rows is not None else wikidata.fetch_all()
    records += wikidata_records(rows)
    stats = insert_companies(db, records)
    recompute_taggable(db)
    return stats


def load_cached(path: Path) -> str:
    return path.read_text(encoding="utf-8")
