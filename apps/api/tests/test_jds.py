from app.jds import MAX_JDS, extract_skills
from app.models import Capability, CapabilityKind, UserCapability
from tests.conftest import as_user

JD_ONE = """Brand Manager, Consumer Foods
We are hiring a brand manager. You will build the brand plan, work with Consumer Insights,
and report on results in Power BI. Strong Excel skills and clear communication are expected."""

JD_TWO = "Analyst role. Daily work in Excel and Power BI, with weekly reporting to leadership and vendors."


def add(client, text=JD_ONE, user="u1", **extra):
    return client.post(f"/jds/{user}", json={"text": text, **extra}, headers=as_user(user))


def test_extraction_is_grounded_in_the_text(db, world):
    db.add(Capability(name="Communication", kind=CapabilityKind.SKILL, taggable=False))
    db.commit()
    names = {c.name for c in extract_skills(db, JD_ONE)}
    assert names == {"Excel", "Power BI", "Consumer Insights", "Communication"}  # generic skills match any case
    assert extract_skills(db, "We need people who excel at teamwork.") == []  # 'excel' the verb is not Excel


def test_add_a_jd_returns_skills_with_what_the_user_has(client, db, world):
    db.add(UserCapability(user_id="u1", capability_id=world.excel.id))
    db.commit()
    res = add(client, company_id=world.hul.id, role_id=world.bm.id)
    assert res.status_code == 201, res.text
    jd = res.json()
    assert jd["title"] == "Brand Manager, Consumer Foods"
    assert jd["company"]["name"] == "HUL" and jd["role"]["title"] == "Brand Manager"
    skills = {s["name"]: s["user_has_it"] for s in jd["skills"]}
    assert skills == {"Excel": True, "Power BI": False, "Consumer Insights": False}
    assert jd["skills"][-1]["name"] == "Excel"  # the ones you lack come first
    assert jd["coverage"] == 33


def test_several_jds_and_the_gaps_across_them(client, db, world):
    db.add(UserCapability(user_id="u1", capability_id=world.excel.id))
    db.commit()
    add(client)
    add(client, JD_TWO, title="Analyst, any company", company_name="Some Startup")
    listing = client.get("/jds/u1", headers=as_user("u1")).json()
    assert [j["title"] for j in listing] == ["Analyst, any company", "Brand Manager, Consumer Foods"]
    gaps = client.get("/jds/u1/gaps", headers=as_user("u1")).json()
    assert gaps["jd_count"] == 2
    top = gaps["skills"][0]
    assert top["name"] == "Power BI" and top["jd_count"] == 2 and top["user_has_it"] is False
    assert [g["name"] for g in gaps["skills"]] == ["Power BI", "Consumer Insights", "Excel"]
    assert gaps["coverage"] == 40  # 2 of 5 requirements are already covered


def test_edit_link_and_delete(client, world):
    jd_id = add(client).json()["id"]
    res = client.patch(
        f"/jds/u1/{jd_id}", json={"company_id": world.itc.id, "title": " Renamed "}, headers=as_user("u1")
    )
    assert res.json()["company"]["name"] == "ITC" and res.json()["title"] == "Renamed"
    assert client.patch(f"/jds/u1/{jd_id}", json={"role_id": "nope"}, headers=as_user("u1")).status_code == 422
    assert client.delete(f"/jds/u1/{jd_id}", headers=as_user("u1")).status_code == 204
    assert client.get(f"/jds/u1/{jd_id}", headers=as_user("u1")).status_code == 404
    assert client.get("/jds/u1", headers=as_user("u1")).json() == []


def test_text_without_known_skills_is_refused_kindly(client, world):
    res = add(client, "This posting mentions nothing we have heard of, only long, plain sentences about a job.")
    assert res.status_code == 422 and "couldn't find any skills" in res.json()["detail"]


def test_jd_limits_and_ownership(client, world, monkeypatch):
    assert add(client, "too short").status_code == 422
    assert add(client, company_id="nope").status_code == 422
    first = add(client).json()["id"]
    assert client.get(f"/jds/u1/{first}", headers=as_user("u2")).status_code == 403
    assert client.get("/jds/u1").status_code == 401
    assert client.get("/jds/ghost", headers=as_user("ghost")).status_code == 404
    monkeypatch.setattr("app.routers.jds.MAX_JDS", 2)
    add(client)
    res = add(client)
    assert res.status_code == 409 and "up to 2" in res.json()["detail"]
    assert MAX_JDS == 30
