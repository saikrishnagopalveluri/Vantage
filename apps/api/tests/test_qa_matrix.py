"""Broad black-box matrix: equivalence classes, boundaries, negative input, security and state.

Case-id prefixes in the test names (AUTH, TAX, ONB, ...) map to the areas in docs/TEST_PLAN.md.
"""

import uuid

import pytest

from app import auth
from app.models import Account, Article, Source
from tests.conftest import as_user


def uniq_email(tag: str = "t") -> str:
    return f"{tag}-{uuid.uuid4().hex[:10]}@example.com"


def signup(client, email=None, password="correct horse 42", **extra):
    return client.post("/auth/signup", json={"email": uniq_email() if email is None else email, "password": password, **extra})


@pytest.fixture(autouse=True)
def _fresh_throttle():
    auth.throttle._failures.clear()
    yield
    auth.throttle._failures.clear()


# ---- AUTH: signup -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "length, status",
    [(0, 422), (1, 422), (7, 422), (8, 201), (9, 201), (64, 201), (127, 201), (128, 201), (129, 422), (5000, 422)],
    ids=lambda v: str(v),
)
def test_AUTH_password_length_boundaries(client, length, status):
    assert signup(client, password="a" * length).status_code == status


@pytest.mark.parametrize(
    "email",
    ["plainaddress", "@no-local.com", "no-at.example.com", "two@@example.com", "spa ce@example.com", "a@b", "a@b.c",
     "a@.com", "", "   ", "a@b.c d", "x" * 65 + "@example.com", "a@" + "b" * 260 + ".com", "\n@example.com"],
    ids=lambda v: repr(v)[:30],
)
def test_AUTH_invalid_emails_are_rejected(client, email):
    assert signup(client, email=email).status_code == 422


@pytest.mark.parametrize(
    "email",
    ["a@example.com", "first.last@example.co.in", "user+tag@example.com", "UPPER@EXAMPLE.COM", "  padded@example.com  ",
     "x" * 64 + "@example.com", "numbers123@sub.domain.example.org", "o'brien@example.com", "user_name@example.io"],
    ids=lambda v: repr(v)[:30],
)
def test_AUTH_valid_emails_are_accepted_and_normalised(client, email):
    r = signup(client, email=email)
    assert r.status_code == 201, r.text
    assert r.json()["email"] == email.strip().lower()


def test_AUTH_email_is_case_and_whitespace_insensitive_for_duplicates(client):
    assert signup(client, email="Dup@Example.com").status_code == 201
    assert signup(client, email="  dup@example.com ").status_code == 409
    assert signup(client, email="DUP@EXAMPLE.COM").status_code == 409


@pytest.mark.parametrize(
    "body",
    [{}, {"email": "a@example.com"}, {"password": "longenough1"}, {"email": None, "password": None},
     {"email": 123, "password": "longenough1"}, {"email": ["a@example.com"], "password": "longenough1"},
     {"email": "a@example.com", "password": {"x": 1}}],
    ids=["empty", "no-password", "no-email", "nulls", "int-email", "list-email", "dict-password"],
)
def test_AUTH_malformed_signup_bodies_are_422(client, body):
    assert client.post("/auth/signup", json=body).status_code == 422


def test_AUTH_non_json_and_wrong_content_type(client):
    assert client.post("/auth/signup", content="email=a&password=b", headers={"content-type": "application/x-www-form-urlencoded"}).status_code == 422
    assert client.post("/auth/signup", content="{not json", headers={"content-type": "application/json"}).status_code == 422


@pytest.mark.parametrize(
    "password",
    ["pässwörd-ünïcode", "密码密码密码密码", "emoji-🔒🔒🔒🔒", "  spaces around  ", "quote'\"and;--drop", "<script>alert(1)</script>", "tab\tin\tside", "a" * 8],
    ids=["latin-ext", "cjk", "emoji", "spaces", "sql-ish", "xss-ish", "tabs", "min"],
)
def test_AUTH_unusual_passwords_round_trip(client, password):
    email = uniq_email()
    assert signup(client, email=email, password=password).status_code == 201
    assert client.post("/auth/login", json={"email": email, "password": password}).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": password + "x"}).status_code == 401


@pytest.mark.parametrize("payload", ["' OR '1'='1", "'; DROP TABLE accounts;--", "admin'--", "a@example.com' OR 1=1--"])
def test_AUTH_sql_injection_strings_never_authenticate(client, payload):
    signup(client, email="victim@example.com")
    assert client.post("/auth/login", json={"email": payload, "password": payload}).status_code == 401
    assert client.post("/auth/login", json={"email": "victim@example.com", "password": payload}).status_code == 401
    assert client.get("/taxonomy/domains").status_code == 200  # tables still there


def test_AUTH_password_is_hashed_and_never_returned(client, db):
    r = signup(client, email="hash@example.com", password="plain-secret-1")
    assert "plain-secret-1" not in r.text and "password" not in r.json()
    stored = db.query(Account).filter_by(email="hash@example.com").one().password_hash
    assert stored.startswith("scrypt$") and "plain-secret-1" not in stored


def test_AUTH_same_password_gets_different_salts(client, db):
    signup(client, email="s1@example.com", password="same-password-1")
    signup(client, email="s2@example.com", password="same-password-1")
    assert len({a.password_hash for a in db.query(Account).all()}) == 2


# ---- AUTH: login / session ---------------------------------------------------------------


def test_AUTH_unknown_email_and_wrong_password_look_identical(client):
    signup(client, email="known@example.com")
    a = client.post("/auth/login", json={"email": "known@example.com", "password": "wrong-password"})
    b = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert (a.status_code, a.json()) == (b.status_code, b.json())
    assert a.status_code == 401


def test_AUTH_login_is_case_insensitive_on_email(client):
    signup(client, email="mixed@example.com", password="right-password")
    assert client.post("/auth/login", json={"email": "MIXED@Example.COM", "password": "right-password"}).status_code == 200


def test_AUTH_password_is_case_sensitive(client):
    signup(client, email="case@example.com", password="Right-Password")
    assert client.post("/auth/login", json={"email": "case@example.com", "password": "right-password"}).status_code == 401


def test_AUTH_throttle_locks_after_eight_failures_then_recovers_on_clear(client):
    signup(client, email="thr@example.com", password="right-password")
    codes = [client.post("/auth/login", json={"email": "thr@example.com", "password": "nope-nope"}).status_code for _ in range(8)]
    assert codes == [401] * 8
    locked = client.post("/auth/login", json={"email": "thr@example.com", "password": "right-password"})
    assert locked.status_code == 429 and int(locked.headers["retry-after"]) > 0  # even the right password waits
    auth.throttle.clear("thr@example.com")
    assert client.post("/auth/login", json={"email": "thr@example.com", "password": "right-password"}).status_code == 200


def test_AUTH_throttle_is_per_email(client):
    signup(client, email="a1@example.com", password="right-password")
    signup(client, email="a2@example.com", password="right-password")
    for _ in range(8):
        client.post("/auth/login", json={"email": "a1@example.com", "password": "bad-bad-bad"})
    assert client.post("/auth/login", json={"email": "a2@example.com", "password": "right-password"}).status_code == 200


def test_AUTH_successful_login_resets_failure_count(client):
    signup(client, email="reset@example.com", password="right-password")
    for _ in range(7):
        client.post("/auth/login", json={"email": "reset@example.com", "password": "bad-bad-bad"})
    assert client.post("/auth/login", json={"email": "reset@example.com", "password": "right-password"}).status_code == 200
    for _ in range(7):
        assert client.post("/auth/login", json={"email": "reset@example.com", "password": "bad-bad-bad"}).status_code == 401


def test_AUTH_cookie_flags_over_http(client):
    cookie = signup(client).headers["set-cookie"].lower()
    assert "vantage_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert "; secure" not in cookie  # plain http: no Secure flag


@pytest.mark.parametrize("proto, secure", [("https", True), ("https,http", True), ("HTTPS", True), ("http", False), ("http,https", False), ("", False)])
def test_AUTH_secure_flag_follows_forwarded_proto(client, proto, secure):
    r = client.post("/auth/signup", json={"email": uniq_email(), "password": "correct horse 42"}, headers={"x-forwarded-proto": proto})
    assert ("; secure" in r.headers["set-cookie"].lower()) is secure


def test_AUTH_max_age_is_thirty_days(client):
    assert f"max-age={30 * 86400}" in signup(client).headers["set-cookie"].lower()


def test_AUTH_me_requires_a_cookie(client):
    assert client.get("/auth/me").status_code == 401


def test_AUTH_me_after_signup_and_logout(client):
    signup(client, email="me@example.com")
    me = client.get("/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "me@example.com" and me.json()["onboarded"] is False
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_AUTH_logout_without_session_is_fine(client):
    assert client.post("/auth/logout").status_code == 204


@pytest.mark.parametrize("token", ["", "garbage", "a.b.c", "....", "x" * 500, "YQ.9999999999.AAAA", None])
def test_AUTH_forged_tokens_are_rejected(client, token):
    cookies = {} if token is None else {"vantage_session": token}
    assert client.get("/auth/me", cookies=cookies).status_code == 401


def test_AUTH_token_signature_tampering_and_expiry():
    good = auth.make_token("user-1")
    assert auth.read_token(good) == "user-1"
    encoded, expires, sig = good.split(".")
    assert auth.read_token(f"{encoded}.{int(expires) + 1}.{sig}") is None  # extended expiry
    other = auth.make_token("user-2").split(".")[0]
    assert auth.read_token(f"{other}.{expires}.{sig}") is None  # swapped user id
    assert auth.read_token(good, now=int(expires) + 1) is None  # expired
    assert auth.read_token(good, now=int(expires) - 5) == "user-1"  # just before expiry


def test_AUTH_token_from_another_secret_is_rejected(client, monkeypatch):
    signup(client, email="sec@example.com")
    cookie = client.cookies.get("vantage_session")
    client.cookies.clear()
    monkeypatch.setenv("VANTAGE_SECRET", "a-different-signing-key-entirely-0123456789")
    assert client.get("/auth/me", cookies={"vantage_session": cookie}).status_code == 401


# ---- CSRF and guest boundary ----------------------------------------------------------


def test_CSRF_cookie_writes_need_matching_x_user_id(client):
    uid = signup(client).json()["user_id"]
    body = {"domain_ids": [], "target_role_ids": [], "target_company_ids": [], "capability_ids": []}
    assert client.post("/onboarding", json=body).status_code == 403  # cookie but no header
    assert client.post("/onboarding", json=body, headers=as_user("someone-else")).status_code == 403
    assert client.post("/onboarding", json=body, headers=as_user(uid)).status_code == 201


def test_GUEST_needs_an_identity_header_for_everything(client):
    assert client.post("/onboarding", json={}).status_code == 401
    assert client.get("/profile/whoever").status_code == 401
    assert client.get("/feed/whoever").status_code == 401
    assert client.get("/jds/whoever").status_code == 401
    assert client.get("/privacy/export").status_code == 401


def test_GUEST_cannot_impersonate_an_account_id(client):
    uid = signup(client).json()["user_id"]
    client.cookies.clear()
    assert client.get(f"/profile/{uid}", headers=as_user(uid)).status_code == 401
    assert client.get("/privacy/export", headers=as_user(uid)).status_code == 401


def test_GUEST_mode_can_be_switched_off(client, monkeypatch):
    monkeypatch.setenv("VANTAGE_ALLOW_GUESTS", "0")
    assert client.get("/profile/x", headers=as_user("x")).status_code == 401
    monkeypatch.setenv("VANTAGE_ALLOW_GUESTS", "1")
    assert client.get("/profile/x", headers=as_user("x")).status_code == 404  # let in, but no profile yet


# ---- TAX: taxonomy read endpoints -------------------------------------------------------------


@pytest.mark.parametrize("path", ["/taxonomy/roles", "/taxonomy/companies", "/taxonomy/capabilities"])
@pytest.mark.parametrize("limit, status", [(0, 422), (-1, 422), (1, 200), (100, 200), (500, 200), (501, 422), ("abc", 422), ("", 422)])
def test_TAX_limit_boundaries(client, taxonomy, path, limit, status):
    assert client.get(path, params={"limit": limit}).status_code == status


@pytest.mark.parametrize("path", ["/taxonomy/roles", "/taxonomy/companies", "/taxonomy/capabilities"])
@pytest.mark.parametrize("offset, status", [(-1, 422), (0, 200), (10_000, 200), ("x", 422)])
def test_TAX_offset_boundaries(client, taxonomy, path, offset, status):
    r = client.get(path, params={"offset": offset})
    assert r.status_code == status
    if offset == 10_000:
        assert r.json() == []


def test_TAX_limit_one_returns_at_most_one(client, taxonomy):
    assert len(client.get("/taxonomy/roles", params={"limit": 1}).json()) == 1


def test_TAX_pagination_pages_do_not_overlap(client, taxonomy):
    first = [r["id"] for r in client.get("/taxonomy/companies", params={"limit": 2, "offset": 0}).json()]
    second = [r["id"] for r in client.get("/taxonomy/companies", params={"limit": 2, "offset": 2}).json()]
    assert first and second and not set(first) & set(second)


@pytest.mark.parametrize("q", ["%", "_", "%%", "\\", "' OR 1=1 --", "\"; DROP TABLE roles; --", "<script>", "日本語", "🙂", "a" * 500])
def test_TAX_search_text_is_treated_literally(client, taxonomy, q):
    r = client.get("/taxonomy/roles", params={"q": q})
    assert r.status_code == 200 and r.json() == []  # wildcards are escaped, so nothing matches
    assert client.get("/taxonomy/domains").status_code == 200


@pytest.mark.parametrize("q", ["brand", "BRAND", "Brand Manager", "manager"])
def test_TAX_role_search_is_case_insensitive_substring(client, taxonomy, q):
    titles = [r["title"] for r in client.get("/taxonomy/roles", params={"q": q}).json()]
    assert "Brand Manager" in titles


def test_TAX_role_search_order_is_deterministic(client, taxonomy):
    a = [r["title"] for r in client.get("/taxonomy/roles", params={"q": "manager"}).json()]
    assert a and a == [r["title"] for r in client.get("/taxonomy/roles", params={"q": "manager"}).json()]


@pytest.mark.parametrize("path", ["/taxonomy/roles/nope", "/taxonomy/companies/nope", "/taxonomy/roles/%00", "/taxonomy/roles/' OR 1=1"])
def test_TAX_unknown_ids_are_404_not_500(client, taxonomy, path):
    assert client.get(path).status_code == 404


def test_TAX_unknown_filters_return_empty_lists(client, taxonomy):
    assert client.get("/taxonomy/roles", params={"domain_id": "nope"}).json() == []
    assert client.get("/taxonomy/companies", params={"industry_id": "nope"}).json() == []
    assert client.get("/taxonomy/companies", params={"domain_id": "nope"}).json() == []
    assert client.get("/taxonomy/capabilities", params={"domain_id": "nope"}).status_code == 200


def test_TAX_role_detail_shape_and_company_links(client, taxonomy):
    d = client.get(f"/taxonomy/roles/{taxonomy.bm.id}").json()
    assert d["title"] == "Brand Manager" and isinstance(d["aliases"], list) and isinstance(d["capabilities"], list)
    assert d["companies_total"] >= len(d["companies"])


def test_TAX_role_detail_derived_hiring_respects_industry_limit(client, taxonomy):
    names = {c["name"] for c in client.get(f"/taxonomy/roles/{taxonomy.bm.id}").json()["companies"]}
    assert "HUL" in names and "Amazon" not in names  # Brand Manager is limited to FMCG


def test_TAX_company_detail_includes_articles_list(client, taxonomy):
    d = client.get(f"/taxonomy/companies/{taxonomy.hul.id}").json()
    assert d["name"] == "HUL" and d["industry"]["name"] == "FMCG" and isinstance(d["articles"], list)


@pytest.mark.parametrize("q, status", [("", 422), ("a", 422), ("ab", 200), ("a" * 80, 200), ("a" * 81, 422)])
def test_TAX_search_length_boundaries(client, taxonomy, q, status):
    assert client.get("/taxonomy/search", params={"q": q}).status_code == status


def test_TAX_search_missing_q_is_422(client, taxonomy):
    assert client.get("/taxonomy/search").status_code == 422


def test_TAX_search_groups_and_caps_results(client, taxonomy):
    r = client.get("/taxonomy/search", params={"q": "ma"}).json()
    assert set(r) == {"query", "roles", "companies", "capabilities", "articles"}
    assert all(len(r[k]) <= 8 for k in ("roles", "companies", "capabilities"))


def test_TAX_search_finds_each_kind(client, taxonomy):
    assert client.get("/taxonomy/search", params={"q": "brand man"}).json()["roles"]
    assert client.get("/taxonomy/search", params={"q": "nestle"}).json()["companies"]
    assert client.get("/taxonomy/search", params={"q": "excel"}).json()["capabilities"]


def test_TAX_capability_kind_filter_and_bad_kind(client, taxonomy):
    tools = client.get("/taxonomy/capabilities", params={"kind": "tool"}).json()
    assert tools and {c["kind"] for c in tools} == {"tool"}
    assert client.get("/taxonomy/capabilities", params={"kind": "bogus"}).status_code == 422


def test_TAX_mba_flag_filters_only_flagged_rows(client, db, taxonomy):
    taxonomy.bm.mba = True
    db.commit()
    assert [r["title"] for r in client.get("/taxonomy/roles", params={"mba": "true"}).json()] == ["Brand Manager"]
    assert len(client.get("/taxonomy/roles").json()) == 2


def test_TAX_families_only_hides_variants(client, db, taxonomy):
    from app.models import Role

    db.add(Role(title="Senior Brand Manager", domain_id=taxonomy.bm.domain_id, parent_id=taxonomy.bm.id, taggable=False))
    db.commit()
    all_titles = {r["title"] for r in client.get("/taxonomy/roles").json()}
    fam_titles = {r["title"] for r in client.get("/taxonomy/roles", params={"families_only": "true"}).json()}
    assert "Senior Brand Manager" in all_titles and "Senior Brand Manager" not in fam_titles


def test_TAX_domains_have_counts(client, taxonomy):
    d = client.get("/taxonomy/domains").json()
    assert d and {"id", "name", "slug", "group", "role_count", "family_count"} <= set(d[0])


def test_TAX_industries_listed(client, taxonomy):
    assert {i["name"] for i in client.get("/taxonomy/industries").json()} >= {"FMCG", "E-commerce"}


# ---- ONB / PROF: onboarding & profile -----------------------------------------------------------------


def onboard_body(t, **over):
    body = {"domain_ids": [], "target_role_ids": [t.bm.id], "target_company_ids": [t.hul.id], "capability_ids": [t.excel.id]}
    body.update(over)
    return body


def test_ONB_student_happy_path(client, taxonomy):
    assert client.post("/onboarding", json=onboard_body(taxonomy), headers=as_user("g1")).status_code == 201
    p = client.get("/profile/g1", headers=as_user("g1")).json()
    assert p["profile_status"] == "targeting" and p["current_role"] is None


def test_ONB_working_professional_starts_placed(client, taxonomy):
    body = onboard_body(taxonomy, current={"company_id": taxonomy.hul.id, "role_id": taxonomy.bm.id})
    r = client.post("/onboarding", json=body, headers=as_user("g2")).json()
    assert r["profile_status"] == "placed" and r["current_company"]["name"] == "HUL" and r["placed_at"] is None


def test_ONB_empty_targets_are_allowed(client, taxonomy):
    assert client.post("/onboarding", json={}, headers=as_user("g3")).status_code == 201


def test_ONB_second_onboarding_is_409(client, taxonomy):
    assert client.post("/onboarding", json={}, headers=as_user("g4")).status_code == 201
    assert client.post("/onboarding", json={}, headers=as_user("g4")).status_code == 409


@pytest.mark.parametrize("field, n", [("target_role_ids", 51), ("target_company_ids", 51), ("capability_ids", 101)])
def test_ONB_list_size_caps(client, taxonomy, field, n):
    assert client.post("/onboarding", json={field: [str(i) for i in range(n)]}, headers=as_user(f"c-{field}")).status_code == 422


def test_ONB_domain_count_limit_is_four(client, db, taxonomy):
    from app.models import Domain

    domains = [Domain(name=f"Field {i}", slug=f"field-{i}") for i in range(5)]
    db.add_all(domains)
    db.commit()
    ids = [d.id for d in domains]
    assert client.post("/onboarding", json={"domain_ids": ids[:4]}, headers=as_user("d4")).status_code == 201
    assert client.post("/onboarding", json={"domain_ids": ids}, headers=as_user("d5")).status_code == 422


def test_ONB_unknown_ids_are_reported_by_field(client, taxonomy):
    r = client.post("/onboarding", json={"target_role_ids": ["nope"], "target_company_ids": ["nope2"], "capability_ids": ["nope3"]}, headers=as_user("u9"))
    assert r.status_code == 422
    unknown = r.json()["detail"]["unknown_ids"]
    assert unknown["target_role_ids"] == ["nope"] and unknown["target_company_ids"] == ["nope2"] and unknown["capability_ids"] == ["nope3"]


def test_ONB_unknown_current_company_or_role(client, taxonomy):
    r = client.post("/onboarding", json={"current": {"company_id": "x", "role_id": "y"}}, headers=as_user("u10"))
    assert r.status_code == 422 and set(r.json()["detail"]["unknown_ids"]) == {"current.company_id", "current.role_id"}


def test_ONB_failed_onboarding_leaves_no_profile(client, taxonomy):
    client.post("/onboarding", json={"target_role_ids": ["nope"]}, headers=as_user("u11"))
    assert client.get("/profile/u11", headers=as_user("u11")).status_code == 404


def test_ONB_duplicate_ids_are_deduplicated(client, taxonomy):
    body = onboard_body(taxonomy, target_role_ids=[taxonomy.bm.id] * 3)
    assert client.post("/onboarding", json=body, headers=as_user("u12")).status_code == 201
    assert len(client.get("/profile/u12", headers=as_user("u12")).json()["target_roles"]) == 1


@pytest.mark.parametrize("bad", [{"domain_ids": "x"}, {"target_role_ids": "x"}, {"target_role_ids": [1, 2]}, {"current": "x"}, {"current": {"company_id": "a"}}, {"consent": {"over_18": "maybe"}}])
def test_ONB_wrong_types_are_422(client, taxonomy, bad):
    assert client.post("/onboarding", json=bad, headers=as_user("uw")).status_code == 422


def test_PROF_other_users_profile_is_403(client, world):
    assert client.get("/profile/u1", headers=as_user("u2")).status_code == 403
    assert client.put("/profile/u1/targets", json={}, headers=as_user("u2")).status_code == 403
    assert client.get("/profile/u1/skill-gaps", headers=as_user("u2")).status_code == 403
    assert client.post("/profile/u1/placement", json={"company_id": "a", "role_id": "b"}, headers=as_user("u2")).status_code == 403


def test_PROF_targets_replace_not_append(client, world):
    ids = {"target_role_ids": [world.dmm.id], "target_company_ids": [], "domain_ids": [], "capability_ids": []}
    p = client.put("/profile/u1/targets", json=ids, headers=as_user("u1")).json()
    assert [r["title"] for r in p["target_roles"]] == ["Digital Marketing Manager"] and p["target_companies"] == []


def test_PROF_targets_with_unknown_ids_change_nothing(client, world):
    before = client.get("/profile/u1", headers=as_user("u1")).json()
    assert client.put("/profile/u1/targets", json={"target_role_ids": ["nope"]}, headers=as_user("u1")).status_code == 422
    assert client.get("/profile/u1", headers=as_user("u1")).json() == before


def test_PROF_placement_events(client, world):
    body = {"company_id": world.hul.id, "role_id": world.bm.id}
    first = client.post("/profile/u1/placement", json=body, headers=as_user("u1")).json()
    assert first["event_type"] == "placed" and first["profile_status"] == "placed"
    assert client.post("/profile/u1/placement", json=body, headers=as_user("u1")).json()["event_type"] == "unchanged"
    changed = client.post("/profile/u1/placement", json={**body, "role_id": world.dmm.id}, headers=as_user("u1")).json()
    assert changed["event_type"] == "role_changed"


def test_PROF_placement_unknown_company_or_role(client, world):
    r = client.post("/profile/u1/placement", json={"company_id": "nope", "role_id": world.bm.id}, headers=as_user("u1"))
    assert r.status_code in {404, 422}


def test_PROF_skill_gaps_shape(client, world):
    d = client.get("/profile/u1/skill-gaps", headers=as_user("u1")).json()
    assert d["user_id"] == "u1" and isinstance(d["target_roles"], list)


# ---- FEED --------------------------------------------------------------------------------------------


@pytest.fixture()
def articles(db, world):
    """Three stories about HUL (tagged through the real ingest path) and one nobody follows."""
    from datetime import datetime, timezone

    from app.ingest import FeedEntry, ingest_entries

    src = Source(name="Test Wire", feed_url="https://example.com/feed", authority=3)
    db.add(src)
    db.commit()
    now = datetime.now(timezone.utc)
    body = "HUL launched a new brand campaign. Brand managers are watching the results closely. Sales rose."
    titles = ["HUL launches monsoon soap campaign", "Brand managers weigh HUL pricing shift", "HUL supply chain hires analytics head"]
    entries = [FeedEntry(t, f"https://example.com/a{i}", body, now) for i, t in enumerate(titles)]
    entries.append(FeedEntry("Celebrity gossip roundup", "https://example.com/gossip", "Nothing relevant here at all.", now))
    ingest_entries(db, src, entries)
    return db.query(Article).filter(Article.url.like("%/a%")).all()


@pytest.mark.parametrize("params, status", [
    ({}, 200), ({"lens": "for_you"}, 200), ({"lens": "companies"}, 200), ({"lens": "skills"}, 200), ({"lens": "bogus"}, 422),
    ({"limit": 0}, 422), ({"limit": 1}, 200), ({"limit": 50}, 200), ({"limit": 51}, 422), ({"offset": -1}, 422), ({"offset": 9999}, 200),
    ({"limit": "x"}, 422), ({"domain_id": "nope"}, 200),
])
def test_FEED_parameter_matrix(client, world, params, status):
    assert client.get("/feed/u1", params=params, headers=as_user("u1")).status_code == status


def test_FEED_shape_and_paging(client, world, articles):
    page1 = client.get("/feed/u1", params={"limit": 1}, headers=as_user("u1")).json()
    assert page1["summary"]["total"] >= 1 and len(page1["items"]) == 1
    item = page1["items"][0]
    assert item["tier"] in {"critical", "relevant", "explore"} and item["brief"]["paragraphs"]
    if page1["has_more"]:
        page2 = client.get("/feed/u1", params={"limit": 1, "offset": 1}, headers=as_user("u1")).json()
        assert page2["items"][0]["id"] != item["id"]


def test_FEED_tier_counts_add_up(client, world, articles):
    s = client.get("/feed/u1", headers=as_user("u1")).json()["summary"]
    assert s["total"] == s["critical"] + s["relevant"] + s["explore"]


def test_FEED_other_user_and_missing_profile(client, world):
    assert client.get("/feed/u1", headers=as_user("u2")).status_code == 403
    assert client.get("/feed/ghost", headers=as_user("ghost")).status_code == 404


@pytest.mark.parametrize("action", ["save", "unsave", "dismiss", "undismiss", "read"])
def test_FEED_each_interaction_action_is_accepted(client, world, articles, action):
    r = client.post("/feed/u1/interaction", json={"article_id": articles[0].id, "action": action}, headers=as_user("u1"))
    assert r.status_code == 200


@pytest.mark.parametrize("body", [{"article_id": "x", "action": "like"}, {"article_id": "x"}, {"action": "save"}, {"article_id": 5, "action": "save"}, {}])
def test_FEED_bad_interaction_bodies_are_422(client, world, body):
    assert client.post("/feed/u1/interaction", json=body, headers=as_user("u1")).status_code == 422


def test_FEED_interaction_on_unknown_article_is_404(client, world):
    assert client.post("/feed/u1/interaction", json={"article_id": "nope", "action": "save"}, headers=as_user("u1")).status_code == 404


def test_FEED_save_is_idempotent_and_reversible(client, world, articles):
    aid = articles[0].id
    for _ in range(3):
        assert client.post("/feed/u1/interaction", json={"article_id": aid, "action": "save"}, headers=as_user("u1")).json()["saved"] is True
    assert len(client.get("/feed/u1/saved", headers=as_user("u1")).json()) == 1
    assert client.post("/feed/u1/interaction", json={"article_id": aid, "action": "unsave"}, headers=as_user("u1")).json()["saved"] is False
    assert client.post("/feed/u1/interaction", json={"article_id": aid, "action": "unsave"}, headers=as_user("u1")).status_code == 200


def test_FEED_dismissed_story_leaves_the_feed_and_returns_on_undismiss(client, world, articles):
    ids = lambda: {i["id"] for i in client.get("/feed/u1", params={"limit": 50}, headers=as_user("u1")).json()["items"]}  # noqa: E731
    before = ids()
    assert before
    aid = next(iter(before))
    client.post("/feed/u1/interaction", json={"article_id": aid, "action": "dismiss"}, headers=as_user("u1"))
    assert aid not in ids()
    client.post("/feed/u1/interaction", json={"article_id": aid, "action": "undismiss"}, headers=as_user("u1"))
    assert aid in ids()


def test_FEED_saving_is_private_to_the_user(client, world, articles):
    client.post("/feed/u1/interaction", json={"article_id": articles[0].id, "action": "save"}, headers=as_user("u1"))
    assert client.get("/feed/u2/saved", headers=as_user("u2")).json() == []
    assert client.post("/feed/u1/interaction", json={"article_id": articles[0].id, "action": "save"}, headers=as_user("u2")).status_code == 403


# ---- JD: job descriptions -------------------------------------------------------------------------------

JD_TEXT = "We are hiring a brand manager. You will build dashboards in Excel and Power BI and drive Consumer Insights work."


@pytest.mark.parametrize("length", [0, 1, 39, 40, 5000])
def test_JD_text_without_a_known_skill_is_rejected(client, world, length):
    assert client.post("/jds/u1", json={"text": "x" * length}, headers=as_user("u1")).status_code == 422


def test_JD_text_over_the_maximum_is_422(client, world):
    assert client.post("/jds/u1", json={"text": "Excel " * 6000}, headers=as_user("u1")).status_code == 422  # 36,000 chars


def test_JD_text_just_inside_the_maximum_is_accepted(client, world):
    text = ("Excel " + "x" * 29_994)[:30_000]
    assert len(text) == 30_000
    assert client.post("/jds/u1", json={"text": text}, headers=as_user("u1")).status_code == 201


def test_JD_text_at_the_minimum_length(client, world):
    text = "Excel skills are needed for this job.".ljust(40, ".")
    assert len(text) == 40
    assert client.post("/jds/u1", json={"text": text}, headers=as_user("u1")).status_code == 201
    assert client.post("/jds/u1", json={"text": text[:39]}, headers=as_user("u1")).status_code == 422


@pytest.mark.parametrize("field, value, status", [("title", "t" * 140, 201), ("title", "t" * 141, 422), ("company_name", "c" * 140, 201), ("company_name", "c" * 141, 422)])
def test_JD_optional_field_length_boundaries(client, world, field, value, status):
    assert client.post("/jds/u1", json={"text": JD_TEXT, field: value}, headers=as_user("u1")).status_code == status


def test_JD_extracts_known_skills_and_reports_coverage(client, world, db):
    from app.models import UserCapability

    db.add(UserCapability(user_id="u1", capability_id=world.excel.id))
    db.commit()
    jd = client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1")).json()
    assert {"Excel", "Power BI", "Consumer Insights"} <= {s["name"] for s in jd["skills"]}
    assert 0 < jd["coverage"] < 100
    have = {s["name"]: s["user_has_it"] for s in jd["skills"]}
    assert have["Excel"] is True and have["Power BI"] is False


def test_JD_title_defaults_to_first_line(client, world):
    jd = client.post("/jds/u1", json={"text": "Brand Manager, HUL\n" + JD_TEXT}, headers=as_user("u1")).json()
    assert jd["title"] == "Brand Manager, HUL"


def test_JD_long_first_line_title_is_clipped(client, world):
    jd = client.post("/jds/u1", json={"text": ("word " * 60) + "Excel " + JD_TEXT}, headers=as_user("u1")).json()
    assert len(jd["title"]) <= 81


def test_JD_unknown_role_or_company_link_is_rejected(client, world):
    assert client.post("/jds/u1", json={"text": JD_TEXT, "company_id": "nope"}, headers=as_user("u1")).status_code in {404, 422}
    assert client.post("/jds/u1", json={"text": JD_TEXT, "role_id": "nope"}, headers=as_user("u1")).status_code in {404, 422}


def test_JD_cap_on_saved_descriptions(client, world):
    from app.jds import MAX_JDS

    for _ in range(MAX_JDS):
        assert client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1")).status_code == 201
    assert client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1")).status_code == 409
    listed = client.get("/jds/u1", headers=as_user("u1")).json()
    client.delete(f"/jds/u1/{listed[0]['id']}", headers=as_user("u1"))
    assert client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1")).status_code == 201  # room again


def test_JD_isolation_between_users(client, world):
    jd = client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1")).json()
    assert client.get(f"/jds/u1/{jd['id']}", headers=as_user("u2")).status_code == 403
    assert client.get(f"/jds/u2/{jd['id']}", headers=as_user("u2")).status_code == 404  # own path, not their row
    assert client.delete(f"/jds/u2/{jd['id']}", headers=as_user("u2")).status_code == 404
    assert client.patch(f"/jds/u2/{jd['id']}", json={"title": "hax"}, headers=as_user("u2")).status_code == 404
    assert client.get(f"/jds/u1/{jd['id']}", headers=as_user("u1")).json()["title"] == jd["title"]


def test_JD_patch_delete_lifecycle(client, world):
    jd = client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1")).json()
    assert client.patch(f"/jds/u1/{jd['id']}", json={"title": "  Renamed  "}, headers=as_user("u1")).json()["title"] == "Renamed"
    assert client.delete(f"/jds/u1/{jd['id']}", headers=as_user("u1")).status_code == 204
    assert client.delete(f"/jds/u1/{jd['id']}", headers=as_user("u1")).status_code == 404
    assert client.get(f"/jds/u1/{jd['id']}", headers=as_user("u1")).status_code == 404


def test_JD_gaps_aggregate_across_saved_jobs(client, world):
    assert client.get("/jds/u1/gaps", headers=as_user("u1")).json() == {"jd_count": 0, "coverage": 0, "skills": []}
    client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1"))
    client.post("/jds/u1", json={"text": "Marketing role needing Excel every single day, plus reporting."}, headers=as_user("u1"))
    g = client.get("/jds/u1/gaps", headers=as_user("u1")).json()
    assert g["jd_count"] == 2
    excel = next(s for s in g["skills"] if s["name"] == "Excel")
    assert excel["jd_count"] == 2 and excel["jd_total"] == 2


@pytest.mark.parametrize("title", ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "'; DROP TABLE jds;--", "${7*7}", "{{7*7}}"])
def test_JD_hostile_titles_are_stored_as_inert_json_text(client, world, title):
    r = client.post("/jds/u1", json={"text": JD_TEXT, "title": title}, headers=as_user("u1"))
    assert r.status_code == 201 and r.headers["content-type"].startswith("application/json")
    assert r.json()["title"] == title  # returned verbatim; the web layer escapes it on render
    assert client.get("/jds/u1", headers=as_user("u1")).status_code == 200


# ---- PRIV: privacy rights ---------------------------------------------------------------------------------------


def test_PRIV_export_contains_only_own_data(client, world, articles):
    client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1"))
    e1 = client.get("/privacy/export", headers=as_user("u1"))
    assert e1.headers["content-disposition"].startswith("attachment") and e1.headers["cache-control"] == "no-store"
    data = e1.json()
    assert data["job_descriptions"] and "Brand Manager" in data["target_roles"]
    e2 = client.get("/privacy/export", headers=as_user("u2")).json()
    assert e2["job_descriptions"] == [] and e2["target_roles"] == []


def test_PRIV_export_never_includes_password_hash_or_token(client):
    signup(client, email="exp@example.com", password="export-secret-1")
    uid = client.get("/auth/me").json()["user_id"]
    text = client.get("/privacy/export", headers=as_user(uid)).text
    assert "scrypt$" not in text and "export-secret-1" not in text and "vantage_session" not in text


def test_PRIV_account_delete_requires_the_password(client):
    signup(client, email="del@example.com", password="right-password-1")
    uid = client.get("/auth/me").json()["user_id"]
    h = as_user(uid)
    assert client.request("DELETE", "/privacy/account", headers=h).status_code == 403
    assert client.request("DELETE", "/privacy/account", json={"password": "wrong-wrong"}, headers=h).status_code == 403
    assert client.request("DELETE", "/privacy/account", json={"password": ""}, headers=h).status_code == 403
    assert client.get("/auth/me").status_code == 200  # nothing erased by the failed attempts
    assert client.request("DELETE", "/privacy/account", json={"password": "right-password-1"}, headers=h).status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login", json={"email": "del@example.com", "password": "right-password-1"}).status_code == 401


def test_PRIV_delete_throttle_after_repeated_wrong_passwords(client):
    signup(client, email="delthr@example.com", password="right-password-1")
    uid = client.get("/auth/me").json()["user_id"]
    for _ in range(8):
        assert client.request("DELETE", "/privacy/account", json={"password": "nope-nope-1"}, headers=as_user(uid)).status_code == 403
    assert client.request("DELETE", "/privacy/account", json={"password": "right-password-1"}, headers=as_user(uid)).status_code == 429


def test_PRIV_guest_erasure_removes_everything(client, world, db, articles):
    from app.models import JD, UserInteraction, UserProfile

    client.post("/jds/u1", json={"text": JD_TEXT}, headers=as_user("u1"))
    client.post("/feed/u1/interaction", json={"article_id": articles[0].id, "action": "save"}, headers=as_user("u1"))
    assert client.request("DELETE", "/privacy/account", headers=as_user("u1")).status_code == 204
    db.expire_all()
    assert db.query(JD).filter_by(user_id="u1").count() == 0
    assert db.query(UserInteraction).filter_by(user_id="u1").count() == 0
    assert db.get(UserProfile, "u1") is None
    assert db.get(UserProfile, "u2") is not None  # someone else's data untouched


def test_PRIV_delete_is_repeatable_for_guests(client, world):
    assert client.request("DELETE", "/privacy/account", headers=as_user("u1")).status_code == 204
    assert client.request("DELETE", "/privacy/account", headers=as_user("u1")).status_code == 204


def test_PRIV_signup_records_consent_and_it_is_exported(client, monkeypatch):
    from app.legal import PRIVACY_VERSION, TERMS_VERSION

    monkeypatch.setenv("VANTAGE_REQUIRE_CONSENT", "1")
    consent = {"terms_version": TERMS_VERSION, "privacy_version": PRIVACY_VERSION, "over_18": True}
    r = signup(client, email="cons@example.com", consent=consent)
    assert r.status_code == 201
    consents = client.get("/privacy/export", headers=as_user(r.json()["user_id"])).json()["consents"]
    assert consents and consents[0]["terms_version"] == TERMS_VERSION


@pytest.mark.parametrize("kind", ["missing", "old-version", "under-18"])
def test_PRIV_signup_without_valid_consent_is_refused_when_required(client, monkeypatch, kind):
    from app.legal import PRIVACY_VERSION, TERMS_VERSION

    monkeypatch.setenv("VANTAGE_REQUIRE_CONSENT", "1")
    consents = {
        "missing": None,
        "old-version": {"terms_version": "1999-01-01", "privacy_version": "1999-01-01", "over_18": True},
        "under-18": {"terms_version": TERMS_VERSION, "privacy_version": PRIVACY_VERSION, "over_18": False},
    }
    extra = {"consent": consents[kind]} if consents[kind] else {}
    assert signup(client, email=uniq_email(), **extra).status_code in {400, 422}


# ---- PUB / OPS: public endpoints and generic HTTP behaviour --------------------------------------------------------


def test_PUB_pulse_shape_and_types(client, taxonomy):
    p = client.get("/public/pulse").json()
    for key in ("job_titles", "companies", "stories_total", "stories_today"):
        assert isinstance(p[key], int) and p[key] >= 0
    assert p["job_titles"] >= 2 and p["companies"] >= 5


def test_PUB_legal_reports_versions(client, monkeypatch):
    for k in ("VANTAGE_OPERATOR_NAME", "VANTAGE_CONTACT_EMAIL", "VANTAGE_GRIEVANCE_OFFICER", "VANTAGE_HOSTING_REGION"):
        monkeypatch.setenv(k, "")
    legal = client.get("/public/legal").json()
    assert legal["terms_version"] and legal["privacy_version"]


def test_PUB_legal_reflects_configured_operator(client, monkeypatch):
    monkeypatch.setenv("VANTAGE_CONTACT_EMAIL", "privacy@example.org")
    assert "privacy@example.org" in client.get("/public/legal").text


def test_OPS_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


@pytest.mark.parametrize("method, path", [("GET", "/nope"), ("GET", "/taxonomy/nope"), ("POST", "/taxonomy/roles"), ("DELETE", "/auth/me"), ("PUT", "/auth/login"), ("GET", "/auth/signup")])
def test_OPS_unknown_routes_and_wrong_methods_are_4xx(client, method, path):
    assert client.request(method, path).status_code in {404, 405}


def test_OPS_errors_never_leak_a_stack_trace(client, taxonomy):
    for r in (client.get("/taxonomy/roles/nope"), client.post("/auth/login", json={"email": "x@y.zz", "password": "abcdefgh"}), client.get("/taxonomy/roles", params={"limit": "x"})):
        assert "Traceback" not in r.text and 'File "' not in r.text


def test_OPS_openapi_lists_every_route_group(client):
    paths = client.get("/openapi.json").json()["paths"]
    for prefix in ("/auth/", "/taxonomy/", "/feed/", "/jds/", "/privacy/", "/public/", "/profile/", "/onboarding"):
        assert any(p.startswith(prefix) for p in paths), prefix


def test_OPS_large_request_body_is_handled_not_crashed(client, world):
    r = client.post("/jds/u1", json={"text": "Excel " * 200_000}, headers=as_user("u1"))  # 1.2 MB
    assert r.status_code in {413, 422}


@pytest.mark.parametrize("origin", ["https://evil.example", "null"])
def test_OPS_cors_does_not_reflect_arbitrary_origins(client, origin):
    r = client.get("/taxonomy/domains", headers={"Origin": origin})
    assert r.headers.get("access-control-allow-origin") not in {"*", origin}


def test_FEED_untagged_story_is_not_shown(client, world, articles):
    urls = {i["url"] for i in client.get("/feed/u1", params={"limit": 50}, headers=as_user("u1")).json()["items"]}
    assert "https://example.com/gossip" not in urls
    assert {"https://example.com/a0", "https://example.com/a1", "https://example.com/a2"} <= urls


def test_FEED_near_identical_headlines_from_two_outlets_are_one_story(client, db, world):
    from datetime import datetime, timezone

    from app.ingest import FeedEntry, ingest_entries

    now = datetime.now(timezone.utc)
    for name in ("Wire One", "Wire Two"):
        src = Source(name=name, feed_url=f"https://{name.replace(' ', '')}.test/rss", authority=3)
        db.add(src)
        db.commit()
        ingest_entries(db, src, [FeedEntry("HUL launches monsoon soap campaign", f"https://{name.replace(' ', '')}.test/hul", "HUL launches a campaign. It targets rural buyers.", now)])
    items = client.get("/feed/u1", params={"limit": 50}, headers=as_user("u1")).json()["items"]
    assert len(items) == 1 and len(items[0]["also_covered_by"]) == 1
