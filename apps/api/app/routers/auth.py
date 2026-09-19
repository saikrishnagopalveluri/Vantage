import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth
from app.deps import get_db
from app.legal import ConsentIn, record_consent
from app.models import Account, User

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=auth.MAX_PASSWORD)
    consent: ConsentIn | None = None  # required to sign up, ignored for log in


class AuthOut(BaseModel):
    user_id: str
    email: str
    onboarded: bool


def _secure(request: Request) -> bool:
    if os.getenv("VANTAGE_COOKIE_SECURE") == "1":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return request.url.scheme == "https" or forwarded == "https"


def _start_session(request: Request, response: Response, user_id: str) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_token(user_id),
        max_age=auth.SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=_secure(request),
        path="/",
    )


def _out(db: Session, account: Account) -> AuthOut:
    return AuthOut(user_id=account.user_id, email=account.email, onboarded=db.get(User, account.user_id) is not None)


@router.post("/signup", response_model=AuthOut, status_code=201)
def signup(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)) -> AuthOut:
    email = auth.normalize_email(body.email)
    if not auth.valid_email(email):
        raise HTTPException(status_code=422, detail="That doesn't look like an email address.")
    if len(body.password) < auth.MIN_PASSWORD:
        raise HTTPException(status_code=422, detail=f"Use at least {auth.MIN_PASSWORD} characters for your password.")
    if db.scalar(select(Account.user_id).where(Account.email == email)) is not None:
        raise HTTPException(status_code=409, detail="That email already has an account. Log in instead.")
    account = Account(user_id=str(uuid.uuid4()), email=email, password_hash=auth.hash_password(body.password))
    db.add(account)
    record_consent(db, account.user_id, body.consent, "signup")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That email already has an account. Log in instead.")
    _start_session(request, response, account.user_id)
    return _out(db, account)


@router.post("/login", response_model=AuthOut)
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)) -> AuthOut:
    email = auth.normalize_email(body.email)
    wait = auth.throttle.retry_after(email)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Too many tries. Wait a few minutes and try again.",
            headers={"Retry-After": str(wait)},
        )
    account = db.scalar(select(Account).where(Account.email == email))
    # Same work whether or not the email exists, and the same answer, so nobody can probe for accounts.
    ok = auth.verify_password(body.password, account.password_hash if account else auth.DUMMY_HASH)
    if account is None or not ok:
        auth.throttle.fail(email)
        raise HTTPException(status_code=401, detail="That email and password don't match.")
    auth.throttle.clear(email)
    _start_session(request, response, account.user_id)
    return _out(db, account)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(auth.COOKIE_NAME, path="/")


@router.get("/me", response_model=AuthOut)
def me(request: Request, db: Session = Depends(get_db)) -> AuthOut:
    user_id = auth.read_token(request.cookies.get(auth.COOKIE_NAME))
    account = db.get(Account, user_id) if user_id else None
    if account is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return _out(db, account)
