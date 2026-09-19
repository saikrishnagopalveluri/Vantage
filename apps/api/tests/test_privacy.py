import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.legal import PRIVACY_VERSION, TERMS_VERSION
from app.main import app
from app.models import (
    JD,
    Account,
    Article,
    Base,
    Consent,
    InteractionAction,
    JDCapability,
    Source,
    User,
    UserInteraction,
)
from app.routers.privacy import erase
from tests.conftest import as_user

GOOD = {"terms_version": TERMS_VERSION, "privacy_version": PRIVACY_VERSION, "over_18": True}
CREDS = {"email": "asha@example.com", "password": "correct horse battery"}
EMPTY = {"domain_ids": [], "target_role_ids": [], "target_company_ids": [], "capability_ids": []}


def signup(client, consent=GOOD):
    return client.post("/auth/signup", json={**CREDS, "consent": consent})


def test_signup_needs_current_consent_and_an_adult(client, monkeypatch):
    monkeypatch.setenv("VANTAGE_REQUIRE_CONSENT", "1")
    assert signup(client, consent=None).status_code == 422
    assert signup(client, consent={**GOOD, "over_18": False}).status_code == 422
    stale = signup(client, consent={**GOOD, "terms_version": "1999-01-01"})
    assert stale.status_code == 422 and "just changed" in stale.json()["detail"]
    assert client.get("/auth/me").status_code == 401  # nothing was created by the failed tries
    assert signup(client).status_code == 201


def test_the_consent_record_is_stored_with_versions(client, session_factory, monkeypatch):
    monkeypatch.setenv("VANTAGE_REQUIRE_CONSENT", "1")
    user_id = signup(client).json()["user_id"]
    with session_factory() as db:
        row = db.query(Consent).one()
        assert (row.user_id, row.terms_version, row.privacy_version, row.over_18, row.source) == (
            user_id, TERMS_VERSION, PRIVACY_VERSION, True, "signup",
        )


def test_guests_agree_during_onboarding_and_accounts_do_not_repeat_it(client, session_factory, monkeypatch):
    monkeypatch.setenv("VANTAGE_REQUIRE_CONSENT", "1")
    assert client.post("/onboarding", json=EMPTY, headers=as_user("g1")).status_code == 422
    ok = client.post("/onboarding", json={**EMPTY, "consent": GOOD}, headers=as_user("g1"))
    assert ok.status_code == 201
    with session_factory() as db:
        assert db.query(Consent).filter_by(user_id="g1", source="guest").count() == 1

    account = TestClient(app)
    user_id = signup(account).json()["user_id"]
    assert account.post("/onboarding", json=EMPTY, headers={"X-User-Id": user_id}).status_code == 201
    with session_factory() as db:
        assert db.query(Consent).filter_by(user_id=user_id).count() == 1  # only the signup one


def test_public_legal_info_lists_versions_and_only_the_contacts_that_are_set(client, monkeypatch):
    monkeypatch.setenv("VANTAGE_CONTACT_EMAIL", "privacy@example.org")
    body = client.get("/public/legal").json()
    assert body["terms_version"] == TERMS_VERSION and body["privacy_version"] == PRIVACY_VERSION
    assert body["contact_email"] == "privacy@example.org" and body["grievance_email"] == "privacy@example.org"
    assert body["operator_name"] is None  # never invented


def add_story_activity(db, world, user_id):
    source = Source(name="S", feed_url="https://f.test", authority=3)
    db.add(source)
    db.flush()
    article = Article(source_id=source.id, title="Story", url="https://x.test/s", published_at=datetime.now(timezone.utc))
    db.add(article)
    db.flush()
    db.add(UserInteraction(user_id=user_id, article_id=article.id, action=InteractionAction.SAVED))
    jd = JD(user_id=user_id, title="My JD", raw_text="Excel required", company_id=world.hul.id)
    db.add(jd)
    db.flush()
    db.add(JDCapability(jd_id=jd.id, capability_id=world.excel.id))
    db.commit()


def test_export_contains_everything_in_words_and_never_the_password(client, db, world):
    user_id = signup(client).json()["user_id"]
    body = {**EMPTY, "target_role_ids": [world.bm.id], "target_company_ids": [world.hul.id], "capability_ids": [world.excel.id]}
    assert client.post("/onboarding", json=body, headers={"X-User-Id": user_id}).status_code == 201
    add_story_activity(db, world, user_id)

    res = client.get("/privacy/export")
    assert res.status_code == 200 and "attachment" in res.headers["content-disposition"]
    data = res.json()
    assert data["account"]["email"] == "asha@example.com"
    assert data["target_roles"] == ["Brand Manager"] and data["target_companies"] == ["HUL"]
    assert data["skills_and_tools_you_have"] == ["Excel"]
    assert data["story_activity"][0]["story"] == "Story" and data["story_activity"][0]["action"] == "saved"
    assert data["job_descriptions"][0]["text"] == "Excel required" and data["job_descriptions"][0]["skills_found"] == ["Excel"]
    assert "scrypt" not in json.dumps(data)


def test_export_needs_a_caller():
    assert TestClient(app).get("/privacy/export").status_code == 401


def test_deleting_an_account_needs_the_password_and_removes_everything(client, db, world, session_factory):
    user_id = signup(client).json()["user_id"]
    body = {**EMPTY, "target_role_ids": [world.bm.id], "capability_ids": [world.excel.id]}
    client.post("/onboarding", json=body, headers={"X-User-Id": user_id})
    add_story_activity(db, world, user_id)
    headers = {"X-User-Id": user_id}

    assert client.request("DELETE", "/privacy/account", headers=headers).status_code == 403
    assert client.request("DELETE", "/privacy/account", json={"password": "wrong wrong"}, headers=headers).status_code == 403
    assert db.get(User, user_id) is not None

    assert client.request("DELETE", "/privacy/account", json={"password": CREDS["password"]}, headers=headers).status_code == 204
    with session_factory() as fresh:
        assert fresh.get(User, user_id) is None and fresh.get(Account, user_id) is None
        for table in Base.metadata.sorted_tables:
            if "user_id" in table.c:
                assert fresh.execute(table.select().where(table.c.user_id == user_id)).first() is None, table.name
        assert fresh.query(JDCapability).count() == 0
    assert client.get("/auth/me").status_code == 401  # the cookie is gone too


def test_deleting_a_guest_needs_no_password_and_only_touches_that_guest(client, db, world):
    assert client.request("DELETE", "/privacy/account", headers=as_user("u1")).status_code == 204
    db.expire_all()
    assert db.get(User, "u1") is None and db.get(User, "u2") is not None


def test_every_table_that_holds_a_user_id_is_covered_by_erasure():
    tables = {t.name for t in Base.metadata.sorted_tables if "user_id" in t.c}
    assert {"user_profiles", "user_interactions", "jds", "profile_events", "consents", "accounts"} <= tables
    assert "user_id" in (erase.__doc__ or "")
