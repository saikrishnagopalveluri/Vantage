"""Versions of the legal texts, who runs the service, and the consent check.

Change a version when the matching page changes in a way people should agree to again.
Contact details come from the environment, so nothing is invented: until they are set the pages say so.
"""

import os
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import Consent

TERMS_VERSION = "2026-09-20"
PRIVACY_VERSION = "2026-09-20"


class ConsentIn(BaseModel):
    terms_version: str
    privacy_version: str
    over_18: bool


def consent_required() -> bool:
    return os.getenv("VANTAGE_REQUIRE_CONSENT", "1").lower() not in {"0", "false", "no", "off"}


def operator() -> dict[str, str | None]:
    def env(name: str) -> str | None:
        return (os.getenv(name) or "").strip() or None  # an empty line in .env means "not set"

    return {
        "operator_name": env("VANTAGE_OPERATOR_NAME"),
        "contact_email": env("VANTAGE_CONTACT_EMAIL"),
        "grievance_officer": env("VANTAGE_GRIEVANCE_OFFICER"),
        "grievance_email": env("VANTAGE_GRIEVANCE_EMAIL") or env("VANTAGE_CONTACT_EMAIL"),
        "postal_address": env("VANTAGE_POSTAL_ADDRESS"),
        "hosting_region": env("VANTAGE_HOSTING_REGION"),
    }


def record_consent(db: Session, user_id: str, consent: ConsentIn | None, source: str) -> None:
    """Check the reader agreed to the current texts and is an adult, and store proof. Adds to the
    session without committing, so it lands in the same transaction as the account or profile."""
    if not consent_required():
        return
    if consent is None or not consent.over_18:
        raise HTTPException(status_code=422, detail="Confirm that you are 18 or older and agree to the terms and privacy policy.")
    if consent.terms_version != TERMS_VERSION or consent.privacy_version != PRIVACY_VERSION:
        raise HTTPException(status_code=422, detail="The terms or privacy policy just changed. Reload the page and read them again.")
    db.add(
        Consent(
            user_id=user_id,
            terms_version=consent.terms_version,
            privacy_version=consent.privacy_version,
            over_18=True,
            source=source,
            given_at=datetime.now(timezone.utc),
        )
    )
