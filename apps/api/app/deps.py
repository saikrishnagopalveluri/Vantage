import os
from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import COOKIE_NAME, read_token
from app.db import SessionLocal
from app.models import Account

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def guests_allowed() -> bool:
    return os.getenv("VANTAGE_ALLOW_GUESTS", "1").lower() not in {"0", "false", "no", "off"}


def get_caller_id(
    request: Request,
    x_user_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    """Who is calling. A signed session cookie is the strong proof. Without one, the caller is a
    guest whose random device id acts as the key (kept for people without an account), and an id
    that belongs to an account can never be used that way."""
    account_id = read_token(request.cookies.get(COOKIE_NAME))
    if account_id:
        # A cross-site page can send the cookie but cannot add this header, so writes must carry it.
        if request.method not in SAFE_METHODS and x_user_id != account_id:
            raise HTTPException(status_code=403, detail="Missing or mismatched X-User-Id header")
        return account_id
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    if db.scalar(select(Account.user_id).where(Account.user_id == x_user_id)) is not None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    if not guests_allowed():
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return x_user_id


def require_self(user_id: str, caller_id: str) -> None:
    if user_id != caller_id:
        raise HTTPException(status_code=403, detail="Cannot access another user's profile")
