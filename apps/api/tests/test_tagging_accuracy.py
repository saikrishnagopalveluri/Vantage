"""Measures tagging accuracy on a labelled set, against the real taxonomy. The thresholds are
targets to hold, not numbers reverse-engineered from a run: a regression in either precision or
recall fails the build, and the failing cases are printed so the cause is obvious."""

import pytest

from app.models import Capability, Company, Role, TagType, Topic
from app.seed import seed_taxonomy
from app.tagging import build_index, is_relevant_enough, tag_article
from tests.tagging_cases import ALL_CASES, NEGATIVE, POSITIVE

KIND = {TagType.COMPANY: "company", TagType.CAPABILITY: "capability", TagType.TOPIC: "topic", TagType.ROLE: "role"}
PRECISION_TARGET = 0.95
RECALL_TARGET = 0.90


@pytest.fixture(scope="module")
def tagger():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.models import Base

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        seed_taxonomy(db)
        names = {}
        for model, attr in ((Company, "name"), (Capability, "name"), (Topic, "name"), (Role, "title")):
            for row in db.query(model):
                names[row.id] = getattr(row, attr)
        index = build_index(db)

    def run(title: str, teaser: str = ""):
        tags = tag_article(index, title, teaser)
        found: dict[str, set[str]] = {"company": set(), "capability": set(), "topic": set(), "role": set()}
        for (tag_type, ref_id) in tags:
            if tag_type in KIND:
                found[KIND[tag_type]].add(names[ref_id])
        return found, tags

    return run


def evaluate(tagger):
    tp = fp = fn = 0
    misses: list[str] = []
    for title, teaser, expected in ALL_CASES:
        found, _ = tagger(title, teaser)
        for kind in found:
            want = expected.get(kind, set())
            got = found[kind]
            tp += len(want & got)
            for extra in got - want:
                fp += 1
                misses.append(f"FALSE POSITIVE  {kind}:{extra!r}  <- {title!r}")
            for absent in want - got:
                fn += 1
                misses.append(f"MISSED          {kind}:{absent!r}  <- {title!r}")
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return precision, recall, misses


def test_precision_and_recall_meet_targets(tagger):
    precision, recall, misses = evaluate(tagger)
    report = "\n".join(misses)
    print(f"\nprecision={precision:.3f} recall={recall:.3f} over {len(ALL_CASES)} headlines\n{report}")
    assert precision >= PRECISION_TARGET, f"precision {precision:.3f} < {PRECISION_TARGET}\n{report}"
    assert recall >= RECALL_TARGET, f"recall {recall:.3f} < {RECALL_TARGET}\n{report}"


@pytest.mark.parametrize("title,teaser,expected", NEGATIVE, ids=[c[0][:50] for c in NEGATIVE])
def test_known_traps_are_not_tagged(tagger, title, teaser, expected):
    found, _ = tagger(title, teaser)
    tagged = {f"{kind}:{name}" for kind, names in found.items() for name in names}
    assert tagged == {f"{kind}:{name}" for kind, names in expected.items() for name in names}


def test_every_expected_positive_tag_is_found_in_isolation(tagger):
    """Each labelled tag must be found, so a missing alias is reported per case, not averaged away."""
    missing = []
    for title, teaser, expected in POSITIVE:
        found, _ = tagger(title, teaser)
        for kind, names in expected.items():
            for name in names - found[kind]:
                missing.append((kind, name, title))
    assert not missing, missing


def test_headline_mentions_outweigh_teaser_mentions(tagger):
    _, in_title = tagger("Infosys expands hiring", "")
    _, in_teaser = tagger("Big consultancy expands hiring", "Infosys is adding staff this quarter.")
    assert max(in_title.values()) == 1.0
    assert all(w < 1.0 for tag, w in in_teaser.items() if tag[0] == TagType.COMPANY)


def test_a_single_incidental_teaser_mention_is_not_enough(tagger):
    _, tags = tagger("Markets wobble on Tuesday", "Analysts pointed to Infosys among many names.")
    assert not is_relevant_enough(tags)
    _, both = tagger("Markets wobble on Tuesday", "Infosys and Wipro were among the names analysts pointed to.")
    assert is_relevant_enough(both)
