"""Companies listed on a stock exchange, with their industry, from Wikidata (CC0).

Queried one country at a time so no request is large, cached per country in data/raw/wikidata,
and skipped on re-runs. Wikidata rate-limits, so we pause between countries.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from app.importers.common import RAW_DIR, USER_AGENT

ENDPOINT = "https://query.wikidata.org/sparql"
CACHE_DIR = RAW_DIR / "wikidata"

# Wikidata country ids: markets where the audience is likely to look for employers.
COUNTRIES = {
    "US": "Q30", "IN": "Q668", "GB": "Q145", "DE": "Q183", "FR": "Q142", "JP": "Q17", "CN": "Q148",
    "CA": "Q16", "AU": "Q408", "SG": "Q334", "AE": "Q878", "CH": "Q39", "NL": "Q55", "SE": "Q34",
    "ES": "Q29", "IT": "Q38", "BR": "Q155", "KR": "Q884", "HK": "Q8646", "ZA": "Q258", "IE": "Q27",
    "MY": "Q833", "ID": "Q252", "TH": "Q869", "SA": "Q851", "MX": "Q96", "NO": "Q20", "DK": "Q35",
    "FI": "Q33", "IL": "Q801", "NZ": "Q664", "PL": "Q36", "TR": "Q43", "PH": "Q928", "VN": "Q881",
    "TW": "Q865", "BD": "Q902", "PK": "Q843", "LK": "Q854", "NG": "Q1033", "EG": "Q79", "KE": "Q114",
}

QUERY = """SELECT ?cLabel (SAMPLE(?indLabel) AS ?industry) WHERE {{
  ?c wdt:P414 ?ex ; wdt:P17 wd:{country} .
  OPTIONAL {{ ?c wdt:P452 ?ind . ?ind rdfs:label ?indLabel . FILTER(LANG(?indLabel) = "en") }}
  ?c rdfs:label ?cLabel . FILTER(LANG(?cLabel) = "en")
}} GROUP BY ?cLabel"""


def fetch_country(code: str, qid: str, *, retries: int = 3) -> list[dict]:
    cache = CACHE_DIR / f"{code}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    url = ENDPOINT + "?format=json&query=" + urllib.parse.quote(QUERY.format(country=qid))
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.load(response)
            rows = [
                {"name": b["cLabel"]["value"], "industry": b.get("industry", {}).get("value"), "country": code}
                for b in payload["results"]["bindings"]
            ]
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(rows), encoding="utf-8")
            return rows
        except (urllib.error.URLError, TimeoutError, ValueError):
            time.sleep(10 * (attempt + 1))
    return []


def fetch_all(pause: float = 2.0) -> list[dict]:
    rows: list[dict] = []
    for code, qid in COUNTRIES.items():
        cached = (CACHE_DIR / f"{code}.json").exists()
        rows.extend(fetch_country(code, qid))
        if not cached:
            time.sleep(pause)
    return rows


if __name__ == "__main__":
    print(len(fetch_all()), "companies")
