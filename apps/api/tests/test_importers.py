import zipfile

from app.importers import companies, onet
from app.importers.industry import industry_key
from app.models import (
    Capability,
    CapabilityKind,
    Company,
    Domain,
    Industry,
    Role,
    RoleCapability,
)
from app.tagging import build_index, tag_text


def _tsv(rows: list[list[str]]) -> str:
    return "\n".join("\t".join(r) for r in rows) + "\n"


def make_onet_zip(path):
    files = {
        "Occupation Data.txt": [
            ["O*NET-SOC Code", "Title", "Description"],
            ["11-2021.00", "Marketing Managers", "Plan marketing programs."],
            ["11-1011.00", "Chief Executives", "Direct organizations."],
            ["41-9011.00", "Demonstrators and Product Promoters", "Demonstrate products."],
        ],
        "Job Titles.txt": [
            ["O*NET-SOC Code", "Job Title", "Short Title", "Source(s)"],
            ["11-1011.00", "Agency Owner", "n/a", "10"],
            ["11-1011.00", "agency owner", "n/a", "10"],
            ["11-1011.00", "Chief Executive Officer", "n/a", "10"],
            ["11-2021.00", "Marketing Director", "n/a", "08"],
            ["41-9011.00", "Brand Ambassador", "n/a", "08"],
        ],
        "Sample of Reported Titles.txt": [
            ["O*NET-SOC Code", "Reported Job Title", "Shown in My Next Move"],
            ["11-1011.00", "CEO", "Y"],
            ["11-1011.00", "Agency Owner", "N"],
        ],
        "Software Skills.txt": [
            ["O*NET-SOC Code", "Workplace Example", "Element ID", "Element Name", "Hot Technology", "In Demand"],
            ["11-1011.00", "Atlassian JIRA", "2.E.5.a", "Content workflow", "Y", "N"],
            ["11-1011.00", "Adobe Acrobat", "2.E.5.b", "Document management", "N", "N"],
            ["11-2021.00", "Atlassian JIRA", "2.E.5.a", "Content workflow", "Y", "N"],
        ],
        "Essential Skills.txt": [
            ["O*NET-SOC Code", "Element ID", "Element Name", "Scale ID", "Data Value", "N", "SE", "L", "U", "R", "NR", "D", "S"],
            ["11-1011.00", "2.A.1.a", "Reading Comprehension", "IM", "4.12", "8", "0", "0", "0", "N", "n/a", "x", "x"],
            ["11-1011.00", "2.A.1.a", "Reading Comprehension", "LV", "4.62", "8", "0", "0", "0", "N", "N", "x", "x"],
            ["11-1011.00", "2.A.1.b", "Active Listening", "IM", "4.00", "8", "0", "0", "0", "N", "n/a", "x", "x"],
        ],
    }
    with zipfile.ZipFile(path, "w") as zf:
        for name, rows in files.items():
            zf.writestr(f"db_31_0_text/{name}", _tsv(rows))
    return path


def seed_domains(db):
    db.add_all([Domain(name=n, slug=s) for n, s in [("Marketing", "marketing"), ("Operations", "operations"), ("Sales", "sales")]])
    db.commit()


def test_onet_import_builds_roles_variants_and_skills(db, tmp_path):
    seed_domains(db)
    curated = Role(title="Marketing Manager", taggable=True, source="curated")
    db.add(curated)
    db.commit()

    stats = onet.import_onet(db, make_onet_zip(tmp_path / "onet.zip"))

    assert stats["occupations"] == 2 and stats["linked_to_curated"] == 1
    db.refresh(curated)
    assert curated.onet_code == "11-2021.00" and curated.description == "Plan marketing programs."
    ceo = db.query(Role).filter_by(title="Chief Executives").one()
    assert ceo.source == "onet" and ceo.taggable is False and ceo.domain.slug == "operations"
    promoter = db.query(Role).filter_by(title="Demonstrators and Product Promoters").one()
    assert promoter.domain.slug == "sales"

    variants = {r.title: r for r in db.query(Role).filter(Role.parent_id.is_not(None))}
    assert set(variants) == {"Agency Owner", "Chief Executive Officer", "CEO", "Brand Ambassador", "Marketing Director"}
    assert variants["CEO"].parent_id == ceo.id and variants["CEO"].domain_id == ceo.domain_id
    assert variants["Marketing Director"].parent_id == curated.id  # variants of a curated role hang off it


def test_onet_skills_live_on_imported_roles_only_and_never_tag_news(db, tmp_path):
    seed_domains(db)
    db.add(Role(title="Marketing Manager", taggable=True))
    db.commit()
    onet.import_onet(db, make_onet_zip(tmp_path / "onet.zip"))

    ceo = db.query(Role).filter_by(title="Chief Executives").one()
    names = {c.name: c for c in db.query(Capability).join(RoleCapability).filter(RoleCapability.role_id == ceo.id)}
    assert set(names) == {"Atlassian JIRA", "Adobe Acrobat", "Reading Comprehension", "Active Listening"}
    assert names["Atlassian JIRA"].kind == CapabilityKind.TOOL and names["Reading Comprehension"].kind == CapabilityKind.SKILL
    assert all(c.taggable is False and c.source == "onet" for c in names.values())
    assert db.query(Capability).filter_by(name="Atlassian JIRA").count() == 1  # shared, not doubled
    curated = db.query(Role).filter_by(title="Marketing Manager").one()
    assert db.query(RoleCapability).filter_by(role_id=curated.id).count() == 0

    index = build_index(db)
    assert tag_text(index, "Chief Executives reading comprehension Atlassian JIRA CEO") == set()
    assert tag_text(index, "A new Marketing Manager joins") != set()


def test_onet_import_is_idempotent(db, tmp_path):
    seed_domains(db)
    path = make_onet_zip(tmp_path / "onet.zip")
    onet.import_onet(db, path)
    counts = (db.query(Role).count(), db.query(Capability).count(), db.query(RoleCapability).count())
    again = onet.import_onet(db, path)
    assert (db.query(Role).count(), db.query(Capability).count(), db.query(RoleCapability).count()) == counts
    assert again["occupations"] == again["variants"] == again["role_skills"] == 0


def test_soc_codes_map_to_fields():
    assert onet.domain_for("11-2021.00") == "marketing"
    assert onet.domain_for("13-2011.00") == "finance"
    assert onet.domain_for("15-2051.00") == "data-ai"
    assert onet.domain_for("29-1141.00") == "healthcare"
    assert onet.domain_for("99-9999.00") == "operations"


def test_industry_from_free_text():
    assert industry_key("Services-Prepackaged Software") == "saas"
    assert industry_key("State Commercial Banks") == "banking"
    assert industry_key("Pharmaceutical Preparations") == "pharma"
    assert industry_key("Crude Petroleum & Natural Gas") == "energy"
    assert industry_key(None, "Tata Motors Limited") == "auto"
    assert industry_key("Something unclassifiable") is None


def test_company_names_are_cleaned_and_judged_for_tagging():
    assert companies.pretty("MICROSOFT CORP") == "Microsoft Corp"
    assert companies.pretty("IBM CORP") == "IBM Corp"
    assert companies.pretty("Reliance Industries Limited") == "Reliance Industries Limited"
    assert companies.is_distinctive("Zomato Technologies") is False  # 'technologies' is generic
    assert companies.is_distinctive("Quillon Harbor Works") is True
    assert companies.is_distinctive("Apple Inc") is False  # a single word is too ambiguous
    assert companies.is_distinctive("First National Bank") is False


def test_sec_and_nse_records_parse_and_dedupe_by_cik():
    tickers = [
        {"cik": 1, "name": "ACME WIDGETS INC", "ticker": "ACME", "exchange": "Nasdaq"},
        {"cik": 1, "name": "ACME WIDGETS INC", "ticker": "ACMEP", "exchange": "Nasdaq"},
        {"cik": 2, "name": "BETA BANCORP", "ticker": "BETA", "exchange": "NYSE"},
    ]
    sic = {2: {"cik": 2, "sic": "6022", "desc": "State Commercial Banks"}}
    recs = companies.sec_records(tickers, sic)
    assert [r.name for r in recs] == ["Acme Widgets Inc", "Beta Bancorp"]
    assert recs[1].industry == "banking" and recs[1].external_id == "cik:2"
    nse = companies.nse_records(
        "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"
        "SUNPHARMA,Sun Pharmaceutical Industries Limited,EQ,01-JAN-1994,1,1,INE044A01036,1\n"
    )
    assert nse[0].ticker == "SUNPHARMA" and nse[0].country == "IN" and nse[0].industry == "pharma"
    assert nse[0].external_id == "INE044A01036"


def test_company_insert_skips_curated_duplicates_and_sets_industry(db):
    pharma = Industry(name="Pharma & Biotech", aliases=[])
    db.add(pharma)
    db.add(Company(name="Infosys", taggable=True))
    db.commit()
    recs = [
        companies.Record("Infosys Limited", "nse", "INFY", "IN"),
        companies.Record("Zenith Pharma Labs Pvt", "wikidata", None, "IN", "pharma"),
        companies.Record("Zenith Pharma Labs Pvt.", "wikidata", None, "IN", "pharma"),
        companies.Record("Quillon Harbor Freight Works", "sec", "QHFW", "US", None),
    ]
    stats = companies.insert_companies(db, recs)
    assert stats["added"] == 2 and stats["duplicates"] == 2 and stats["with_industry"] == 1
    zenith = db.query(Company).filter_by(name="Zenith Pharma Labs Pvt").one()
    assert zenith.industry_id == pharma.id and zenith.source == "wikidata" and zenith.taggable is False
    assert db.query(Company).filter_by(name="Quillon Harbor Freight Works").one().taggable is True
    assert db.query(Company).filter_by(name="Infosys").one().source == "curated"

