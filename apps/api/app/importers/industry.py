"""Map free-text industry labels (SEC SIC descriptions, Wikidata industries, company names) to our
30 industries. Ordered rules, first match wins. No match means the company has no industry, which
is fine: it can still be picked, it just does not get derived hiring."""

import re

# Keywords match at the start of a word ("bank" matches "Banks"). Short ones also have to end the
# word, so "gas" does not match "Las Vegas" and "bus" does not match "business".
_WHOLE_WORD = {"bus", "oil", "gas", "chip", "toy", "seed", "space", "ores", "lng", "reit", "wind", "tool", "iron", "coal"}

_RULES: list[tuple[str, str]] = [
    ("fintech", "payment|fintech|financial technology|credit bureau|digital bank|neobank"),
    ("insurance", "insurance|insurer|reinsur|assurance|title guaranty|surety"),
    ("capmkts", "security brokers|brokerage|investment bank|commodity contracts|stock exchange|securities|capital markets|underwriter"),
    ("assetmgmt", "asset management|investment advice|fund|trust|wealth|private equity|venture capital|reit"),
    ("banking", "bank|savings institution|credit union|lending|mortgage|finance company|credit institution|loan|nbfc|housing finance|personal credit|short-term business credit"),
    ("holding", "blank check|holding compan|shell compan|investment compan|special purpose|acquisition corp"),
    ("realestate", "real estate|realty|property|land subdivid|developers|homebuild|housing"),
    ("pharma", "pharma|biolog|biotech|drug|medicinal|therapeut|vaccine|diagnostic substances|life sciences|generic medicine"),
    ("healthcare", "hospital|health service|medical|dental|nursing|clinic|home health|healthcare|surgical|diagnostic lab|ambulatory|managed care|health care"),
    ("semis", "semiconductor|integrated circuit|electronic component|chip|microelectron"),
    ("telecom", "telecom|telephone|radiotelephone|wireless|cable|satellite communication|communications services|broadband"),
    ("saas", "prepackaged software|software|internet|cloud|data processing|information retrieval|application"),
    ("itservices", "computer programming|computer integrated|computer services|it services|information technology|outsourc|data center|computer facilities"),
    ("consulting", "management consulting|business services|consult|advisory|engineering services|management services|staffing|employment agenc|help supply"),
    ("media", "advertis|publish|broadcast|television|radio|motion picture|entertainment|media|newspaper|film|music|video|games|gaming"),
    ("ecom", "catalog & mail-order|e-commerce|online retail|marketplace|internet retail|electronic shopping"),
    ("retail", "retail|stores|supermarket|grocery|wholesale|department store|eating places|drug stores|shops|dealers"),
    ("hospitality", "hotel|motel|lodging|resort|casino|travel|tourism|leisure|restaurant|eating|cruise|amusement|recreation|food service"),
    ("education", "education|school|university|college|training|edtech|learning"),
    ("agriculture", "agricultur|farm|crop|livestock|food|beverage|dairy|meat|grain|fishing|seed|fertiliz|sugar|tobacco|bottled|canned|bakery|confection"),
    ("fmcg", "consumer goods|household|personal care|cosmetic|soap|detergent|toiletr|perfume|consumer products|apparel|footwear|textile|garment|jewel|toy|furniture"),
    ("aerospace", "aerospace|aircraft|defense|defence|missile|space|ordnance|shipbuilding|military"),
    ("transport", "airline|air transportation|railroad|rail transport|trucking|bus|water transportation|shipping line|transportation services|air courier|aviation|airport"),
    ("logistics", "logistic|freight|courier|warehous|delivery|supply chain|forwarding|cargo|pipeline"),
    ("auto", "motors|motor vehicle|automobile|automotive|auto parts|car manufactur|vehicle|truck|tires|two-wheeler|motorcycle"),
    ("utilities", "electric services|electric utilit|gas distribution|water supply|utility|utilities|power generation|natural gas distribution|sanitary services|waste|cogeneration|power transmission"),
    ("energy", "petroleum|oil|gas|coal|energy|solar|wind|renewable|refining|crude|drilling|fuel|uranium|lng|hydrogen|biofuel"),
    ("mining", "mining|metal|steel|iron|aluminum|copper|gold|silver|zinc|ores|quarry|smelting|nonferrous"),
    ("materials", "chemical|cement|plastic|paper|glass|rubber|paint|coating|packaging|materials|fibre|fiber|lumber|wood|ceramic|industrial gases"),
    ("construction", "construction|contractor|infrastructure|civil engineering|building|engineering|electrical work|plumbing|dredging"),
    ("mfg", "machinery|equipment|manufactur|industrial|instruments|electrical|appliance|fabricated|engine|pump|tool|hardware|electronic|controls|valve|components|precision|devices"),
]


def _compile(words: str) -> re.Pattern[str]:
    parts = [rf"\b{re.escape(w)}" + (r"\b" if w in _WHOLE_WORD else "") for w in words.split("|")]
    return re.compile("|".join(parts), re.IGNORECASE)


_COMPILED = [(key, _compile(words)) for key, words in _RULES]


def industry_key(*labels: str | None) -> str | None:
    for label in labels:
        if not label:
            continue
        for key, pattern in _COMPILED:
            if pattern.search(label):
                return key
    return None
