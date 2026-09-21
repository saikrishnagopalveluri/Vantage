"""Data-pipeline cases: feed parsing, ingest, the brief builder, tagging and connection strings.

Idempotency, hostile input and boundary values, the things that go wrong quietly in a pipeline.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.db import check_url, engine_options, normalize_url
from app.ingest import (
    BODY_MAX_CHARS,
    SUMMARY_MAX_CHARS,
    FeedEntry,
    clean_body,
    clean_summary,
    ingest_entries,
    parse_feed,
    retag_all,
)
from app.models import Article, ArticleTag, Source
from app.summarize import MAX_PARAGRAPH_CHARS, MAX_POINTER_CHARS, MAX_POINTERS, SHORT_NOTE, build_brief, sentences

NOW = datetime.now(timezone.utc)


def rss(*items: str) -> str:
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{"".join(items)}</channel></rss>'


def item(title="HUL launches campaign", link="https://example.com/a", desc="Body text.", date="Mon, 01 Jan 2024 10:00:00 GMT"):
    parts = [f"<title>{title}</title>", f"<link>{link}</link>", f"<description>{desc}</description>"]
    if date:
        parts.append(f"<pubDate>{date}</pubDate>")
    return f"<item>{''.join(parts)}</item>"


# ---- PIPE: feed parsing ---------------------------------------------------------------------


@pytest.mark.parametrize("content", ["", "   ", "not xml at all", "<html><body>nope</body></html>", "<rss><channel></rss>", b"\xff\xfe\x00garbage", "{}"])
def test_PIPE_garbage_feeds_give_no_entries_and_do_not_raise(content):
    assert parse_feed(content) == []


@pytest.mark.parametrize("link", ["javascript:alert(1)", "data:text/html,<script>1</script>", "ftp://example.com/x", "file:///etc/passwd", "//example.com/x", "example.com/x", ""])
def test_PIPE_non_http_links_are_dropped(link):
    assert parse_feed(rss(item(link=link))) == []


@pytest.mark.parametrize("link", ["http://example.com/a", "https://example.com/a?x=1&amp;y=2", "https://例え.jp/a"])
def test_PIPE_http_links_are_kept(link):
    assert len(parse_feed(rss(item(link=link)))) == 1


def test_PIPE_entries_without_title_or_link_are_skipped():
    feed = rss(item(title=""), item(link=""), item(title="Keep me", link="https://example.com/keep"))
    assert [e.title for e in parse_feed(feed)] == ["Keep me"]


def test_PIPE_html_in_titles_and_summaries_is_stripped():
    feed = rss(item(title="&lt;b&gt;HUL&lt;/b&gt; &amp; ITC", desc="&lt;p&gt;Hello &lt;script&gt;x()&lt;/script&gt; world&lt;/p&gt;"))
    e = parse_feed(feed)[0]
    assert "<" not in e.title and "&lt;" not in e.title and "HUL" in e.title
    assert "<" not in e.summary and "<p>" not in e.summary


def test_PIPE_future_dates_are_capped_at_now():
    e = parse_feed(rss(item(date="Mon, 01 Jan 2099 10:00:00 GMT")))[0]
    assert e.published_at <= datetime.now(timezone.utc)


def test_PIPE_missing_date_defaults_to_now():
    e = parse_feed(rss(item(date="")))[0]
    assert abs((datetime.now(timezone.utc) - e.published_at).total_seconds()) < 60


def test_PIPE_atom_feeds_parse_too():
    atom = ('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>t</title><entry><title>Atom story</title>'
            '<link href="https://example.com/atom"/><updated>2024-01-01T10:00:00Z</updated><summary>Sum</summary></entry></feed>')
    assert [e.title for e in parse_feed(atom)] == ["Atom story"]


def test_PIPE_one_bad_item_does_not_lose_the_good_ones():
    feed = rss(item(link="javascript:x"), item(title="Good one", link="https://example.com/good"), item(title="", link="https://example.com/x"))
    assert [e.title for e in parse_feed(feed)] == ["Good one"]


@pytest.mark.parametrize("n", [SUMMARY_MAX_CHARS - 1, SUMMARY_MAX_CHARS, SUMMARY_MAX_CHARS + 1, SUMMARY_MAX_CHARS * 5])
def test_PIPE_summary_length_boundaries(n):
    out = clean_summary("word " * n)
    assert len(out) <= SUMMARY_MAX_CHARS


@pytest.mark.parametrize("n", [BODY_MAX_CHARS - 1, BODY_MAX_CHARS, BODY_MAX_CHARS + 1, BODY_MAX_CHARS * 3])
def test_PIPE_body_length_boundaries(n):
    assert len(clean_body("word " * n)) <= BODY_MAX_CHARS


@pytest.mark.parametrize("raw", [None, "", "   ", "\n\t"])
def test_PIPE_empty_text_cleans_to_empty(raw):
    assert clean_summary(raw) == "" and clean_body(raw) == ""


def test_PIPE_entities_are_decoded_and_whitespace_collapsed():
    assert clean_summary("A &amp; B\n\n   C &lt;D&gt;") == "A & B C <D>"
    assert clean_summary("<p>One</p><p>Two</p>") == "One Two"


# ---- PIPE: ingest idempotency and gating --------------------------------------------------------------


@pytest.fixture()
def source(db, taxonomy):
    s = Source(name="QA Wire", feed_url="https://qa.test/rss", authority=3)
    db.add(s)
    db.commit()
    return s


def entry(title, url, body="HUL announced a new soap campaign for the monsoon quarter. Analysts expect results to show within two months.", when=NOW):
    return FeedEntry(title, url, body, when, body)


def test_PIPE_ingest_twice_adds_nothing_the_second_time(db, source):
    e = [entry("HUL launches monsoon soap campaign", "https://qa.test/1")]
    assert ingest_entries(db, source, e) == 1
    assert ingest_entries(db, source, e) == 0
    assert db.query(Article).count() == 1


def test_PIPE_same_url_twice_in_one_batch_is_stored_once(db, source):
    e = entry("HUL launches monsoon soap campaign", "https://qa.test/dup")
    assert ingest_entries(db, source, [e, e]) == 1


def test_PIPE_irrelevant_stories_are_not_stored(db, source):
    assert ingest_entries(db, source, [entry("Celebrity gossip roundup", "https://qa.test/gossip", "Nothing relevant here at all.")]) == 0


def test_PIPE_old_stories_are_ignored(db, source):
    old = NOW - timedelta(days=400)
    assert ingest_entries(db, source, [entry("HUL launches monsoon soap campaign", "https://qa.test/old", when=old)]) == 0


def test_PIPE_stored_article_has_tags_and_brief(db, source):
    ingest_entries(db, source, [entry("HUL launches monsoon soap campaign", "https://qa.test/tagged")])
    a = db.query(Article).one()
    assert a.brief and a.brief["paragraphs"] and db.query(ArticleTag).filter_by(article_id=a.id).count() >= 1


def test_PIPE_retag_keeps_relevant_and_is_stable(db, source):
    ingest_entries(db, source, [entry("HUL launches monsoon soap campaign", "https://qa.test/r1")])
    first = retag_all(db)
    second = retag_all(db)
    assert first == second == {"kept": 1, "removed": 0}


def test_PIPE_retag_removes_stories_that_no_longer_qualify_unless_saved(db, source, taxonomy):
    from app.models import User, UserInteraction, InteractionAction

    ingest_entries(db, source, [entry("HUL launches monsoon soap campaign", "https://qa.test/a"), entry("ITC opens new hotel wing", "https://qa.test/b")])
    db.query(ArticleTag).delete()
    db.add(User(id="reader"))
    db.flush()
    saved = db.query(Article).filter(Article.url.like("%/a")).one()
    db.add(UserInteraction(user_id="reader", article_id=saved.id, action=InteractionAction.SAVED))
    db.commit()
    # both keep their titles, so both still qualify on retag; force one to stop qualifying
    other = db.query(Article).filter(Article.url.like("%/b")).one()
    other.title, other.summary = "Celebrity gossip", "nothing relevant"
    db.commit()
    saved.title, saved.summary = "Celebrity gossip", "nothing relevant"
    db.commit()
    result = retag_all(db)
    assert result["removed"] == 1 and db.get(Article, saved.id) is not None  # the saved one survives


# ---- BRIEF: extractive summariser --------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["", "   ", "\n\n", "Too short.", "a"])
def test_BRIEF_empty_or_tiny_input_gives_a_safe_shape(text):
    b = build_brief("Title", text)
    assert set(b) >= {"paragraphs", "pointers"} and isinstance(b["paragraphs"], list)
    assert b["note"] == SHORT_NOTE


def test_BRIEF_single_sentence_gets_the_short_note():
    b = build_brief("HUL", "Hindustan Unilever announced a large new marketing campaign for the monsoon season today.")
    assert len(b["paragraphs"]) == 1 and b["note"] == SHORT_NOTE


LONG = " ".join(f"Sentence number {i} says that HUL grew sales by {i + 3} percent in the quarter." for i in range(30))


def test_BRIEF_long_text_respects_every_limit():
    b = build_brief("HUL grew sales", LONG)
    assert 1 <= len(b["paragraphs"]) <= 2 and all(len(p) <= MAX_PARAGRAPH_CHARS for p in b["paragraphs"])
    assert len(b["pointers"]) <= MAX_POINTERS and all(len(p) <= MAX_POINTER_CHARS for p in b["pointers"])


def test_BRIEF_only_uses_sentences_from_the_source_text():
    b = build_brief("HUL grew sales", LONG)
    source_sentences = set(sentences(LONG))
    for paragraph in b["paragraphs"]:
        for s in sentences(paragraph):
            assert s in source_sentences  # nothing is invented, every sentence is the publisher's own


def test_BRIEF_boilerplate_is_removed():
    text = ("HUL reported strong quarterly growth across categories in the latest results. "
            "The post HUL reports growth appeared first on Example Blog and more text here. "
            "Subscribe to our newsletter for daily updates and offers from us. "
            "Read more about the company results on our website today please.")
    assert not any("appeared first on" in s or "Subscribe" in s or "Read more" in s for s in sentences(text))


@pytest.mark.parametrize(
    "text",
    ["<script>alert(1)</script> " * 5, "x" * 100_000, ("Word " * 30 + ". ") * 500, "🙂" * 500, "日本語のテキストです。" * 200],
    ids=["script-tags", "one-huge-token", "many-long-sentences", "emoji", "cjk"],
)
def test_BRIEF_hostile_or_huge_input_never_raises_or_explodes(text):
    b = build_brief("Title", text)
    assert sum(len(p) for p in b["paragraphs"]) <= 2 * MAX_PARAGRAPH_CHARS + 5


def test_BRIEF_is_deterministic():
    assert build_brief("HUL grew sales", LONG) == build_brief("HUL grew sales", LONG)


# ---- DB: connection strings and engine options ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "given, expected",
    [
        ("postgres://u:p@h:6543/postgres", "postgresql+psycopg://u:p@h:6543/postgres"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///./x.db", "sqlite:///./x.db"),
        ("", ""),
    ],
)
def test_DB_normalize_url(given, expected):
    assert normalize_url(given) == expected


@pytest.mark.parametrize("url", ["", "postgresql://u:[YOUR-PASSWORD]@h/db", "postgresql://u:<password>@h/db", "postgresql://u:p@ss@h/db", "postgres://u:a@b@c@h/db"])
def test_DB_check_url_rejects_common_paste_mistakes(url):
    with pytest.raises(SystemExit):
        check_url(url)


@pytest.mark.parametrize("url", ["postgresql://u:p%40ss@h:6543/postgres", "sqlite:///./vantage.db", "postgresql+psycopg://u:p@h/db"])
def test_DB_check_url_accepts_good_urls(url):
    assert check_url(url) == url


def test_DB_engine_options_by_environment():
    from sqlalchemy.pool import NullPool

    assert engine_options("sqlite:///x.db", False) == {"connect_args": {"check_same_thread": False}}
    serverless = engine_options("postgresql+psycopg://u:p@h/db", True)
    assert serverless["poolclass"] is NullPool and serverless["connect_args"]["prepare_threshold"] is None
    pooled = engine_options("postgresql+psycopg://u:p@h/db", False)
    assert pooled["pool_size"] == 5 and "poolclass" not in pooled and pooled["pool_pre_ping"] is True
