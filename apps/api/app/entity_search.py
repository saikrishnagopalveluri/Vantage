"""Finding a role or company that's missing from the taxonomy: a Google Programmable Search Engine
call (scoped, in the operator's own console, to a handful of reference sites — Wikipedia, LinkedIn,
O*NET, etc.), and a direct fetch of a company's own website when the person gives one. Both are
best-effort: a search failure never blocks adding the entry by hand, it just means no web context
comes along with it.
"""

import html
import os
import re
from dataclasses import dataclass

import httpx

USER_AGENT = "VantageBot/0.1 (+personal research; respects robots.txt)"
SEARCH_TIMEOUT = 8


@dataclass(frozen=True)
class WebResult:
    title: str
    snippet: str
    url: str


def google_search(query: str, num: int = 3) -> list[WebResult]:
    """Empty (never an error) when the API isn't configured, the query fails, or nothing comes back —
    the caller always has a working add-it-anyway path regardless."""
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not engine_id or not query.strip():
        return []
    try:
        response = httpx.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": api_key, "cx": engine_id, "q": query, "num": min(max(num, 1), 10)},
            timeout=SEARCH_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except (httpx.HTTPError, ValueError):
        return []
    return [
        WebResult(title=item.get("title", ""), snippet=item.get("snippet", ""), url=item.get("link", ""))
        for item in items[:num]
        if item.get("link")
    ]


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
# The closing quote must match whichever quote character opened the attribute (a backreference),
# not "either kind" — otherwise an apostrophe inside the text itself ("India's...") gets mistaken
# for the end of a double-quoted value and truncates it.
_DESCRIPTION_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=(["\'])(.*?)\1', re.IGNORECASE)


def fetch_website_meta(url: str) -> WebResult | None:
    """The page's own <title> and meta description, for a company whose site the person gave us
    directly. No HTML parser dependency — just the two tags this needs, tolerantly matched, and only
    the first slice of the response (a page's <head> is always near the top)."""
    address = url if re.match(r"^https?://", url) else f"https://{url}"
    try:
        response = httpx.get(address, timeout=SEARCH_TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    text = response.text[:200_000]
    title_match = _TITLE_RE.search(text)
    description_match = _DESCRIPTION_RE.search(text)
    title = html.unescape(title_match.group(1)).strip() if title_match else address
    description = html.unescape(description_match.group(2)).strip() if description_match else ""
    return WebResult(title=title[:200], snippet=description[:300], url=str(response.url))
