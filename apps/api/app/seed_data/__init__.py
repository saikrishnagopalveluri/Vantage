"""Loads and validates the hand-curated taxonomy. Validation is deliberately strict: a dangling
capability reference, an unknown industry key or two entities sharing an alias is an error,
because each of those silently degrades matching accuracy."""

from collections import defaultdict

from . import (
    b2b,
    companies,
    consulting,
    data_ai,
    digital_transformation,
    finance,
    hr,
    it_security,
    marketing,
    mba,
    operations,
    platform_business,
    product_design,
    sales,
    software,
)
from .mba import MBA_COMPANIES, MBA_ROLES, MBA_SKILLS
from .common import CURATED_DOMAINS, DOMAINS, GENERAL_CAPABILITIES, INDUSTRIES, INDUSTRY_DOMAINS
from .other_fields import TOPICS_BY_DOMAIN
from .samples import SAMPLE_ARTICLES
from .sources import SAMPLE_SOURCE, SOURCES
from .spec import (
    Taxonomy,
    parse_capabilities,
    parse_companies,
    parse_roles,
    parse_topics,
)

DOMAIN_MODULES = (
    marketing, finance, software, data_ai, it_security, operations, hr, sales, product_design,
    consulting, digital_transformation, platform_business, b2b,
)

# (company, role) -> capabilities that replace the role-level list for that pair. Illustrative.
COMPANY_ROLE_CAPABILITIES: dict[tuple[str, str], list[str]] = {
    ("Hindustan Unilever", "Brand Manager"): ["Consumer Insights", "Brand Strategy", "Media Planning", "Campaign ROI Analysis", "Excel", "Power BI"],
    ("Nestle India", "Brand Manager"): ["Consumer Insights", "Brand Strategy", "Campaign ROI Analysis", "Excel", "Power BI"],
    ("Procter & Gamble", "Brand Manager"): ["Consumer Insights", "Brand Strategy", "Media Planning", "Market Research", "Excel", "Power BI"],
    ("Goldman Sachs", "Investment Banking Analyst"): ["Financial Modeling", "Discounted Cash Flow", "Mergers & Acquisitions", "Excel", "PowerPoint", "Capital IQ"],
    ("Amazon India", "Supply Chain Analyst"): ["Supply Chain Planning", "SQL", "Excel", "Inventory Management", "Demand Forecasting"],
    ("Tata Consultancy Services", "Java Developer"): ["Java", "Spring Boot", "SQL", "Microservices", "Agile"],
    ("Google", "Data Scientist"): ["Python", "Machine Learning", "SQL", "A/B Testing", "Causal Inference", "Statistics"],
    # From the placement tables in the Managing Digital Transformation and Managing Platform Businesses handouts.
    ("Deloitte", "Risk Advisory Analyst, Digital Transformation and Cybersecurity"): ["Digital Strategy", "Regulatory Compliance", "Risk Management", "Cybersecurity", "Threat Analysis", "Data Security", "Digital Framework Evaluation"],
    ("Deloitte", "Finance Transformation Consultant"): ["Organisational Readiness", "Change Management", "KPI Measurement", "Strategic Roadmapping", "Process Optimization", "Financial Modeling", "Digital Strategy"],
    ("Deloitte", "Strategy and Operations Business Analyst"): ["Digital Innovation", "Digital Customer Experience", "KPI Measurement", "Data-Driven Strategy", "Client Engagement", "Process Mapping", "Data Analysis", "Communication", "Strategic Analysis"],
    ("Deloitte", "Cloud Services Technology Analyst"): ["Cloud Computing", "Cloud Architecture", "Process Automation", "System Design", "Internet of Things", "Deployment Strategy", "Industry 4.0", "Change Management"],
    ("Deloitte", "Manufacturing Transformation Specialist"): ["Supply Chain Digitisation", "Smart Manufacturing Operations", "Change Management", "Change Adoption", "Lean Operations", "SCM Tools", "Process Automation", "Data Interpretation", "Internet of Things"],
    ("Accenture", "Delivery and Project Insights Senior Analyst"): ["Network Effects", "Data Analysis", "Regulatory Compliance", "Financial Modeling", "Business Process Design", "Client Relationship Management", "Strategic Problem Solving"],
    ("Accenture", "Supply Chain and Software Senior Analyst"): ["Ecosystem Design", "Supply Chain Analytics", "Agile", "Process Automation", "Cloud Migration", "Business Transformation"],
    ("Accenture", "Business Transformation Team Lead"): ["Platform Governance", "Monetization Models", "Platform Ethics", "Cross-Industry Knowledge", "Change Management", "Digital Strategy", "End-to-End Lifecycle Delivery", "Communication", "Stakeholder Management"],
    ("Accenture", "Retail AI Team Lead"): ["Retail Transformation", "Data Analysis", "Consumer Insights", "Platform Innovation", "Digital Customer Experience"],
}


def load_taxonomy() -> Taxonomy:
    tax = Taxonomy()
    tax.capabilities += parse_capabilities(GENERAL_CAPABILITIES, None)
    for module in DOMAIN_MODULES:
        tax.capabilities += parse_capabilities(module.CAPABILITIES, module.DOMAIN)
        tax.roles += parse_roles(module.ROLES, module.DOMAIN)
        tax.topics += parse_topics(module.TOPICS, module.DOMAIN)
    for domain, text in TOPICS_BY_DOMAIN.items():
        tax.topics += parse_topics(text, domain)
    tax.companies += parse_companies(companies.COMPANIES)
    # Management students come first: their roles, skills, topics and recruiters.
    for domain, text in mba.CAPABILITIES.items():
        tax.capabilities += parse_capabilities(text, None if domain == "GENERAL" else domain)
    for domain, text in mba.ROLES.items():
        tax.roles += parse_roles(text, domain)
    for domain, text in mba.TOPICS.items():
        tax.topics += parse_topics(text, domain)
    tax.companies += parse_companies(mba.COMPANIES)
    problems = validate(tax)
    if problems:
        raise ValueError("Invalid taxonomy:\n  " + "\n  ".join(problems))
    return tax


def validate(tax: Taxonomy) -> list[str]:
    problems: list[str] = []

    def duplicates(kind: str, names: list[str]) -> None:
        seen: set[str] = set()
        for name in names:
            if name.lower() in seen:
                problems.append(f"duplicate {kind}: {name}")
            seen.add(name.lower())

    duplicates("capability", [c.name for c in tax.capabilities])
    duplicates("role", [r.title for r in tax.roles])
    duplicates("company", [c.name for c in tax.companies])
    duplicates("topic", [t.name for t in tax.topics])

    capability_names = {c.name for c in tax.capabilities}
    role_titles = {r.title for r in tax.roles}
    company_names = {c.name for c in tax.companies}
    for role in tax.roles:
        for cap in role.capabilities:
            if cap not in capability_names:
                problems.append(f"role {role.title!r} references unknown capability {cap!r}")
        for key in role.industries:
            if key not in INDUSTRIES:
                problems.append(f"role {role.title!r} references unknown industry {key!r}")
        if role.domain not in DOMAINS:
            problems.append(f"role {role.title!r} is in unknown field {role.domain!r}")
    for kind, wanted, have in (
        ("role", mba.MBA_ROLES, role_titles),
        ("skill", mba.MBA_SKILLS, capability_names),
        ("company", mba.MBA_COMPANIES, company_names),
    ):
        problems += [f"management-student {kind} list names something that does not exist: {name!r}" for name in sorted(wanted - have)]
    for topic in tax.topics:
        if topic.domain not in DOMAINS:
            problems.append(f"topic {topic.name!r} is in unknown field {topic.domain!r}")
    for company in tax.companies:
        if company.industry not in INDUSTRIES:
            problems.append(f"company {company.name!r} has unknown industry {company.industry!r}")
    for (company, role), caps in COMPANY_ROLE_CAPABILITIES.items():
        if company not in company_names or role not in role_titles:
            problems.append(f"override references unknown pair ({company!r}, {role!r})")
        problems += [f"override ({company}, {role}) unknown capability {c!r}" for c in caps if c not in capability_names]
    for industry, domains in INDUSTRY_DOMAINS.items():
        if industry not in INDUSTRIES:
            problems.append(f"hiring rules mention unknown industry {industry!r}")
        problems += [f"industry {industry!r} lists unknown field {d!r}" for d in domains if d not in DOMAINS]

    # An alias claimed by two different entities of the same kind can never be resolved.
    for kind, entities in (
        ("capability", [(c.name, c.aliases) for c in tax.capabilities]),
        ("company", [(c.name, c.aliases) for c in tax.companies]),
        ("role", [(r.title, r.aliases) for r in tax.roles]),
        ("topic", [(t.name, t.aliases) for t in tax.topics]),
    ):
        owners: dict[str, set[str]] = defaultdict(set)
        for name, aliases in entities:
            for term in (name, *aliases):
                owners[term.lower()].add(name)
        for term, names in owners.items():
            if len(names) > 1:
                problems.append(f"{kind} term {term!r} is claimed by {sorted(names)}")
    return problems
