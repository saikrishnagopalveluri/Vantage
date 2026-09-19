import time

from fastapi.testclient import TestClient

from app import auth
from app.main import app
from app.models import Account, User
from tests.conftest import as_user

CREDS = {"email": "Asha@Example.com ", "password": "correct horse battery"}


def fresh(client):
    """A client with its own cookie jar."""
    return TestClient(app)


def signup(client, **over):
    return client.post("/auth/signup", json={**CREDS, **over})


def test_password_hashes_are_salted_and_verify():
    a, b = auth.hash_password("hunter2hunter2"), auth.hash_password("hunter2hunter2")
    assert a != b and a.startswith("scrypt$")
    assert auth.verify_password("hunter2hunter2", a) and not auth.verify_password("hunter3hunter3", a)
    assert not auth.verify_password("x", "garbage") and not auth.verify_password("x", "md5$1$2$3$4$5")


def test_tokens_are_signed_expire_and_reject_tampering():
    token = auth.make_token("user-1")
    assert auth.read_token(token) == "user-1"
    assert auth.read_token(auth.make_token("user-1", now=time.time() - 40 * 86400)) is None
    payload, expires, signature = token.split(".")
    assert auth.read_token(f"{auth._b64(b'user-2')}.{expires}.{signature}") is None
    assert auth.read_token(f"{payload}.{expires}.{signature[:-2]}AA") is None
    assert auth.read_token("nonsense") is None and auth.read_token(None) is None


def test_signup_sets_an_httponly_cookie_and_me_works(client, session_factory):
    res = signup(client)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "asha@example.com" and body["onboarded"] is False
    cookie = res.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "vantage_session=" in cookie
    assert client.get("/auth/me").json()["user_id"] == body["user_id"]
    with session_factory() as db:
        stored = db.query(Account).one()
        assert "correct horse" not in stored.password_hash and stored.password_hash.startswith("scrypt$")


def test_signup_validation_and_duplicates(client):
    assert signup(client, email="not-an-email").status_code == 422
    short = signup(client, password="short")
    assert short.status_code == 422 and "at least 8" in short.json()["detail"]
    assert signup(client).status_code == 201
    dup = signup(fresh(client), email="ASHA@example.com")
    assert dup.status_code == 409 and "Log in instead" in dup.json()["detail"]


def test_login_logout_and_a_wrong_password_gives_no_hints(client):
    signup(client)
    other = fresh(client)
    bad = other.post("/auth/login", json={**CREDS, "password": "wrong password!"})
    ghost = other.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong password!"})
    assert bad.status_code == ghost.status_code == 401 and bad.json() == ghost.json()
    assert other.get("/auth/me").status_code == 401
    ok = other.post("/auth/login", json=CREDS)
    assert ok.status_code == 200 and other.get("/auth/me").status_code == 200
    assert other.post("/auth/logout").status_code == 204
    assert other.get("/auth/me").status_code == 401


def test_repeated_failures_pause_logins_for_that_email(client, monkeypatch):
    monkeypatch.setattr(auth, "throttle", auth.LoginThrottle(limit=3, window=900))
    monkeypatch.setattr("app.routers.auth.auth.throttle", auth.throttle)
    signup(client)
    other = fresh(client)
    for _ in range(3):
        assert other.post("/auth/login", json={**CREDS, "password": "nope nope nope"}).status_code == 401
    blocked = other.post("/auth/login", json=CREDS)  # even the right password waits
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0


def test_the_cookie_alone_authenticates_reads_and_an_account_id_cannot_be_used_as_a_guest(client, db):
    user_id = signup(client).json()["user_id"]
    db.add(User(id=user_id))
    db.commit()
    assert client.get(f"/profile/{user_id}").status_code == 404  # signed in, no profile yet (not 401)
    guest = fresh(client)
    assert guest.get(f"/profile/{user_id}", headers=as_user(user_id)).status_code == 401  # id is reserved
    assert guest.get(f"/profile/{user_id}").status_code == 401


def test_writes_with_a_cookie_need_the_matching_header(client):
    user_id = signup(client).json()["user_id"]
    body = {"domain_ids": [], "target_role_ids": [], "target_company_ids": [], "capability_ids": []}
    assert client.post("/onboarding", json=body).status_code == 403  # what a cross-site form would send
    assert client.post("/onboarding", json=body, headers={"X-User-Id": "someone-else"}).status_code == 403
    ok = client.post("/onboarding", json=body, headers={"X-User-Id": user_id})
    assert ok.status_code == 201
    assert client.get("/auth/me").json()["onboarded"] is True


def test_another_user_still_cannot_read_a_profile(client):
    user_id = signup(client).json()["user_id"]
    assert client.get("/profile/someone-else").status_code == 403
    assert client.get(f"/profile/{user_id}").status_code in {200, 404}


def test_guests_can_be_switched_off(client, monkeypatch):
    monkeypatch.setenv("VANTAGE_ALLOW_GUESTS", "0")
    assert client.get("/profile/g1", headers=as_user("g1")).status_code == 401


def test_the_cookie_is_secure_behind_a_proxy_chain(client):
    res = client.post(
        "/auth/signup", json=CREDS, headers={"x-forwarded-proto": "https,http"}
    )
    assert res.status_code == 201 and "Secure" in res.headers["set-cookie"]
    plain = fresh(client).post("/auth/signup", json={**CREDS, "email": "b@example.com"}, headers={"x-forwarded-proto": "http"})
    assert "Secure" not in plain.headers["set-cookie"]
