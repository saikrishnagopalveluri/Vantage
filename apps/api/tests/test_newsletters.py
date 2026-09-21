from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pytest

import app.feed as feed_module
from app.ingest import FeedEntry, ingest_entries, parse_feed, tag_story
from app.models import Source
from app.seed_data.sources import NEWSLETTER_NAMES, NEWSLETTERS, SOURCES
from app.tagging import build_index
from tests.conftest import as_user

NOW = datetime.now(timezone.utc)


# ---- the seeded list ------------------------------------------------------------------------------------


def test_every_source_has_a_unique_name_and_a_unique_https_feed():
    names = [n for n, _, _ in SOURCES]
    urls = [u for _, u, _ in SOURCES]
    assert len(names) == len(set(names)) and len(urls) == len(set(urls))
    assert all(urlparse(u).scheme == "https" for u in urls)


def test_every_authority_is_on_the_one_to_five_scale():
    assert {a for _, _, a in SOURCES} <= {1, 2, 3, 4, 5}


def test_the_newsletters_are_part_of_the_seeded_sources():
    assert NEWSLETTER_NAMES == {n for n, _, _ in NEWSLETTERS}
    assert {n for n, _, _ in NEWSLETTERS} <= {n for n, _, _ in SOURCES}
    assert len(NEWSLETTERS) >= 20


@pytest.mark.parametrize(
    "name",
    ["Google News - Big 4", "Google News - Digital transformation", "TechCrunch", "The Hindu - Technology", "Gadgets 360",
     "WSJ - Technology", "Mashable - Tech", "CNET", "Indian Express - Technology", "ITPro", "CX Today - Digital Transformation",
     "Business Standard - Technology", "ET CIO", "Morning Brew Daily", "The Playbook (Morning Brew)", "Lenny's Newsletter"],
)
def test_the_sources_you_asked_for_are_there(name):
    assert name in {n for n, _, _ in SOURCES}


def test_the_big_four_and_it_services_are_covered_through_news_searches():
    urls = " ".join(u for n, u, _ in SOURCES if n.startswith("Google News"))
    for company in ("Deloitte", "PwC", "EY", "KPMG", "Infosys", "TCS", "Wipro", "Accenture", "Cognizant"):
        assert company in urls


# ---- podcast feeds have no page per episode --------------------------------------------------------------------


def podcast(*items):
    return (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>Show</title><link>https://show.example</link>'
        + "".join(items)
        + "</channel></rss>"
    )


def episode(guid="ep-1", title="Episode one", enclosure=True):
    tag = '<enclosure url="https://cdn.example/a.mp3" type="audio/mpeg" length="1"/>' if enclosure else ""
    return f"<item><title>{title}</title><guid isPermaLink='false'>{guid}</guid>{tag}<description>About it.</description><pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate></item>"


def test_a_podcast_episode_links_to_the_show_with_its_own_id():
    [e] = parse_feed(podcast(episode("abc-123")))
    assert e.url == "https://show.example/#abc-123"


def test_each_episode_gets_a_different_address():
    urls = [e.url for e in parse_feed(podcast(episode("a"), episode("b", "Episode two")))]
    assert len(set(urls)) == 2


def test_an_item_with_no_link_and_no_audio_is_still_dropped():
    assert parse_feed(podcast(episode("x", enclosure=False))) == []


def test_a_normal_link_is_never_replaced():
    feed = podcast("<item><title>Story</title><link>https://news.example/a</link><guid>g</guid></item>")
    assert [e.url for e in parse_feed(feed)] == ["https://news.example/a"]


# ---- newsletters are judged on their opening text --------------------------------------------------------------------


@pytest.fixture()
def index(db, taxonomy):
    return build_index(db)


def test_a_newsletter_essay_is_kept_on_one_match_in_its_opening_text(index):
    tags, keep = tag_story(index, "Lenny's Newsletter", "The quiet rise of a playbook", "An essay.", "It follows how HUL rebuilt its brand teams.")
    assert keep and tags


def test_the_same_essay_from_a_news_source_needs_a_headline_match(index):
    _, keep = tag_story(index, "Marketing Dive", "The quiet rise of a playbook", "An essay.", "It follows how HUL rebuilt its brand teams.")
    assert not keep


def test_a_newsletter_with_nothing_relevant_is_dropped(index):
    _, keep = tag_story(index, "Lenny's Newsletter", "My garden this spring", "Tomatoes.", "Nothing about work at all.")
    assert not keep


def test_an_industry_alone_does_not_keep_a_newsletter_essay(index):
    tags, keep = tag_story(index, "Lenny's Newsletter", "Notes", "Short.", "")
    assert not keep and not tags


# ---- the Newsletters lens --------------------------------------------------------------------------------------------


@pytest.fixture()
def posts(db, world):
    letter = Source(name="Lenny's Newsletter", feed_url="https://letter.test/feed", authority=4)
    news = Source(name="Marketing Dive", feed_url="https://news.test/feed", authority=4)
    db.add_all([letter, news])
    db.commit()
    ingest_entries(db, letter, [FeedEntry("HUL rebuilt its brand playbook", "https://letter.test/hul", "An essay on the team.", NOW, "HUL brand teams changed how they plan.")])
    ingest_entries(db, news, [FeedEntry("ITC opens a new plant near Pune", "https://news.test/itc", "", NOW)])
    return letter, news


def items(client, lens):
    res = client.get("/feed/u1", params={"lens": lens, "limit": 50}, headers=as_user("u1"))
    assert res.status_code == 200, res.text
    return {i["url"].rsplit("/", 1)[1]: i for i in res.json()["items"]}


def test_the_newsletters_lens_shows_only_newsletters(client, posts):
    got = items(client, "newsletters")
    assert set(got) == {"hul"} and got["hul"]["newsletter"] is True


def test_the_main_feed_still_mixes_both_and_marks_the_newsletter(client, posts):
    got = items(client, "for_you")
    assert {"hul", "itc"} <= set(got)
    assert got["hul"]["newsletter"] is True and got["itc"]["newsletter"] is False


def test_the_lens_name_comes_back_in_the_response(client, posts):
    res = client.get("/feed/u1", params={"lens": "newsletters"}, headers=as_user("u1"))
    assert res.json()["lens"] == "newsletters"


def test_an_unknown_lens_is_still_refused(client, posts):
    assert client.get("/feed/u1", params={"lens": "podcasts"}, headers=as_user("u1")).status_code == 422


def test_a_weekly_newsletter_is_not_crowded_out_by_a_busy_news_day(client, db, posts, monkeypatch):
    letter, news = posts
    monkeypatch.setattr(feed_module, "MAX_CANDIDATES", 5)
    old = NOW - timedelta(days=6)
    ingest_entries(db, letter, [FeedEntry("ITC brand lessons from last week", "https://letter.test/old", "Essay.", old, "ITC brand notes.")])
    ingest_entries(db, news, [FeedEntry(f"Nestle India update number {i}", f"https://news.test/n{i}", "", NOW) for i in range(12)])
    assert "old" in items(client, "newsletters")  # the newsletter query is not cut off by the newest 5 news stories


def test_newsletters_let_in_weaker_matches_than_news_does():
    assert feed_module.NEWSLETTER_MIN_SCORE < feed_module.MIN_SCORE


def test_the_companies_lens_marks_newsletters_too(client, posts):
    got = items(client, "companies")
    assert got.get("hul", {"newsletter": True})["newsletter"] is True
