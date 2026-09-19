def names(res, key="name"):
    assert res.status_code == 200
    return [row[key] for row in res.json()]


def test_lists_are_sorted_and_public(client, taxonomy):
    assert names(client.get("/taxonomy/roles"), "title") == [
        "Brand Manager",
        "Digital Marketing Manager",
    ]
    assert names(client.get("/taxonomy/industries")) == ["E-commerce", "FMCG"]
    assert names(client.get("/taxonomy/companies")) == [
        "Amazon", "HUL", "ITC", "Nestle", "Startup Co",
    ]


def test_search_is_case_insensitive_and_escapes_wildcards(client, taxonomy):
    assert names(client.get("/taxonomy/companies", params={"q": "nes"})) == ["Nestle"]
    assert names(client.get("/taxonomy/companies", params={"q": "%"})) == []
    assert names(client.get("/taxonomy/roles", params={"q": "MARKETING"}), "title") == [
        "Digital Marketing Manager"
    ]


def test_company_includes_industry(client, taxonomy):
    rows = {c["name"]: c for c in client.get("/taxonomy/companies").json()}
    assert rows["HUL"]["industry"]["name"] == "FMCG"
    assert rows["Startup Co"]["industry"] is None


def test_capabilities_filter_by_kind_and_limit(client, taxonomy):
    assert names(client.get("/taxonomy/capabilities", params={"kind": "skill"})) == [
        "Consumer Insights"
    ]
    assert names(client.get("/taxonomy/capabilities", params={"kind": "tool"})) == [
        "Excel",
        "Power BI",
    ]
    assert len(client.get("/taxonomy/capabilities", params={"limit": 1}).json()) == 1
    assert client.get("/taxonomy/capabilities", params={"limit": 0}).status_code == 422
    assert client.get("/taxonomy/capabilities", params={"kind": "bogus"}).status_code == 422
