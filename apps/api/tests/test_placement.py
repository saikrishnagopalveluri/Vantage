from datetime import datetime

from sqlalchemy import select

from app.models import ProfileEvent, UserProfile, UserTargetCompany, UserTargetRole
from tests.conftest import as_user


def place(client, world, company=None, role=None, user="u1", **extra):
    body = {"company_id": (company or world.hul).id, "role_id": (role or world.bm).id, **extra}
    return client.post(f"/profile/{user}/placement", json=body, headers=as_user(user))


def events(db, user="u1"):
    db.expire_all()
    return list(db.scalars(select(ProfileEvent).where(ProfileEvent.user_id == user)))


def test_first_call_is_a_placement_and_infers_industry(client, world, db):
    res = place(client, world)
    assert res.status_code == 200
    body = res.json()
    assert body["event_type"] == "placed"
    assert body["profile_status"] == "placed"
    assert body["current_company"]["name"] == "HUL"
    assert body["current_role"]["title"] == "Brand Manager"
    assert body["current_industry"]["name"] == "FMCG"
    assert body["placed_at"] is not None and body["placed_at"].endswith(("Z", "+00:00"))
    [event] = events(db)
    assert event.event_type == "placed"
    assert event.payload["new_company_id"] == world.hul.id
    assert event.payload["old_company_id"] is None


def test_placement_keeps_targets_by_default(client, world, db):
    place(client, world)
    db.expire_all()
    assert db.scalars(select(UserTargetRole)).all()
    assert len(db.scalars(select(UserTargetCompany)).all()) == 4


def test_clear_targets_removes_them(client, world, db):
    place(client, world, clear_targets=True)
    db.expire_all()
    assert db.scalars(select(UserTargetRole)).all() == []
    assert db.scalars(select(UserTargetCompany)).all() == []


def test_placed_on_backdates_placed_at(client, world):
    body = place(client, world, placed_on="2026-06-14").json()
    assert body["placed_at"].startswith("2026-06-14T00:00:00")


def test_job_change_logs_role_changed_and_keeps_placed_at(client, world, db):
    first = place(client, world).json()
    second = place(client, world, company=world.itc).json()
    assert second["event_type"] == "role_changed"
    assert second["current_company"]["name"] == "ITC"
    assert second["placed_at"] == first["placed_at"]
    assert datetime.fromisoformat(second["current_role_started_at"]) >= datetime.fromisoformat(
        first["current_role_started_at"]
    )
    assert sorted(e.event_type for e in events(db)) == ["placed", "role_changed"]
    changed = next(e for e in events(db) if e.event_type == "role_changed")
    assert changed.payload["old_company_id"] == world.hul.id
    assert changed.payload["new_company_id"] == world.itc.id


def test_repeating_the_same_call_is_a_noop(client, world, db):
    place(client, world)
    again = place(client, world, clear_targets=True)
    assert again.json()["event_type"] == "unchanged"
    assert len(events(db)) == 1
    db.expire_all()
    assert db.scalars(select(UserTargetRole)).all()  # clear_targets skipped on no-op


def test_industry_required_when_company_has_none(client, world):
    res = place(client, world, company=world.nameless_industry)
    assert res.status_code == 422
    ok = place(client, world, company=world.nameless_industry, industry_id=world.ecom.id)
    assert ok.status_code == 200
    assert ok.json()["current_industry"]["name"] == "E-commerce"


def test_explicit_industry_overrides_company_default(client, world):
    body = place(client, world, industry_id=world.ecom.id).json()
    assert body["current_industry"]["name"] == "E-commerce"


def test_auth_and_not_found(client, world):
    no_header = client.post("/profile/u1/placement", json={"company_id": "x", "role_id": "y"})
    assert no_header.status_code == 401
    other = client.post(
        "/profile/u1/placement",
        json={"company_id": world.hul.id, "role_id": world.bm.id},
        headers=as_user("u2"),
    )
    assert other.status_code == 403
    assert client.post(
        "/profile/u1/placement",
        json={"company_id": "nope", "role_id": world.bm.id},
        headers=as_user("u1"),
    ).status_code == 404
    assert client.post(
        "/profile/u1/placement",
        json={"company_id": world.hul.id, "role_id": "nope"},
        headers=as_user("u1"),
    ).status_code == 404
    assert client.post(
        "/profile/ghost/placement",
        json={"company_id": world.hul.id, "role_id": world.bm.id},
        headers=as_user("ghost"),
    ).status_code == 404


def test_failed_request_writes_nothing(client, world, db):
    place(client, world, company=world.nameless_industry)  # 422
    db.expire_all()
    profile = db.get(UserProfile, "u1")
    assert profile.profile_status.value == "targeting"
    assert events(db) == []
