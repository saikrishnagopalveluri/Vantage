"""What kind of story a headline is, read from the headline alone.

Used to make the "why it matters" and "what to do" lines specific ("this is a leadership change")
instead of generic, and to push down stories that are noise for someone building a career (stock
tips, market-holiday notices). Only the headline is read, so the label never claims more than the
headline says.
"""

import re

# Order matters: the first kind that matches wins, so the specific ones come before the broad ones.
_KINDS: list[tuple[str, re.Pattern[str]]] = [
    (
        "leadership",
        re.compile(
            r"\b(appoints?|appointed|names? [^,;:|]{0,40}\b(as|new)\b|elevates?|elevated|promotes?|promoted|steps? down|stepping down|"
            r"resigns?|resigned|quits?|exits?|exit of|new (ceo|cfo|coo|chro|cmo|cto|head|chief|md|chairman)|"
            r"joins? as|takes? charge|(ceo|cfo|coo|chro|cmo|cto|chief|chairman|md)\b.*\b(steps?|quits?|exits?|resigns?)|"
            r"concludes?\b.*\b(stint|tenure)|(stint|tenure) at|succeeds?|successor|hired as|to lead)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "deal",
        re.compile(
            r"\b(acquires?|acquired|acquisition|merges?|merger|buys|buyout|takeover|takes? over|stake sale|"
            r"raises?\b.*\b(\$|₹|rs\.?|funding|million|billion|crore|series)|funding|fundraising|series [a-e]\b|ipo|"
            r"valuation|invests?|investment of|joint venture|divest\w*|demerger|sells? (its|a) )",
            re.IGNORECASE,
        ),
    ),
    (
        "results",
        re.compile(
            r"\b(q[1-4]\b|q[1-4] ?fy|fy ?\d{2}|results?|earnings|net profit|profit (rises?|falls?|jumps?|dips?|up|down)|"
            r"revenue|sales (rise|fall|grow|jump|drop|up|down)|market share|quarterly|annual report)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "hiring",
        re.compile(
            r"\b(hiring|hires|layoffs?|lays? off|job cuts?|cuts? jobs|recruit\w*|campus|placements?|salary|salaries|"
            r"appraisals?|(salary|pay|wage) hikes?|increments?|headcount|attrition|workforce|talent|internships?|stipend|freshers?|bonus)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "policy",
        re.compile(
            r"\b(rbi|sebi|cci|fssai|trai|irdai|gst|budget|tariffs?|regulat\w+|policy|policies|ban(s|ned)?|"
            r"rate (cut|hike)|repo rate|inflation|subsid\w+|government|ministry|supreme court|high court|"
            r"compliance|probe|penalty|fined?|legal action|notice)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "launch",
        re.compile(
            r"\b(launch\w*|unveils?|rolls? out|introduces?|debuts?|new (product|range|brand|variant|app|service|campaign)|"
            r"campaign|rebrand\w*|ad film|sponsors?|partners? with|tie-?up|collaborat\w+|alliance)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "expansion",
        re.compile(
            r"\b(expands?|expansion|opens?|plans? to open|sets? up|new (plant|factory|office|store|centre|center|hub)|"
            r"enters?|entry into|invests? in (india|a new)|capacity)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tech",
        re.compile(
            r"\b(ai|a\.i\.|generative|genai|llm|automation|cloud|cyber\w*|data centre|data center|platform|"
            r"digital|software|analytics|saas|chatbot|machine learning)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "markets",
        re.compile(
            r"\b(stocks?|shares?|sensex|nifty|target price|price target|buy rating|sell rating|upside|downside|"
            r"brokerages?|bullish|bearish|rally|plunges?|surges?|gains?|dividend)\b",
            re.IGNORECASE,
        ),
    ),
]

# Stock tips and holiday notices say very little about a career, however often a company is named.
_LOW_VALUE = re.compile(
    r"\b(stocks? to (buy|watch|sell)|stock picks?|top stocks?|buy or sell|shares? to buy|multibagger|"
    r"(bank|market|stock exchange)s? holiday|open or closed today|closed today|horoscope|live updates?|"
    r"share price today|gold rate|petrol price|sensex today|nifty today|today'?s? (stock|market))\b",
    re.IGNORECASE,
)


def story_kind(title: str) -> str | None:
    """One of leadership, deal, results, hiring, policy, launch, expansion, tech, markets, or None."""
    for kind, pattern in _KINDS:
        if pattern.search(title):
            return kind
    return None


def is_low_value(title: str) -> bool:
    return bool(_LOW_VALUE.search(title))
