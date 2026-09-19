from datetime import datetime, timezone

from app.ingest import FeedEntry, ingest_entries
from app.models import Source
from app.routers import public

NOW = datetime.now(timezone.utc)


def test_pulse_counts_and_headlines_need_no_login(client, db, world):
    public._cache.clear()
    real = Source(name="Marketing Dive", feed_url="https://f.test/a", authority=4)
    sample = Source(name="Vantage Samples (placeholder)", feed_url="sample://x", authority=1)
    db.add_all([real, sample])
    db.commit()
    ingest_entries(db, real, [FeedEntry("HUL rolls out Power BI dashboards", "https://x.test/hul", "", NOW)])
    ingest_entries(db, sample, [FeedEntry("[Sample] Amazon expands delivery", "https://x.test/s", "", NOW)])

    body = client.get("/public/pulse").json()
    assert body["job_titles"] == 2 and body["companies"] == 5 and body["skills_and_tools"] == 3
    assert body["stories_total"] == 2 and body["stories_today"] == 2
    assert [h["title"] for h in body["headlines"]] == ["HUL rolls out Power BI dashboards"]  # placeholders never show
    assert body["headlines"][0]["source"] == "Marketing Dive"
