"""Accounts: password hashing, signed session tokens and a login throttle. Standard library only.

Passwords are hashed with scrypt and a per-user salt. A session is a signed token
(`user_id.expiry.signature`, HMAC-SHA256) kept in an HttpOnly, SameSite=Lax cookie, so page
scripts can never read it. The signing secret comes from VANTAGE_SECRET, or from a key file that is
created on first run and never committed.
"""

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path

COOKIE_NAME = "vantage_session"
SESSION_DAYS = 30
MIN_PASSWORD = 8
MAX_PASSWORD = 128

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s.]{2,}$")
_KEY_FILE = Path(__file__).resolve().parents[1] / "data" / "secret.key"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(_EMAIL.match(email))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(password.encode(), salt=_unb64(salt), dklen=32, n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(candidate, _unb64(digest))
    except (ValueError, TypeError):
        return False


# Checked when the email is unknown, so "no such account" costs the same time as "wrong password".
DUMMY_HASH = hash_password("not-a-real-password")


def _secret() -> bytes:
    env = os.getenv("VANTAGE_SECRET")
    if env:
        return env.encode()
    if not _KEY_FILE.exists():
        try:
            _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            _KEY_FILE.write_text(secrets.token_hex(32), encoding="utf-8")
        except OSError as exc:
            raise RuntimeError("Set VANTAGE_SECRET: there is nowhere to keep a signing key on this host.") from exc
    return _KEY_FILE.read_text(encoding="utf-8").strip().encode()


def _sign(payload: str) -> str:
    return _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())


def make_token(user_id: str, now: float | None = None) -> str:
    expires = int((now or time.time()) + SESSION_DAYS * 86400)
    payload = f"{_b64(user_id.encode())}.{expires}"
    return f"{payload}.{_sign(payload)}"


def read_token(token: str | None, now: float | None = None) -> str | None:
    """The user id inside a valid, unexpired token, otherwise None."""
    if not token:
        return None
    try:
        encoded_id, expires, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(f"{encoded_id}.{expires}")):
            return None
        if int(expires) < (now or time.time()):
            return None
        return _unb64(encoded_id).decode()
    except (ValueError, UnicodeDecodeError):
        return None


class LoginThrottle:
    """Too many wrong passwords for one email pauses logins for it. In memory, so it resets on
    restart and is per process; put a shared store or a proxy rule in front for a real deployment."""

    def __init__(self, limit: int = 8, window: int = 900) -> None:
        self.limit, self.window = limit, window
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, key: str, now: float) -> deque[float]:
        failures = self._failures[key]
        while failures and now - failures[0] > self.window:
            failures.popleft()
        return failures

    def retry_after(self, key: str, now: float | None = None) -> int:
        now = now or time.time()
        failures = self._recent(key, now)
        return int(self.window - (now - failures[0])) + 1 if len(failures) >= self.limit else 0

    def fail(self, key: str, now: float | None = None) -> None:
        now = now or time.time()
        self._recent(key, now).append(now)

    def clear(self, key: str) -> None:
        self._failures.pop(key, None)


throttle = LoginThrottle()
