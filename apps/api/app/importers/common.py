import re
import time
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
USER_AGENT = "Vantage/1.0 (career news app; contact: hello@vantage.app)"

_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited", "plc", "llc",
    "lp", "llp", "sa", "ag", "nv", "se", "bv", "gmbh", "pte", "pvt", "private", "public", "the",
    "holdings", "holding", "group", "de", "cv", "sab", "spa", "ab", "oyj", "asa", "as",
}


def singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith(("ss", "us", "is")) and len(word) > 3:
        return word[:-1]
    return word


def norm_title(title: str) -> str:
    words = re.sub(r"[^a-z0-9& ]+", " ", title.lower()).split()
    return " ".join(singular(w) for w in words)


def norm_company(name: str) -> str:
    words = re.sub(r"[^a-z0-9& ]+", " ", name.lower()).split()
    while words and words[-1] in _SUFFIXES:
        words.pop()
    while words and words[0] in _SUFFIXES:
        words.pop(0)
    return " ".join(words)


def download(url: str, dest: Path, *, headers: dict | None = None, pause: float = 0.0) -> Path:
    """Fetch once and cache under data/raw. A cached file is never re-downloaded."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    dest.write_bytes(data)
    if pause:
        time.sleep(pause)
    return dest
