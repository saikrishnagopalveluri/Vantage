"""PLACEHOLDER hiring model. Which industry hires which fields, and the curated role-to-skill lists,
are illustrative and built from general knowledge. The O*NET import supplies sourced occupation and
skill data on top of this."""

# slug -> (display name, group shown in the picker)
DOMAINS: dict[str, tuple[str, str]] = {
    "marketing": ("Marketing", "Business & Finance"),
    "finance": ("Finance & Banking", "Business & Finance"),
    "sales": ("Sales & Business Development", "Business & Finance"),
    "hr": ("Human Resources", "Business & Finance"),
    "consulting": ("Consulting & Strategy", "Business & Finance"),
    "b2b": ("B2B Business", "Business & Finance"),
    "software": ("Software Engineering", "Technology"),
    "data-ai": ("Data & AI", "Technology"),
    "it-security": ("IT, Cloud & Security", "Technology"),
    "product-design": ("Product & Design", "Technology"),
    "digital-transformation": ("Digital Transformation", "Technology"),
    "platform-business": ("Platform Businesses", "Technology"),
    "operations": ("Operations & Supply Chain", "Operations & Industry"),
    "engineering": ("Engineering & Manufacturing", "Operations & Industry"),
    "trades": ("Construction & Skilled Trades", "Operations & Industry"),
    "agriculture": ("Agriculture & Environment", "Operations & Industry"),
    "admin": ("Office & Administration", "Operations & Industry"),
    "healthcare": ("Healthcare & Life Sciences", "Health, Science & Public"),
    "science": ("Science & Research", "Health, Science & Public"),
    "education": ("Education & Training", "Health, Science & Public"),
    "legal": ("Legal & Compliance", "Health, Science & Public"),
    "public-services": ("Public Services & Safety", "Health, Science & Public"),
    "creative-media": ("Creative, Media & Arts", "Creative & Services"),
    "hospitality": ("Hospitality, Food & Travel", "Creative & Services"),
}

# Fields with hand-written roles, skills and topics. The others get roles from the O*NET import.
CURATED_DOMAINS = (
    "marketing", "finance", "sales", "hr", "consulting", "b2b", "software", "data-ai",
    "it-security", "product-design", "digital-transformation", "platform-business", "operations",
)

# key -> (name, aliases)
INDUSTRIES: dict[str, tuple[str, list[str]]] = {
    "fmcg": ("FMCG", ["fast-moving consumer goods", "consumer goods", "CPG"]),
    "ecom": ("E-commerce", ["ecommerce", "online retail", "quick commerce"]),
    "saas": ("Software & SaaS", ["SaaS", "software industry", "software-as-a-service"]),
    "itservices": ("IT Services", ["IT services", "IT outsourcing", "IT sector"]),
    "banking": ("Banking", ["banking sector", "lenders"]),
    "capmkts": ("Capital Markets", ["investment banking", "capital markets"]),
    "assetmgmt": ("Asset Management", ["asset management", "mutual funds", "wealth management"]),
    "insurance": ("Insurance", ["insurers", "insurance sector"]),
    "fintech": ("Fintech", ["fintech", "financial technology"]),
    "consulting": ("Consulting", ["management consulting", "consulting firms"]),
    "mfg": ("Manufacturing", ["manufacturing sector", "factory output"]),
    "auto": ("Automotive", ["automobile industry", "auto industry", "automakers", "carmakers"]),
    "logistics": ("Logistics", ["logistics sector", "freight industry", "shipping industry"]),
    "pharma": ("Pharma & Biotech", ["pharmaceutical", "pharma sector", "biotech sector", "drugmakers"]),
    "healthcare": ("Healthcare Services", ["hospital chains", "healthcare providers", "healthcare services"]),
    "retail": ("Retail", ["retailers", "retail sector", "brick-and-mortar"]),
    "telecom": ("Telecom", ["telecommunications", "telecom sector", "telcos"]),
    "energy": ("Energy", ["energy sector", "oil and gas", "renewable energy"]),
    "utilities": ("Utilities", ["power utilities", "utility companies", "electricity distributors"]),
    "semis": ("Semiconductors", ["semiconductor", "chipmakers", "chip makers"]),
    "media": ("Media & Advertising", ["advertising industry", "adtech", "ad agencies"]),
    "realestate": ("Real Estate", ["real estate sector", "property developers", "realty"]),
    "hospitality": ("Hospitality & Travel", ["hotel industry", "hospitality sector", "travel industry"]),
    "education": ("Education", ["education sector", "edtech firms", "universities"]),
    "agriculture": ("Agriculture & Food Production", ["agribusiness", "agriculture sector", "farm sector"]),
    "materials": ("Chemicals & Materials", ["chemicals sector", "cement makers", "materials industry"]),
    "construction": ("Construction & Engineering", ["construction sector", "infrastructure firms", "engineering and construction"]),
    "mining": ("Mining & Metals", ["mining sector", "metals industry", "steelmakers"]),
    "aerospace": ("Aerospace & Defense", ["aerospace industry", "defence sector", "defense contractors"]),
    "transport": ("Transportation & Airlines", ["airline industry", "airlines", "rail operators"]),
    "holding": ("Investment Holdings", ["holding companies", "blank-check companies"]),
}

_BUSINESS = ("marketing", "sales", "finance", "hr", "operations", "admin", "data-ai", "software", "it-security", "consulting")


def _fields(*extra: str, base: tuple[str, ...] = _BUSINESS) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*base, *extra)))


# Which fields of work a company in each industry hires for. Placeholder, but broad on purpose.
INDUSTRY_DOMAINS: dict[str, tuple[str, ...]] = {
    "fmcg": _fields("product-design", "b2b", "digital-transformation", "agriculture", "creative-media", "legal"),
    "ecom": _fields("product-design", "platform-business", "digital-transformation", "b2b", "creative-media", "legal"),
    "saas": _fields("product-design", "platform-business", "digital-transformation", "b2b", "creative-media", "legal", "education"),
    "itservices": _fields("product-design", "digital-transformation", "b2b", "legal", "education"),
    "banking": _fields("product-design", "digital-transformation", "b2b", "legal", "creative-media"),
    "capmkts": _fields("digital-transformation", "b2b", "legal"),
    "assetmgmt": _fields("digital-transformation", "legal"),
    "insurance": _fields("product-design", "digital-transformation", "legal", "healthcare"),
    "fintech": _fields("product-design", "platform-business", "digital-transformation", "b2b", "legal"),
    "consulting": _fields("digital-transformation", "b2b", "legal", "product-design", "education", "science"),
    "mfg": _fields("engineering", "trades", "digital-transformation", "b2b", "product-design", "science", "legal"),
    "auto": _fields("engineering", "trades", "digital-transformation", "b2b", "product-design", "science", "creative-media"),
    "logistics": _fields("digital-transformation", "b2b", "platform-business", "trades", "engineering"),
    "pharma": _fields("healthcare", "science", "engineering", "digital-transformation", "b2b", "legal"),
    "healthcare": _fields("healthcare", "science", "education", "digital-transformation", "public-services", "legal"),
    "retail": _fields("product-design", "digital-transformation", "creative-media", "hospitality", "legal", "trades"),
    "telecom": _fields("engineering", "product-design", "platform-business", "digital-transformation", "b2b", "legal"),
    "energy": _fields("engineering", "trades", "science", "digital-transformation", "b2b", "legal", "agriculture"),
    "utilities": _fields("engineering", "trades", "science", "digital-transformation", "public-services", "legal"),
    "semis": _fields("engineering", "science", "product-design", "b2b", "digital-transformation"),
    "media": _fields("creative-media", "product-design", "platform-business", "digital-transformation", "legal", "b2b"),
    "realestate": _fields("trades", "engineering", "hospitality", "legal", "digital-transformation"),
    "hospitality": _fields("hospitality", "platform-business", "digital-transformation", "creative-media", "trades"),
    "education": _fields("education", "science", "creative-media", "digital-transformation", "public-services"),
    "agriculture": _fields("agriculture", "science", "engineering", "trades", "b2b", "digital-transformation"),
    "materials": _fields("engineering", "science", "trades", "b2b", "digital-transformation", "agriculture"),
    "construction": _fields("engineering", "trades", "legal", "digital-transformation", "b2b"),
    "mining": _fields("engineering", "trades", "science", "b2b", "legal", "agriculture"),
    "aerospace": _fields("engineering", "science", "trades", "public-services", "b2b", "legal"),
    "transport": _fields("hospitality", "trades", "engineering", "platform-business", "public-services", "digital-transformation"),
    "holding": ("finance", "legal", "admin", "consulting"),
}

# Skills and tools shared across domains.
GENERAL_CAPABILITIES = """
Excel | T | Microsoft Excel | avoid:Surf Excel
PowerPoint | T | Microsoft PowerPoint
Google Sheets | T
SQL | T
Python | T | | avoid:snake; avoid:reptile; avoid:python rescued
Power BI | T | PowerBI
Tableau | T
Looker | T | Looker Studio
Jira | T
Microsoft Project | T | MS Project
Agile | S | Scrum; agile methodology
A/B Testing | S | AB testing; split testing; A/B test
CRM | S | customer relationship management
Pricing Strategy | S | revenue growth management
Change Management | S | organizational change management
OKRs | S | objectives and key results
PMP | S | Project Management Professional
~Communication | S
~Presentation Skills | S
~Stakeholder Management | S
~Negotiation | S
~Leadership | S
~Problem Solving | S
~Project Management | S
~Data Visualization | S
~Business Analysis | S
~Statistics | S
~Analytical Thinking | S
~Team Management | S
~Process Improvement | S
~Documentation | S
~Troubleshooting | S
"""
