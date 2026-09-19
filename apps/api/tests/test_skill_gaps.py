from app.models import (
    JD,
    CompanyRoleCapability,
    JDCapability,
    RoleCapability,
    UserCapability,
)
from tests.conftest import as_user


def gaps(client, user="u1", **params):
    res = client.get(f"/profile/{user}/skill-gaps", params=params, headers=as_user(user))
    assert res.status_code == 200, res.text
    return res.json()


def only_role(body):
    [role] = body["target_roles"]
    return role


def by_name(role):
    return {c["name"]: c for c in role["capabilities"]}


def test_role_taxonomy_fallback_excludes_non_hiring_companies(client, world, db):
    db.add_all(
        [
            RoleCapability(role_id=world.bm.id, capability_id=world.excel.id),
            RoleCapability(role_id=world.bm.id, capability_id=world.insights.id),
            UserCapability(user_id="u1", capability_id=world.excel.id),
        ]
    )
    db.commit()
    role = only_role(gaps(client))
    # Amazon targets but doesn't hire Brand Managers -> not in the denominator.
    assert role["companies_considered"] == 3
    assert role["companies_with_no_data"] == 0
    caps = by_name(role)
    assert caps["Excel"]["required_by_count"] == 3
    assert caps["Excel"]["required_by_total"] == 3
    assert caps["Excel"]["gap_ratio"] == 1.0
    assert caps["Excel"]["user_has_it"] is True
    assert caps["Excel"]["kind"] == "tool"
    assert caps["Excel"]["source"] == "taxonomy"
    assert caps["Consumer Insights"]["user_has_it"] is False
    assert caps["Consumer Insights"]["kind"] == "skill"


def test_company_specific_requirements_override_role_taxonomy(client, world, db):
    db.add(RoleCapability(role_id=world.bm.id, capability_id=world.excel.id))
    db.add(
        CompanyRoleCapability(
            company_id=world.hul.id, role_id=world.bm.id, capability_id=world.powerbi.id
        )
    )
    db.commit()
    caps = by_name(only_role(gaps(client)))
    # HUL's own list replaces the generic one, so only ITC + Nestle need Excel.
    assert caps["Excel"]["required_by_count"] == 2
    assert caps["Power BI"]["required_by_count"] == 1
    assert caps["Power BI"]["source"] == "company"
    assert caps["Excel"]["source"] == "taxonomy"


def test_jd_takes_precedence_and_marks_source(client, world, db):
    db.add(RoleCapability(role_id=world.bm.id, capability_id=world.excel.id))
    jd = JD(user_id="u1", company_id=world.itc.id, role_id=world.bm.id)
    db.add(jd)
    db.flush()
    db.add(JDCapability(jd_id=jd.id, capability_id=world.powerbi.id))
    db.commit()
    caps = by_name(only_role(gaps(client)))
    assert caps["Excel"]["required_by_count"] == 2  # ITC's JD replaced the generic list
    assert caps["Power BI"]["required_by_count"] == 1
    assert caps["Power BI"]["source"] == "jd"


def test_a_jd_belonging_to_another_user_is_ignored(client, world, db):
    db.add(RoleCapability(role_id=world.bm.id, capability_id=world.excel.id))
    jd = JD(user_id="u2", company_id=world.itc.id, role_id=world.bm.id)
    db.add(jd)
    db.flush()
    db.add(JDCapability(jd_id=jd.id, capability_id=world.powerbi.id))
    db.commit()
    caps = by_name(only_role(gaps(client)))
    assert "Power BI" not in caps
    assert caps["Excel"]["required_by_count"] == 3


def test_companies_without_any_data_are_counted_not_hidden(client, world, db):
    role = only_role(gaps(client))  # no capabilities seeded anywhere
    assert role["companies_considered"] == 0
    assert role["companies_with_no_data"] == 3
    assert role["capabilities"] == []


def test_partial_coverage_reports_denominator_honestly(client, world, db):
    db.add(
        CompanyRoleCapability(
            company_id=world.hul.id, role_id=world.bm.id, capability_id=world.excel.id
        )
    )
    db.commit()
    role = only_role(gaps(client))
    assert role["companies_considered"] == 1
    assert role["companies_with_no_data"] == 2
    assert by_name(role)["Excel"]["required_by_total"] == 1


def test_sorting_and_filters(client, world, db):
    for company in (world.hul, world.itc, world.nestle):
        db.add(
            CompanyRoleCapability(
                company_id=company.id, role_id=world.bm.id, capability_id=world.excel.id
            )
        )
    db.add(
        CompanyRoleCapability(
            company_id=world.hul.id, role_id=world.bm.id, capability_id=world.powerbi.id
        )
    )
    db.add(UserCapability(user_id="u1", capability_id=world.excel.id))
    db.commit()
    names = [c["name"] for c in only_role(gaps(client))["capabilities"]]
    assert names == ["Excel", "Power BI"]
    assert [c["name"] for c in only_role(gaps(client, gaps_only=True))["capabilities"]] == [
        "Power BI"
    ]
    assert [c["name"] for c in only_role(gaps(client, min_ratio=0.5))["capabilities"]] == [
        "Excel"
    ]


def test_role_filter_and_auth(client, world):
    assert only_role(gaps(client, role_id=world.bm.id))["role_title"] == "Brand Manager"
    not_target = client.get(
        "/profile/u1/skill-gaps", params={"role_id": world.dmm.id}, headers=as_user("u1")
    )
    assert not_target.status_code == 404
    assert client.get("/profile/u1/skill-gaps").status_code == 401
    assert client.get("/profile/u1/skill-gaps", headers=as_user("u2")).status_code == 403
    assert client.get("/profile/ghost/skill-gaps", headers=as_user("ghost")).status_code == 404
    assert client.get(
        "/profile/u1/skill-gaps", params={"min_ratio": 2}, headers=as_user("u1")
    ).status_code == 422
