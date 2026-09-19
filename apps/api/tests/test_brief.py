from datetime import datetime, timezone

from app.ingest import FeedEntry, clean_body, ingest_entries, parse_feed
from app.models import Article, Source
from app.summarize import SHORT_NOTE, build_brief
from tests.conftest import as_user
from tests.test_feed import feed_world, fetch  # noqa: F401  (fixture reuse)

NOW = datetime.now(timezone.utc)

LONG = (
    "HUL is rolling out Power BI dashboards across its 14 factories to track output in real time. "
    "The rollout covers 3,200 planners and will finish by March. "
    "Read more on our site. "
    "Executives said the tool replaces a patchwork of spreadsheets that took two days to reconcile each week. "
    "Analysts expect similar moves at other consumer goods makers this year. "
    "The company will spend about Rs 40 crore on training. "
    "Subscribe to our newsletter for daily updates. "
    "Shares of the company were flat on Tuesday."
)


def test_brief_has_paragraphs_and_pointers_without_boilerplate():
    brief = build_brief("HUL rolls out Power BI dashboards", LONG)
    assert 1 <= len(brief["paragraphs"]) <= 2
    joined = " ".join(brief["paragraphs"] + brief["pointers"])
    assert "Subscribe" not in joined and "Read more" not in joined
    assert brief["pointers"] and len(brief["pointers"]) <= 4
    assert all(len(p) <= 131 for p in brief["pointers"])
    assert brief["note"] is None
    # extractive: every paragraph sentence comes from the source text
    for para in brief["paragraphs"]:
        for sentence in para.split(". "):
            assert sentence.rstrip(".…") in LONG


def test_short_excerpt_gets_an_honest_note():
    brief = build_brief("Amazon expands same-day delivery", "Amazon is adding same-day delivery in 20 more cities.")
    assert brief["paragraphs"] == ["Amazon is adding same-day delivery in 20 more cities."]
    assert brief["note"] == SHORT_NOTE
    assert build_brief("x", "") == {"paragraphs": [], "pointers": [], "note": SHORT_NOTE}


def test_feed_body_prefers_full_content_and_is_capped():
    rss = (
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>'
        "<title>T</title><link>https://x.test/a</link><description>short teaser</description>"
        "<content:encoded><![CDATA[<p>" + ("Long sentence about markets. " * 200) + "</p>]]></content:encoded>"
        "</item></channel></rss>"
    )
    (entry,) = parse_feed(rss)
    assert entry.summary == "short teaser" and 1000 < len(entry.body) <= 1600
    assert "<p>" not in entry.body
    assert clean_body(None) == ""


def test_ingest_stores_the_brief_and_feed_shows_it(client, db, world):
    source = Source(name="Marketing Dive", feed_url="https://feed.test/rss", authority=4)
    db.add(source)
    db.commit()
    entry = FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "HUL is rolling out Power BI.", NOW, body=LONG)
    assert ingest_entries(db, source, [entry]) == 1
    stored = db.query(Article).one()
    assert stored.body == LONG and stored.brief["paragraphs"]


def test_feed_item_carries_a_brief_and_falls_back_to_matches(client, feed_world):  # noqa: F811
    items = {i["url"].rsplit("/", 1)[1]: i for i in fetch(client)["items"]}
    for item in items.values():
        assert item["brief"]["paragraphs"] == [] or isinstance(item["brief"]["paragraphs"], list)
    # These fixtures have no feed text, so the pointers come from what the article matched.
    assert any("HUL" in p for p in items["hul"]["brief"]["pointers"])
    assert items["hul"]["brief"]["note"] == SHORT_NOTE


def test_retag_drops_articles_the_taxonomy_no_longer_matches_but_keeps_saved_ones(client, db, world):
    from app.ingest import retag_all
    from app.models import Company, InteractionAction, UserInteraction

    source = Source(name="Marketing Dive", feed_url="https://feed.test/rss", authority=4)
    db.add(source)
    db.commit()
    entries = [
        FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "", NOW),
        FeedEntry("Amazon expands same-day delivery", "https://x.test/amazon", "", NOW),
        FeedEntry("Nestle opens a new plant", "https://x.test/nestle", "", NOW),
    ]
    assert ingest_entries(db, source, entries) == 3
    db.query(Company).filter(Company.name.in_(["Amazon", "Nestle"])).update({"taggable": False})
    saved = db.query(Article).filter_by(url="https://x.test/nestle").one()
    db.add(UserInteraction(user_id="u1", article_id=saved.id, action=InteractionAction.SAVED))
    db.commit()

    assert retag_all(db) == {"kept": 2, "removed": 1}
    assert {a.url for a in db.query(Article)} == {"https://x.test/hul", "https://x.test/nestle"}


def test_markup_in_a_feed_title_is_stripped():
    rss = (
        '<rss version="2.0"><channel><item><title>&lt;a href="https://x.test/y"&gt;Bayer&amp;#39;s drug wins nod&lt;/a&gt; &amp;amp; more</title>'
        "<link>https://x.test/y</link><description>d</description></item></channel></rss>"
    )
    (entry,) = parse_feed(rss)
    assert "<" not in entry.title and entry.title.startswith("Bayer")
