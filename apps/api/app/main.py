import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import scheduler
from app.db import engine
from app.deps import get_db
from app.migrate import add_missing_columns
from app.models import Base, IngestRun
from app.routers import auth, feed, jds, onboarding, privacy, profile, public, taxonomy


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("VANTAGE_SKIP_DDL", "0").lower() not in {"1", "true", "yes"}:
        Base.metadata.create_all(bind=engine)
        add_missing_columns(engine)
    background = scheduler.Scheduler() if scheduler.enabled() else None
    if background:
        background.start()
    yield
    if background:
        background.stop()


app = FastAPI(title="Vantage API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(public.router)
app.include_router(privacy.router)
app.include_router(taxonomy.router)
app.include_router(onboarding.router)
app.include_router(profile.router)
app.include_router(feed.router)
app.include_router(jds.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    last = db.scalar(select(IngestRun).where(IngestRun.finished_at.is_not(None)).order_by(IngestRun.finished_at.desc()).limit(1))
    return {
        "status": "ok",
        "scheduler": "on" if scheduler.enabled() else "off",
        "last_ingest": None
        if last is None
        else {
            "kind": last.kind,
            "finished_at": scheduler._utc(last.finished_at).isoformat(),
            "articles_added": last.articles_added,
            "sources_failed": last.sources_failed,
            "error": last.error,
        },
    }
