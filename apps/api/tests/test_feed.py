from datetime import datetime, timedelta, timezone

import pytest

from app.feed import tier_for
from app.ingest import FeedEntry, ingest_entries
from app.models import RoleCapability, Source, UserCapability
from tests.conftest import as_user

NOW = datetime.now(timezone.utc)


@pytest.fixture()
def feed_world(db, world):
    """u1 wants Excel/Consumer Insights/Power BI for Brand Manager and already has Excel."""
    for cap in (world.excel, world.insights, world.powerbi):
        db.add(RoleCapability(role_id=world.bm.id, capability_id=cap.id))
    db.add(UserCapability(user_id="u1", capability_id=world.excel.id))
    source = Source(name="Marketing Dive", feed_url="https://feed.test/rss", authority=4)
    db.add(source)
    db.commit()
    entries = [
        FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "", NOW),
        FeedEntry("Consumer Insights join the Brand Manager toolkit", "https://x.test/bm", "", NOW),
        FeedEntry("Amazon expands same-day delivery", "https://x.test/amazon", "", NOW),
        FeedEntry("Ten Excel tips for analysts", "https://x.test/excel", "", NOW),
        FeedEntry("Celebrity gossip", "https://x.test/none", "", NOW),
    ]
    assert ingest_entries(db, source, entries) == 4
    return world


def fetch(client, user="u1", **params):
    res = client.get(f"/feed/{user}", params=params, headers=as_user(user))
    assert res.status_code == 200, res.text
    return res.json()


def urls(body):
    return [item["url"].rsplit("/", 1)[1] for item in body["items"]]


def article_id(client, slug):
    return next(i["id"] for i in fetch(client, limit=50)["items"] if i["url"].endswith(slug))


def act(client, article, action, user="u1"):
    return client.post(
        f"/feed/{user}/interaction",
        json={"article_id": article, "action": action},
        headers=as_user(user),
    )


def test_for_you_is_ranked_by_relevance_with_tiers(client, feed_world):
    body = fetch(client)
    assert set(urls(body)[:2]) == {"hul", "bm"} and urls(body)[2:] == ["amazon", "excel"]
    # Two matches (a role or company plus a missing skill) are critical; a company alone is relevant.
    assert [i["tier"] for i in body["items"]] == ["critical", "critical", "relevant", "explore"]
    assert body["summary"] == {"total": 4, "critical": 2, "relevant": 1, "explore": 1}
    scores = [i["score"] for i in body["items"]]
    assert scores == sorted(scores, reverse=True)
    assert scores[2] >= 40 > scores[3]  # a headline naming a target company is worth reading


def test_why_this_matters_is_grounded_in_matches(client, feed_world):
    by = {i["url"].rsplit("/", 1)[1]: i for i in fetch(client)["items"]}
    hul, bm, amazon, excel = by["hul"], by["bm"], by["amazon"], by["excel"]
    assert hul["why_this_matters"].startswith("HUL is one of your target companies.")
    assert "Power BI shows up in requirements" in hul["why_this_matters"]
    assert hul["action"]  # the exact advice depends on what the headline is about; see tests/test_why.py
    assert hul["matched"]["capabilities"] == ["Power BI"]
    assert "Brand Manager" in bm["why_this_matters"]
    assert amazon["why_this_matters"].startswith("Amazon is one of your target companies.")
    assert excel["why_this_matters"] == "It relates to Excel, which you already have."
    assert "Excel" in excel["action"]


def test_untagged_articles_never_appear(client, feed_world):
    assert "none" not in urls(fetch(client))


def test_companies_lens_only_shows_target_companies(client, feed_world):
    assert urls(fetch(client, lens="companies")) == ["hul", "amazon"]


def test_skills_lens_only_shows_capabilities_the_user_lacks(client, feed_world):
    # Excel is owned, so the Excel article is not a "skill to learn".
    assert set(urls(fetch(client, lens="skills"))) == {"hul", "bm"}


def test_dismissed_articles_leave_the_feed_and_can_return(client, feed_world):
    target = article_id(client, "amazon")
    assert act(client, target, "dismiss").json() == {
        "article_id": target, "saved": False, "dismissed": True,
    }
    assert "amazon" not in urls(fetch(client))
    assert fetch(client)["summary"]["total"] == 3
    act(client, target, "undismiss")
    assert "amazon" in urls(fetch(client))


def test_save_is_idempotent_and_shows_in_feed_and_saved_list(client, feed_world):
    target = article_id(client, "hul")
    act(client, target, "save")
    assert act(client, target, "save").json()["saved"] is True
    hul = next(i for i in fetch(client)["items"] if i["id"] == target)
    assert hul["saved"] is True
    saved = client.get("/feed/u1/saved", headers=as_user("u1")).json()
    assert [s["id"] for s in saved] == [target]
    assert saved[0]["source"] == {"name": "Marketing Dive", "authority": 4}
    assert act(client, target, "unsave").json()["saved"] is False
    assert client.get("/feed/u1/saved", headers=as_user("u1")).json() == []


def test_a_dismissed_article_stays_in_saved(client, feed_world):
    target = article_id(client, "hul")
    act(client, target, "save")
    act(client, target, "dismiss")
    assert "hul" not in urls(fetch(client))
    assert [s["id"] for s in client.get("/feed/u1/saved", headers=as_user("u1")).json()] == [target]


def test_pagination(client, feed_world):
    first = fetch(client, limit=3)
    assert len(first["items"]) == 3 and first["has_more"] is True
    rest = fetch(client, limit=3, offset=3)
    assert urls(rest) == ["excel"] and rest["has_more"] is False
    assert first["summary"]["total"] == 4


def test_as_of_pins_recency_scoring_across_a_scroll_session(client, feed_world):
    """Every page must echo back the `as_of` the first page used, and every later page in that
    scroll must use it too — otherwise the ranking (which scores recency against "now") reshuffles
    between page loads and the same story can reappear a few pages later under a new leader."""
    first = fetch(client)
    as_of = first["as_of"]
    assert as_of

    pinned_full = fetch(client, limit=10, as_of=as_of)
    page1 = fetch(client, limit=2, as_of=as_of)
    page2 = fetch(client, limit=2, offset=2, as_of=as_of)
    assert [i["id"] for i in page1["items"]] + [i["id"] for i in page2["items"]] == [i["id"] for i in pinned_full["items"]]
    assert page1["as_of"] == page2["as_of"] == as_of

    stale = fetch(client, limit=10, as_of=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat())
    fresh_score = next(i["score"] for i in pinned_full["items"] if i["url"].endswith("/hul"))
    stale_score = next(i["score"] for i in stale["items"] if i["url"].endswith("/hul"))
    assert stale_score < fresh_score  # the same story, scored as if 30 days older


def test_old_articles_are_outside_the_window_and_stale_ones_score_lower(client, db, feed_world):
    source = db.query(Source).one()
    ingest_entries(
        db,
        source,
        [
            FeedEntry("Amazon history lesson", "https://x.test/old", "", NOW - timedelta(days=90)),
            FeedEntry("HUL Power BI a week ago", "https://x.test/week", "", NOW - timedelta(days=7)),
        ],
    )
    body = fetch(client)
    assert "old" not in urls(body)
    fresh = next(i for i in body["items"] if i["url"].endswith("/hul"))
    week = next(i for i in body["items"] if i["url"].endswith("/week"))
    assert week["score"] < fresh["score"]


def test_a_user_with_no_targets_gets_an_empty_feed(client, feed_world):
    body = fetch(client, user="u2")
    assert body.pop("as_of")
    assert body == {
        "lens": "for_you",
        "summary": {"total": 0, "critical": 0, "relevant": 0, "explore": 0},
        "items": [],
        "offset": 0,
        "has_more": False,
    }


def test_auth_validation_and_missing_things(client, feed_world):
    assert client.get("/feed/u1").status_code == 401
    assert client.get("/feed/u1", headers=as_user("u2")).status_code == 403
    assert client.get("/feed/ghost", headers=as_user("ghost")).status_code == 404
    assert client.get("/feed/u1", params={"lens": "nope"}, headers=as_user("u1")).status_code == 422
    assert client.get("/feed/u1", params={"limit": 0}, headers=as_user("u1")).status_code == 422
    assert act(client, "missing", "save").status_code == 404
    assert act(client, "missing", "explode").status_code == 422
    assert client.get("/feed/u1/saved", headers=as_user("u2")).status_code == 403


def test_tier_boundaries():
    assert [tier_for(s) for s in (100, 70, 69.9, 40, 39.9, 0.1)] == [
        "critical", "critical", "relevant", "relevant", "explore", "explore",
    ]
