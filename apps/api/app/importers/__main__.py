"""python -m app.importers [onet|companies|all]: bulk-load roles, tools, skills and companies."""

import sys

from app.db import SessionLocal, engine
from app.importers import companies, onet
from app.models import Base


def main(argv: list[str]) -> None:
    target = argv[0] if argv else "all"
    if target not in {"onet", "companies", "all"}:
        raise SystemExit("usage: python -m app.importers [onet|companies|all]")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if target in {"onet", "all"}:
            onet.ensure_onet()
            print("onet:", onet.import_onet(db))
        if target in {"companies", "all"}:
            print("companies:", companies.import_companies(db))


if __name__ == "__main__":
    main(sys.argv[1:])
