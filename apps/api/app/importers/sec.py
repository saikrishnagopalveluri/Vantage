"""SEC-registered companies: names and tickers from the public ticker file, industries from SIC codes.

The SIC lookup needs one request per company (SEC allows 10 per second), so it is resumable:
every answer is appended to data/raw/sec_sic.jsonl and already-fetched CIKs are skipped.
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request
from pathlib import Path

from app.importers.common import RAW_DIR, USER_AGENT, download

TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
TICKERS_FILE = RAW_DIR / "sec_exchange.json"
SIC_FILE = RAW_DIR / "sec_sic.jsonl"


def load_tickers(path: Path = TICKERS_FILE) -> list[dict]:
    download(TICKERS_URL, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    fields = payload["fields"]
    return [dict(zip(fields, row)) for row in payload["data"]]


def load_sic(path: Path = SIC_FILE) -> dict[int, dict]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["cik"]] = row
    return out


def _fetch_one(cik: int) -> dict | None:
    request = urllib.request.Request(SUBMISSIONS_URL.format(cik=cik), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
        return {"cik": cik, "sic": data.get("sic") or "", "desc": data.get("sicDescription") or ""}
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return {"cik": cik, "sic": "", "desc": ""}
        time.sleep(3)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        time.sleep(1)
    return None  # not cached, so the next run retries it


def fetch_sic(
    ciks: list[int], path: Path = SIC_FILE, per_second: float = 8.0, workers: int = 12, limit: int | None = None
) -> int:
    """Fetch SIC code and description for each CIK not already cached, staying under SEC's 10 req/s."""
    done = load_sic(path)
    todo = [c for c in dict.fromkeys(ciks) if c not in done]
    if limit is not None:
        todo = todo[:limit]
    path.parent.mkdir(parents=True, exist_ok=True)
    lock, next_slot = threading.Lock(), [time.monotonic()]

    def paced(cik: int) -> dict | None:
        with lock:
            wait = next_slot[0] - time.monotonic()
            next_slot[0] = max(next_slot[0], time.monotonic()) + 1 / per_second
        if wait > 0:
            time.sleep(wait)
        return _fetch_one(cik)

    fetched = 0
    with path.open("a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(paced, todo):
            if row is not None:
                out.write(json.dumps(row) + "\n")
                out.flush()
                fetched += 1
    return fetched


if __name__ == "__main__":
    tickers = load_tickers()
    print(f"{len(tickers)} tickers; fetching SIC codes (resumable)")
    print("fetched", fetch_sic([t["cik"] for t in tickers]))
