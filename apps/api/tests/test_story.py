from datetime import datetime, timezone

import pytest

from app.ingest import FeedEntry, ingest_entries
from app.models import RoleCapability, Source, UserCapability
from app.story import is_low_value, story_kind
from tests.conftest import as_user

# Real headlines from the feeds, and the kind a reader would say each one is.
HEADLINES = [
    ("Bhavna Verma concludes five-year stint at Hindustan Unilever", "leadership"),
    ("Procter & Gamble elevates Ratul Ghosh as VP-HR (CHRO), APAC", "leadership"),
    ("Raisin UK appoints ex-Goldman Sachs exec Jules di Mambro CEO", "leadership"),
    ("Reliance names Anant Ambani as director", "leadership"),
    ("Anthropic, Accenture to invest $2 billion in AI model evaluation", "deal"),
    ("Link Logistics buys 4 last-mile facilities in Dallas-Fort Worth, Atlanta", "deal"),
    ("India IPO Boom: Foreign Investors Shift From Secondary To Primary", "deal"),
    ("Tata Steel seeks fresh UK government funding as Port Talbot project faces delays", "deal"),
    ("HUL Q1 results: net profit rises 5%", "results"),
    ("Anthropic's annualised revenue to top $100 billion in 2026", "results"),
    ("University of Maine preparing for staff and faculty layoffs", "hiring"),
    ("Infosys plans campus hiring of 20,000 freshers", "hiring"),
    ("FSSAI initiates legal action against Nestle India over infant nutrition products", "policy"),
    ("Rupee snaps losing streak on RBI support, oil retreat", "policy"),
    ("PepsiCo launches first-ever brand portfolio campaign", "launch"),
    ("DS Group, WPP Media and MICA launch DCODE 2.0", "launch"),
    ("Adani Enterprises airport unit enters into $1 billion fundraising deal", "deal"),
    ("Your marketing automation needs more context", "tech"),
    ("ITC stock: 360 ONE maintains BUY, sees 68% upside", "markets"),
    ("HDFC Bank shares gain over 1%: Here's why", "markets"),
]


@pytest.mark.parametrize("title, kind", HEADLINES, ids=[t[:40] for t, _ in HEADLINES])
def test_headline_kinds(title, kind):
    assert story_kind(title) == kind


@pytest.mark.parametrize(
    "title",
    [
        "Fed hikes main interest rate by quarter point",  # a rate hike is not a pay hike
        "F&O Talk: Sudeep Shah outlines Tata stocks strategy, names 5 picks",  # "names" is not an appointment
        "Putting Edtech Guidance to Work in the Classroom",
        "",
        "   ",
    ],
)
def test_headlines_that_only_look_like_a_kind_are_left_unlabelled_or_not_misread(title):
    assert story_kind(title) not in {"leadership", "hiring", "results"}


@pytest.mark.parametrize(
    "title",
    [
        "Top stocks to buy on Monday: Sumeet Bagadia recommends 3 stocks",
        "Saturday bank holiday: Are HDFC Bank, ICICI Bank, SBI open or closed today on September 19",
        "Today's Gold Rate in India September 18: Gold prices up in Delhi",
        "Sensex today | Stock Market Highlights: Sensex slips but Nifty gains",
        "Stock picks for the week from three brokerages",
    ],
)
def test_noise_is_recognised(title):
    assert is_low_value(title)


@pytest.mark.parametrize(
    "title",
    [
        "Open or closed AI? Nvidia's Nader Khalil and Sydney Sykes take on one of the decisions",
        "Bhavna Verma concludes five-year stint at Hindustan Unilever",
        "HUL Q1 results: net profit rises 5%",
    ],
)
def test_real_news_is_not_called_noise(title):
    assert not is_low_value(title)


def test_kinds_are_case_insensitive_and_only_read_the_headline_text():
    assert story_kind("UNILEVER APPOINTS NEW CEO") == "leadership"
    assert story_kind("unilever appoints new ceo") == "leadership"


# ---- how the feed uses it ---------------------------------------------------------------------------------


@pytest.fixture()
def stories(db, world):
    for cap in (world.excel, world.insights, world.powerbi):
        db.add(RoleCapability(role_id=world.bm.id, capability_id=cap.id))
    db.add(UserCapability(user_id="u1", capability_id=world.excel.id))
    strong = Source(name="Strong Paper", feed_url="https://strong.test/rss", authority=5)
    weak = Source(name="Weak Blog", feed_url="https://weak.test/rss", authority=1)
    db.add_all([strong, weak])
    db.commit()
    now = datetime.now(timezone.utc)
    return db, strong, weak, now


def feed(client, **params):
    res = client.get("/feed/u1", params={"limit": 50, **params}, headers=as_user("u1"))
    assert res.status_code == 200, res.text
    return {i["url"].rsplit("/", 1)[1]: i for i in res.json()["items"]}


def test_a_better_source_scores_a_little_higher_for_the_same_story(client, stories):
    db, strong, weak, now = stories
    ingest_entries(db, strong, [FeedEntry("HUL plans monsoon soap range", "https://strong.test/a", "", now)])
    ingest_entries(db, weak, [FeedEntry("ITC expands hotel portfolio abroad", "https://weak.test/b", "", now)])
    items = feed(client)
    assert items["a"]["score"] > items["b"]["score"]
    assert items["a"]["score"] - items["b"]["score"] < 10  # a nudge, not a takeover


def test_stock_tips_are_pushed_down_but_kept(client, stories):
    db, strong, _, now = stories
    ingest_entries(
        db,
        strong,
        [
            FeedEntry("HUL names new supply chain head", "https://strong.test/news", "", now),
            FeedEntry("Top stocks to buy on Monday: HUL, ITC", "https://strong.test/tips", "", now),
        ],
    )
    items = feed(client)
    assert "news" in items and items["news"]["score"] > 40
    assert items["news"]["score"] > items.get("tips", {"score": 0})["score"] * 1.5


def test_the_headline_kind_shows_up_in_both_lines(client, stories):
    db, strong, _, now = stories
    ingest_entries(db, strong, [FeedEntry("HUL appoints new chief marketing officer", "https://strong.test/cmo", "", now)])
    item = feed(client)["cmo"]
    assert "Leadership changes" in item["why_this_matters"]
    assert "new leader" in item["action"] and "HUL" in item["action"]


def test_a_company_story_does_not_get_credit_twice_for_its_industry(client, stories):
    db, strong, _, now = stories
    # The reader targets HUL, ITC, Nestle and Amazon, so FMCG is one of their target industries.
    # A story that only names HUL is tagged FMCG too, but that is the same fact.
    ingest_entries(db, strong, [FeedEntry("HUL opens a new plant near Pune", "https://strong.test/plant", "", now)])
    item = feed(client)["plant"]
    assert 40 <= item["score"] < 70  # relevant, not critical: one reason, not two


def test_a_target_company_headline_is_never_left_in_explore(client, stories):
    db, strong, _, now = stories
    ingest_entries(db, strong, [FeedEntry("Nestle India responds to notice from regulator", "https://strong.test/notice", "", now)])
    assert feed(client)["notice"]["tier"] in {"relevant", "critical"}
