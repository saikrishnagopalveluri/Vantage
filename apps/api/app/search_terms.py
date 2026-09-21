"""Other ways a person might type the same thing: UK and US spellings, hyphens, and the acronyms
management students actually use. A search for "modelling" should find "Financial Modeling", and
"DCF" should find "Discounted Cash Flow". Nothing here changes what is stored, only what is looked up.
"""

import re

MAX_VARIANTS = 8

# (UK, US) pairs, applied in both directions because the catalogue itself mixes them
# ("Organisational Readiness" next to "Organizational Behavior").
_SPELLINGS = [
    ("modelling", "modeling"), ("modelled", "modeled"), ("labelling", "labeling"), ("travelling", "traveling"),
    ("analyse", "analyze"), ("analysing", "analyzing"), ("analyser", "analyzer"),
    ("programme", "program"), ("centre", "center"), ("behaviour", "behavior"), ("colour", "color"),
    ("favour", "favor"), ("labour", "labor"), ("licence", "license"), ("catalogue", "catalog"),
    ("organisation", "organization"), ("organisational", "organizational"), ("optimisation", "optimization"),
    ("optimise", "optimize"), ("specialisation", "specialization"), ("utilisation", "utilization"),
    ("prioritisation", "prioritization"), ("digitisation", "digitization"), ("monetisation", "monetization"),
    ("localisation", "localization"), ("customisation", "customization"), ("standardisation", "standardization"),
    ("capitalisation", "capitalization"), ("recognise", "recognize"), ("minimise", "minimize"),
    ("maximise", "maximize"), ("summarise", "summarize"), ("harmonisation", "harmonization"),
    ("judgement", "judgment"), ("enrol", "enroll"), ("practise", "practice"), ("defence", "defense"),
]

# Acronym or short form -> what the catalogue calls it. Only forms the catalogue lacks are worth
# listing; "KPI" and "SEO" already match on their own.
_ACRONYMS = {
    "dcf": ["discounted cash flow"],
    "npv": ["net present value"],
    "irr": ["internal rate of return"],
    "wacc": ["cost of capital"],
    "ebitda": ["financial analysis"],
    "roi": ["return on investment", "roi analysis"],
    "roas": ["return on ad spend"],
    "gtm": ["go-to-market", "go to market"],
    "fmcg": ["consumer goods", "fast moving consumer goods"],
    "cpg": ["consumer goods", "consumer packaged goods"],
    "pnl": ["p&l"],
    "p and l": ["p&l"],
    "profit and loss": ["p&l"],
    "kpis": ["kpi"],
    "okr": ["okrs", "objectives and key results"],
    "okrs": ["okr"],
    "ux": ["user experience"],
    "ui": ["user interface"],
    "hr": ["human resources"],
    "hrbp": ["human resources business partner"],
    "l&d": ["learning and development"],
    "ld": ["learning and development"],
    "m&a": ["mergers and acquisitions", "mergers & acquisitions"],
    "ib": ["investment banking"],
    "pe": ["private equity"],
    "vc": ["venture capital"],
    "bd": ["business development"],
    "pm": ["product manager", "project manager", "program manager"],
    "apm": ["associate product manager"],
    "sde": ["software development engineer"],
    "scm": ["supply chain"],
    "mis": ["management information systems"],
    "erp": ["enterprise resource planning"],
    "crm": ["customer relationship management"],
    "sem": ["search engine marketing"],
    "smm": ["social media marketing"],
    "cro": ["conversion rate optimization", "conversion rate optimisation"],
    "b2c": ["business to consumer", "direct to consumer"],
    "d2c": ["direct to consumer", "direct-to-consumer"],
    "esg": ["environmental social governance", "sustainability"],
    "csr": ["corporate social responsibility"],
    "fp&a": ["financial planning", "financial planning and analysis"],
    "fpa": ["fp&a", "financial planning"],
    "mba": ["management"],
    "ai": ["artificial intelligence"],
    "ml": ["machine learning"],
    "bi": ["business intelligence"],
    "gst": ["indirect tax"],
    "sql server": ["sql"],
}

# "MS Excel" and "Microsoft Excel" are just "Excel" here.
_VENDOR_PREFIX = re.compile(r"^(ms|microsoft|google|gsuite|g suite)\s+", re.IGNORECASE)


def _swap(text: str, source: str, target: str) -> str:
    return re.sub(re.escape(source), target, text, flags=re.IGNORECASE)


def variants(q: str) -> list[str]:
    """The query itself first, then other spellings and expansions, without duplicates."""
    base = " ".join(q.lower().split())
    if not base:
        return []
    found: list[str] = [base]

    def add(term: str) -> None:
        term = " ".join(term.split())
        if term and term not in found and len(found) < MAX_VARIANTS:
            found.append(term)

    stripped = _VENDOR_PREFIX.sub("", base)
    if stripped != base:
        add(stripped)
    for seed in list(found):
        for uk, us in _SPELLINGS:
            if uk in seed:
                add(_swap(seed, uk, us))
            elif us in seed:
                add(_swap(seed, us, uk))
        if "-" in seed:
            add(seed.replace("-", " "))
            add(seed.replace("-", ""))
        elif " " in seed:
            add(seed.replace(" ", "-"))
    for seed in list(found):
        for expansion in _ACRONYMS.get(seed, []):
            add(expansion)
    return found
