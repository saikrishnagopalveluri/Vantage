from sqlalchemy import select

from app.models import ProfileEvent, User, UserProfile, UserTargetCompany
from tests.conftest import as_user


def onboard(client, user="new", **body):
    return client.post("/onboarding", json=body, headers=as_user(user))


def test_student_onboarding_creates_targeting_profile(client, taxonomy):
    res = onboard(
        client,
        target_role_ids=[taxonomy.bm.id],
        target_company_ids=[taxonomy.hul.id, taxonomy.itc.id],
        capability_ids=[taxonomy.excel.id, taxonomy.insights.id],
    )
    assert res.status_code == 201
    body = res.json()
    assert body["user_id"] == "new"
    assert body["profile_status"] == "targeting"
    assert body["current_role"] is None and body["placed_at"] is None
    assert [r["title"] for r in body["target_roles"]] == ["Brand Manager"]
    assert [c["name"] for c in body["target_companies"]] == ["HUL", "ITC"]
    assert [(c["name"], c["kind"]) for c in body["capabilities"]] == [
        ("Consumer Insights", "skill"),
        ("Excel", "tool"),
    ]


def test_student_who_does_not_know_their_role_can_onboard_empty(client, taxonomy):
    res = onboard(client)
    assert res.status_code == 201
    assert res.json()["target_roles"] == []


def test_professional_onboarding_starts_placed_without_placed_at(client, taxonomy):
    res = onboard(client, current={"company_id": taxonomy.hul.id, "role_id": taxonomy.bm.id})
    assert res.status_code == 201
    body = res.json()
    assert body["profile_status"] == "placed"
    assert body["current_company"]["name"] == "HUL"
    assert body["current_industry"]["name"] == "FMCG"
    assert body["placed_at"] is None  # never placed through Vantage


def test_professional_job_change_does_not_invent_placed_at(client, taxonomy, db):
    onboard(client, current={"company_id": taxonomy.hul.id, "role_id": taxonomy.bm.id})
    res = client.post(
        "/profile/new/placement",
        json={"company_id": taxonomy.itc.id, "role_id": taxonomy.bm.id},
        headers=as_user("new"),
    )
    assert res.json()["event_type"] == "role_changed"
    assert res.json()["placed_at"] is None
    db.expire_all()
    assert db.get(UserProfile, "new").placed_at is None
    assert [e.event_type for e in db.scalars(select(ProfileEvent))] == ["role_changed"]


def test_current_industry_required_when_company_has_none(client, taxonomy):
    body = {"company_id": taxonomy.nameless_industry.id, "role_id": taxonomy.bm.id}
    assert onboard(client, current=body).status_code == 422
    ok = onboard(client, current={**body, "industry_id": taxonomy.ecom.id})
    assert ok.status_code == 201


def test_duplicate_ids_are_collapsed(client, taxonomy):
    res = onboard(client, target_company_ids=[taxonomy.hul.id, taxonomy.hul.id])
    assert res.status_code == 201
    assert len(res.json()["target_companies"]) == 1


def test_second_onboarding_conflicts_and_changes_nothing(client, taxonomy, db):
    onboard(client, target_company_ids=[taxonomy.hul.id])
    again = onboard(client, target_company_ids=[taxonomy.itc.id])
    assert again.status_code == 409
    db.expire_all()
    [target] = db.scalars(select(UserTargetCompany)).all()
    assert target.company_id == taxonomy.hul.id


def test_unknown_ids_are_reported_and_nothing_is_created(client, taxonomy, db):
    res = onboard(
        client,
        target_role_ids=["nope"],
        target_company_ids=[taxonomy.hul.id, "ghost"],
        current={"company_id": "x", "role_id": taxonomy.bm.id},
    )
    assert res.status_code == 422
    assert res.json()["detail"]["unknown_ids"] == {
        "target_role_ids": ["nope"],
        "target_company_ids": ["ghost"],
        "current.company_id": ["x"],
    }
    db.expire_all()
    assert db.get(User, "new") is None


def test_requires_identity_header(client, taxonomy):
    assert client.post("/onboarding", json={}).status_code == 401


def test_get_profile_round_trips_and_is_private(client, taxonomy):
    onboard(client, target_role_ids=[taxonomy.bm.id])
    mine = client.get("/profile/new", headers=as_user("new"))
    assert mine.status_code == 200
    assert mine.json()["target_roles"][0]["title"] == "Brand Manager"
    assert client.get("/profile/new", headers=as_user("someone-else")).status_code == 403
    assert client.get("/profile/ghost", headers=as_user("ghost")).status_code == 404


def test_targets_are_replaced_wholesale(client, world):
    res = client.put(
        "/profile/u1/targets",
        json={
            "target_role_ids": [world.dmm.id],
            "target_company_ids": [world.amazon.id],
            "capability_ids": [world.powerbi.id, world.powerbi.id],
        },
        headers=as_user("u1"),
    )
    assert res.status_code == 200
    body = res.json()
    assert [r["title"] for r in body["target_roles"]] == ["Digital Marketing Manager"]
    assert [c["name"] for c in body["target_companies"]] == ["Amazon"]
    assert [c["name"] for c in body["capabilities"]] == ["Power BI"]
    assert client.get("/profile/u1", headers=as_user("u1")).json() == body


def test_empty_targets_clear_everything(client, world):
    res = client.put("/profile/u1/targets", json={}, headers=as_user("u1"))
    assert res.json()["target_roles"] == [] and res.json()["target_companies"] == []


def test_targets_update_validates_before_changing_anything(client, world):
    bad = client.put(
        "/profile/u1/targets",
        json={"target_role_ids": [world.dmm.id], "target_company_ids": ["ghost"]},
        headers=as_user("u1"),
    )
    assert bad.status_code == 422
    assert bad.json()["detail"]["unknown_ids"] == {"target_company_ids": ["ghost"]}
    kept = client.get("/profile/u1", headers=as_user("u1")).json()
    assert [r["title"] for r in kept["target_roles"]] == ["Brand Manager"]


def test_targets_update_is_private(client, world):
    assert client.put("/profile/u1/targets", json={}).status_code == 401
    assert client.put("/profile/u1/targets", json={}, headers=as_user("u2")).status_code == 403
    assert client.put("/profile/ghost/targets", json={}, headers=as_user("ghost")).status_code == 404
