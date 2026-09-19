from datetime import datetime, timedelta, timezone

import pytest

from app.feed import DUPLICATE_JACCARD, is_duplicate, title_tokens
from app.ingest import FeedEntry, ingest_entries
from app.models import Company, Domain, Role, Source
from app.seed import seed_taxonomy
from tests.conftest import as_user

NOW = datetime.now(timezone.utc)


@pytest.fixture()
def seeded(db):
    seed_taxonomy(db)
    return db


def find(db, model, **kw):
    return db.query(model).filter_by(**kw).one().id


def source(db, name, authority=4):
    s = db.query(Source).filter_by(name=name).first()
    if s is None:
        s = Source(name=name, feed_url=f"https://{name}.test/rss", authority=authority)
        db.add(s)
        db.commit()
    return s


def publish(db, title, url, teaser="", src="Wire", age_days=0.1, authority=4):
    ingest_entries(db, source(db, src, authority), [FeedEntry(title, url, teaser, NOW - timedelta(days=age_days))])


def onboard(client, user, **body):
    res = client.post("/onboarding", json=body, headers=as_user(user))
    assert res.status_code == 201, res.text
    return res.json()


def feed(client, user, **params):
    res = client.get(f"/feed/{user}", params=params, headers=as_user(user))
    assert res.status_code == 200, res.text
    return res.json()


def titles(body):
    return [i["title"] for i in body["items"]]


def act(client, user, article_id, action):
    assert client.post(f"/feed/{user}/interaction", json={"article_id": article_id, "action": action}, headers=as_user(user)).status_code == 200


def item(body, fragment):
    return next(i for i in body["items"] if fragment in i["title"])


# ---- Domain relevance ----------------------------------------------------------------------------


def test_a_reader_who_only_follows_a_domain_gets_its_untargeted_news(client, seeded):
    publish(seeded, "RBI cuts repo rate as inflation cools", "https://x.test/rbi")
    publish(seeded, "Influencer marketing spend tops $30 billion", "https://x.test/inf")
    onboard(client, "fin", domain_ids=[find(seeded, Domain, slug="finance")])
    body = feed(client, "fin")
    assert titles(body) == ["RBI cuts repo rate as inflation cools"]
    assert "Finance & Banking" in item(body, "RBI")["domains"]
    assert "Interest Rates" in item(body, "RBI")["why_this_matters"]


def test_domain_filter_narrows_the_feed(client, seeded):
    publish(seeded, "RBI cuts repo rate as inflation cools", "https://x.test/rbi")
    publish(seeded, "Influencer marketing spend tops $30 billion", "https://x.test/inf")
    fin, mkt = find(seeded, Domain, slug="finance"), find(seeded, Domain, slug="marketing")
    onboard(client, "both", domain_ids=[fin, mkt])
    assert len(feed(client, "both")["items"]) == 2
    assert titles(feed(client, "both", domain_id=fin)) == ["RBI cuts repo rate as inflation cools"]
    assert titles(feed(client, "both", domain_id=mkt)) == ["Influencer marketing spend tops $30 billion"]


def test_following_a_role_implies_its_domain(client, seeded):
    publish(seeded, "Ransomware gang hits hospital network", "https://x.test/r")
    role = find(seeded, Role, title="Penetration Tester")
    onboard(client, "sec", target_role_ids=[role])
    assert titles(feed(client, "sec")) == ["Ransomware gang hits hospital network"]


# ---- Headline vs teaser --------------------------------------------------------------------------


def test_a_headline_mention_outranks_a_teaser_only_mention(client, seeded):
    publish(seeded, "Infosys wins a large deal", "https://x.test/head")
    publish(seeded, "Big IT deal announced this week", "https://x.test/teaser", teaser="Infosys and Wipro are expected to lead the delivery.")
    onboard(client, "u", target_company_ids=[find(seeded, Company, name="Infosys")])
    body = feed(client, "u")
    assert item(body, "Infosys wins")["score"] > item(body, "Big IT deal")["score"]


# ---- Duplicates ----------------------------------------------------------------------------------


def test_the_same_story_from_two_outlets_appears_once(client, seeded):
    publish(seeded, "FSSAI initiates legal action against Nestle India over infant food", "https://a.test/1", src="Mint", authority=4)
    publish(seeded, "FSSAI initiates legal action against Nestle India for infant food violations", "https://b.test/1", src="BusinessLine", authority=4)
    publish(seeded, "Nestle India responds to regulator", "https://c.test/1", src="Adweek", authority=4)
    onboard(client, "u", target_company_ids=[find(seeded, Company, name="Nestle India")])
    body = feed(client, "u")
    assert len(body["items"]) == 2, titles(body)
    story = next(i for i in body["items"] if "FSSAI" in i["title"])
    assert len(story["also_covered_by"]) == 1
    assert body["summary"]["total"] == 2


def test_title_similarity_rules():
    same = title_tokens("Infosys wins large cloud deal from bank")
    other = title_tokens("Infosys wins a large cloud deal from a bank")
    assert is_duplicate(same, other)
    assert not is_duplicate(same, title_tokens("Wipro announces quarterly results"))
    assert not is_duplicate(title_tokens("Infosys wins"), title_tokens("Infosys wins"))  # too short to trust
    assert 0 < DUPLICATE_JACCARD < 1


# ---- Learning from behaviour ---------------------------------------------------------------------


def test_dismissing_a_topic_lowers_similar_stories_for_that_reader_only(client, seeded):
    fin = find(seeded, Domain, slug="finance")
    publish(seeded, "Bitcoin slides as stablecoin rules loom", "https://x.test/c1")
    publish(seeded, "Crypto exchange faces regulator probe", "https://x.test/c2")
    onboard(client, "a", domain_ids=[fin])
    onboard(client, "b", domain_ids=[fin])
    before = item(feed(client, "a"), "Crypto exchange")["score"]
    act(client, "a", item(feed(client, "a"), "Bitcoin")["id"], "dismiss")
    assert item(feed(client, "a"), "Crypto exchange")["score"] < before
    assert item(feed(client, "b"), "Crypto exchange")["score"] == before


def test_saving_raises_similar_stories(client, seeded):
    fin = find(seeded, Domain, slug="finance")
    publish(seeded, "Bitcoin slides as stablecoin rules loom", "https://x.test/c1")
    publish(seeded, "Crypto exchange faces regulator probe", "https://x.test/c2")
    onboard(client, "a", domain_ids=[fin])
    before = item(feed(client, "a"), "Crypto exchange")["score"]
    act(client, "a", item(feed(client, "a"), "Bitcoin")["id"], "save")
    assert item(feed(client, "a"), "Crypto exchange")["score"] > before


def test_a_dismissal_never_buries_a_company_the_reader_targets(client, seeded):
    infosys = find(seeded, Company, name="Infosys")
    publish(seeded, "Infosys wins a large deal", "https://x.test/i1")
    publish(seeded, "Infosys opens a new campus in Pune", "https://x.test/i2")
    onboard(client, "a", target_company_ids=[infosys])
    body = feed(client, "a")
    before = item(body, "new campus")["score"]
    act(client, "a", item(body, "large deal")["id"], "dismiss")
    after = item(feed(client, "a"), "new campus")["score"]
    assert after >= before - 6 * 0.25 - 0.1  # protected: at most a quarter of the normal penalty


def test_weak_matches_fall_below_the_relevance_floor(client, seeded):
    publish(seeded, "Markets wobble on Tuesday", "https://x.test/weak", teaser="Analysts mentioned Infosys in passing.")
    onboard(client, "u", target_role_ids=[find(seeded, Role, title="Brand Manager")], target_company_ids=[find(seeded, Company, name="ITC")])
    assert feed(client, "u")["items"] == []


# ---- Onboarding with domains ---------------------------------------------------------------------


def test_onboarding_and_profile_carry_domains(client, seeded):
    fin = find(seeded, Domain, slug="finance")
    body = onboard(client, "u", domain_ids=[fin])
    assert [d["name"] for d in body["domains"]] == ["Finance & Banking"]
    updated = client.put("/profile/u/targets", json={"domain_ids": []}, headers=as_user("u")).json()
    assert updated["domains"] == []
    bad = client.post("/onboarding", json={"domain_ids": ["ghost"]}, headers=as_user("v"))
    assert bad.status_code == 422 and bad.json()["detail"]["unknown_ids"] == {"domain_ids": ["ghost"]}


def test_roles_in_a_profile_carry_their_domain(client, seeded):
    role = find(seeded, Role, title="Actuarial Analyst")
    body = onboard(client, "u", target_role_ids=[role])
    assert body["target_roles"][0]["domain"]["name"] == "Finance & Banking"
