"""Smoke and security checks against a deployed stack. Skipped unless a URL is given.

    VANTAGE_LIVE_WEB=https://vantage-web-vert.vercel.app pytest tests/test_live_smoke.py
    VANTAGE_LIVE_WRITE=1 also runs the one test that creates a throwaway account and deletes it.

Everything else is read-only. The web URL is the public entry point, so /api/... goes through the
same proxy a browser uses.
"""

import os
import uuid

import httpx
import pytest

WEB = (os.getenv("VANTAGE_LIVE_WEB") or "").rstrip("/")
API = (os.getenv("VANTAGE_LIVE_API") or "").rstrip("/")

pytestmark = pytest.mark.skipif(not WEB, reason="set VANTAGE_LIVE_WEB to run the live smoke tests")


@pytest.fixture(scope="module")
def http():
    with httpx.Client(base_url=WEB, timeout=60, follow_redirects=False) as c:
        yield c


# ---- pages ------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/login", "/terms", "/privacy", "/offline"])
def test_LIVE_public_pages_load(http, path):
    r = http.get(path)
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("path", ["/feed", "/explore", "/career", "/saved", "/profile", "/onboarding"])
def test_LIVE_app_pages_respond_without_a_server_error(http, path):
    assert http.get(path).status_code < 500  # signed-out visitors may be redirected client-side


@pytest.mark.parametrize("path", ["/nope", "/terms/nope", "/explore/roles/not-a-real-id-xyz"])
def test_LIVE_unknown_pages_do_not_500(http, path):
    assert http.get(path).status_code in {200, 404}


@pytest.mark.parametrize("path, kind", [("/manifest.webmanifest", "json"), ("/sw.js", "javascript"), ("/icon.svg", "svg")])
def test_LIVE_pwa_assets(http, path, kind):
    r = http.get(path)
    if r.status_code == 404 and path == "/manifest.webmanifest":
        pytest.skip("manifest served from a different path")
    assert r.status_code == 200 and kind in r.headers["content-type"]


def test_LIVE_service_worker_is_never_cached(http):
    assert "no-store" in http.get("/sw.js").headers["cache-control"]


def test_LIVE_security_headers_on_pages(http):
    h = http.get("/login").headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"
    csp = h["content-security-policy"]
    assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp and "default-src 'self'" in csp
    assert "unsafe-eval" not in csp


def test_LIVE_https_only_cookie_and_no_server_banner(http):
    h = http.get("/").headers
    assert "x-powered-by" not in {k.lower() for k in h}


# ---- API through the proxy ---------------------------------------------------------------------------


def test_LIVE_health_through_proxy(http):
    r = http.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_LIVE_pulse_numbers_are_at_scale(http):
    p = http.get("/api/public/pulse").json()
    assert p["job_titles"] >= 20_000 and p["companies"] >= 15_000


def test_LIVE_domains_and_industries(http):
    assert len(http.get("/api/taxonomy/domains").json()) >= 20
    assert len(http.get("/api/taxonomy/industries").json()) >= 10


@pytest.mark.parametrize("q", ["marketing", "finance", "brand", "consultant", "sales", "analytics", "operations", "product"])
def test_LIVE_management_role_searches_return_results(http, q):
    assert http.get("/api/taxonomy/roles", params={"q": q, "limit": 10}).json()


@pytest.mark.parametrize("q", ["Hindustan", "Deloitte", "Tata", "Amazon", "Accenture", "McKinsey"])
def test_LIVE_well_known_company_searches(http, q):
    assert http.get("/api/taxonomy/companies", params={"q": q, "limit": 10}).json()


@pytest.mark.parametrize("q", ["Excel", "SQL", "Power BI", "Negotiation", "Financial Modeling", "financial model"])
def test_LIVE_skill_searches(http, q):
    assert http.get("/api/taxonomy/capabilities", params={"q": q, "limit": 10}).json()


@pytest.mark.xfail(strict=True, reason="FINDING: search has no spelling variants or abbreviations, so UK/India spellings and acronyms find nothing")
@pytest.mark.parametrize("q", ["modelling", "DCF", "MS Excel"])
def test_LIVE_skill_search_spelling_variants_and_acronyms(http, q):
    assert http.get("/api/taxonomy/capabilities", params={"q": q, "limit": 10}).json()


def test_LIVE_mba_filter_puts_management_roles_first(http):
    roles = http.get("/api/taxonomy/roles", params={"mba": "true", "limit": 50}).json()
    assert len(roles) >= 20 and all(r["mba"] for r in roles)


def test_LIVE_search_endpoint(http):
    r = http.get("/api/taxonomy/search", params={"q": "brand"}).json()
    assert r["roles"] and set(r) == {"query", "roles", "companies", "capabilities", "articles"}


def test_LIVE_role_detail_round_trip(http):
    first = http.get("/api/taxonomy/roles", params={"q": "Brand Manager", "limit": 1}).json()[0]
    d = http.get(f"/api/taxonomy/roles/{first['id']}").json()
    assert d["title"] and isinstance(d["capabilities"], list)


@pytest.mark.parametrize(
    "path, params, status",
    [("/api/taxonomy/roles", {"limit": 0}, 422), ("/api/taxonomy/roles", {"limit": 501}, 422), ("/api/taxonomy/search", {"q": "a"}, 422),
     ("/api/taxonomy/roles/not-real", {}, 404), ("/api/nope", {}, 404), ("/api/auth/me", {}, 401), ("/api/feed/someone", {}, 401)],
)
def test_LIVE_error_paths(http, path, params, status):
    r = http.get(path, params=params)
    assert r.status_code == status
    assert "Traceback" not in r.text


def test_LIVE_login_with_unknown_account_is_401_and_generic(http):
    r = http.post("/api/auth/login", json={"email": f"nobody-{uuid.uuid4().hex[:8]}@example.com", "password": "wrong-password-1"})
    assert r.status_code == 401 and "no such" not in r.text.lower()


def test_LIVE_signup_rejects_bad_input(http):
    assert http.post("/api/auth/signup", json={"email": "bad", "password": "long-enough-1"}).status_code == 422
    assert http.post("/api/auth/signup", json={"email": "ok@example.com", "password": "short"}).status_code == 422


def test_LIVE_signup_needs_consent(http):
    r = http.post("/api/auth/signup", json={"email": f"noconsent-{uuid.uuid4().hex[:8]}@example.com", "password": "long-enough-1"})
    assert r.status_code in {400, 422}


def test_LIVE_legal_endpoint_exposes_versions(http):
    legal = http.get("/api/public/legal").json()
    assert legal["terms_version"] and legal["privacy_version"]


def test_LIVE_secret_files_are_not_served(http):
    for path in ("/.env", "/.env.local", "/.git/config", "/api/.env", "/vantage.db", "/apps/api/.env.vercel"):
        r = http.get(path)
        assert r.status_code in {403, 404} or "DATABASE_URL" not in r.text, path


def test_LIVE_concurrent_reads_stay_healthy(http):
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(lambda _: http.get("/api/taxonomy/domains").status_code, range(30)))
    assert codes.count(200) == 30


def test_LIVE_response_times_are_reasonable(http):
    import time

    http.get("/api/health")  # warm the function
    start = time.perf_counter()
    http.get("/api/taxonomy/domains")
    assert time.perf_counter() - start < 5


# ---- write path (opt-in) ------------------------------------------------------------------------------------


@pytest.mark.skipif(os.getenv("VANTAGE_LIVE_WRITE") != "1", reason="set VANTAGE_LIVE_WRITE=1 to create and delete a throwaway account")
def test_LIVE_full_account_lifecycle(http):
    legal = http.get("/api/public/legal").json()
    consent = {"terms_version": legal["terms_version"], "privacy_version": legal["privacy_version"], "over_18": True}
    email, password = f"qa-{uuid.uuid4().hex[:10]}@example.com", "qa-throwaway-pass-1"
    with httpx.Client(base_url=WEB, timeout=60) as c:
        r = c.post("/api/auth/signup", json={"email": email, "password": password, "consent": consent})
        assert r.status_code == 201, r.text
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
        uid = r.json()["user_id"]
        h = {"X-User-Id": uid}
        try:
            assert c.get("/api/auth/me").json()["email"] == email
            assert c.post("/api/onboarding", json={}, headers=h).status_code == 201
            assert c.post("/api/onboarding", json={}, headers=h).status_code == 409
            assert c.post("/api/onboarding", json={}).status_code == 403  # CSRF: cookie without the header
            assert c.get(f"/api/feed/{uid}", headers=h).status_code == 200
            assert c.get("/api/privacy/export", headers=h).json()["consents"]
            assert c.post("/api/auth/logout").status_code == 204
            assert c.post("/api/auth/login", json={"email": email, "password": "wrong-password-1"}).status_code == 401
            assert c.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200
        finally:
            c.request("DELETE", "/api/privacy/account", json={"password": password}, headers=h)
        assert c.get("/api/auth/me").status_code == 401
        assert c.post("/api/auth/login", json={"email": email, "password": password}).status_code == 401
