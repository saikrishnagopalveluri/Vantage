from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
from sqlalchemy import select

from app.ingest import (
    SUMMARY_MAX_CHARS,
    FeedEntry,
    clean_summary,
    fetch_source,
    ingest_entries,
    parse_feed,
)
from app.models import Article, ArticleTag, Source, TagType
from app.tagging import build_index, tag_text

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>HUL &amp; Amazon news</title><link>https://x.test/1</link>
<description>&lt;p&gt;Hello   &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;</description>
<pubDate>Tue, 10 Jun 2025 10:00:00 GMT</pubDate></item>
<item><title>No link here</title></item>
<item><title>From the future</title><link>https://x.test/2</link>
<pubDate>Mon, 01 Jan 2099 00:00:00 GMT</pubDate></item>
</channel></rss>"""


def tags(db, text):
    return tag_text(build_index(db), text)


def test_matches_names_and_aliases(db, taxonomy):
    taxonomy.nestle.aliases = ["Nestlé India"]
    db.commit()
    found = tags(db, "Nestlé India cuts prices; HUL follows")
    assert (TagType.COMPANY, taxonomy.nestle.id) in found
    assert (TagType.COMPANY, taxonomy.hul.id) in found


def test_company_implies_its_industry(db, taxonomy):
    assert (TagType.INDUSTRY, taxonomy.fmcg.id) in tags(db, "HUL posts results")


def test_word_boundaries_and_case_rules(db, taxonomy):
    assert tags(db, "excel at writing; an excellent switch; hul; the itc") == set()
    assert (TagType.CAPABILITY, taxonomy.excel.id) in tags(db, "Ten Excel tips")
    assert (TagType.COMPANY, taxonomy.itc.id) in tags(db, "ITC results beat estimates")
    assert (TagType.CAPABILITY, taxonomy.powerbi.id) in tags(db, "new power bi dashboards")
    assert (TagType.CAPABILITY, taxonomy.insights.id) in tags(db, "why consumer insights matter")


def test_clean_summary_strips_html_and_truncates():
    assert clean_summary("<p>Hello   <b>world</b> &amp; co</p>") == "Hello world & co"
    assert clean_summary(None) == ""
    long = clean_summary("word " * 200)
    assert len(long) <= SUMMARY_MAX_CHARS and long.endswith("…")


def test_parse_feed_keeps_valid_entries_and_clamps_future_dates():
    entries = parse_feed(RSS)
    assert [e.url for e in entries] == ["https://x.test/1", "https://x.test/2"]
    first, future = entries
    assert first.title == "HUL & Amazon news"
    assert first.summary == "Hello world"
    assert first.published_at == datetime(2025, 6, 10, 10, 0, tzinfo=timezone.utc)
    assert future.published_at <= datetime.now(timezone.utc)


def make_source(db, name="Src", url="https://feed.test/rss"):
    source = Source(name=name, feed_url=url)
    db.add(source)
    db.commit()
    return source


def entry(title, url, summary=""):
    return FeedEntry(title, url, summary, datetime.now(timezone.utc))


def test_ingest_stores_tagged_entries_once_and_drops_untagged(db, taxonomy):
    source = make_source(db)
    batch = [
        entry("HUL launches Power BI push", "https://x.test/a"),
        entry("Celebrity gossip roundup", "https://x.test/b"),
    ]
    assert ingest_entries(db, source, batch) == 1
    assert ingest_entries(db, source, batch) == 0  # re-run is a no-op
    [article] = db.scalars(select(Article)).all()
    assert article.url == "https://x.test/a"
    found = {(t.tag_type, t.ref_id) for t in db.scalars(select(ArticleTag))}
    assert found == {
        (TagType.COMPANY, taxonomy.hul.id),
        (TagType.INDUSTRY, taxonomy.fmcg.id),
        (TagType.CAPABILITY, taxonomy.powerbi.id),
    }


def test_same_url_within_one_batch_is_stored_once(db, taxonomy):
    source = make_source(db)
    dup = [entry("HUL news", "https://x.test/a"), entry("HUL news again", "https://x.test/a")]
    assert ingest_entries(db, source, dup) == 1


def client_returning(status, body=b""):
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status, content=body)))


def test_fetch_source_ingests_and_clears_previous_error(db, taxonomy):
    source = make_source(db)
    source.last_error = "old failure"
    db.commit()
    fresh = RSS.replace("Tue, 10 Jun 2025 10:00:00 GMT", format_datetime(datetime.now(timezone.utc), usegmt=True))
    added = fetch_source(db, source, client_returning(200, fresh.encode()), build_index(db))
    assert added == 1
    db.refresh(source)
    assert source.last_error is None and source.last_fetched_at is not None


def test_failing_source_records_error_instead_of_raising(db, taxonomy):
    source = make_source(db)
    assert fetch_source(db, source, client_returning(500), build_index(db)) == 0
    db.refresh(source)
    assert "500" in source.last_error
    assert source.last_fetched_at is not None
    assert db.scalars(select(Article)).all() == []


def test_entries_older_than_the_cutoff_are_not_stored(db, taxonomy):
    source = make_source(db)
    old = FeedEntry("HUL archive story", "https://x.test/old", "", datetime.now(timezone.utc) - timedelta(days=400))
    new = FeedEntry("HUL fresh story", "https://x.test/new", "", datetime.now(timezone.utc))
    assert ingest_entries(db, source, [old, new]) == 1
    assert [a.title for a in db.scalars(select(Article))] == ["HUL fresh story"]


def test_only_http_and_https_links_are_accepted():
    feed = """<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
    <item><title>Safe</title><link>https://example.com/a</link></item>
    <item><title>Plain http</title><link>http://example.com/b</link></item>
    <item><title>Script link</title><link>javascript:alert(1)</link></item>
    <item><title>Data link</title><link>data:text/html,hi</link></item>
    <item><title>Relative</title><link>/just/a/path</link></item>
    </channel></rss>"""
    assert [e.title for e in parse_feed(feed)] == ["Safe", "Plain http"]
