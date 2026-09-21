from datetime import datetime, timezone

import pytest

from app.models import (
    Article,
    ArticleTag,
    Capability,
    CapabilityKind,
    Company,
    Domain,
    Industry,
    Role,
    RoleCapability,
    Source,
    TagType,
    User,
    UserProfile,
    UserTargetCompany,
    UserTargetRole,
)
from app.quiz import KIND_LABELS, MAX_LEVEL, make_questions
from app.seed_data.quiz_concepts import CONCEPTS
from tests.conftest import as_user


@pytest.fixture()
def arena(db):
    """A small world with enough of everything for every kind of question."""
    domains = [Domain(name=n, slug=s) for n, s in [("Marketing", "marketing"), ("Finance & Banking", "finance"), ("Consulting & Strategy", "consulting"), ("Operations", "operations"), ("HR", "hr")]]
    industries = [Industry(name=n) for n in ["FMCG", "Banking", "Consulting", "IT Services", "Energy"]]
    db.add_all(domains + industries)
    db.flush()
    companies = {}
    for i, ind in enumerate(industries):
        for j in range(3):
            c = Company(name=f"{ind.name} Co {j}", industry_id=ind.id, source="curated", taggable=True, mba=(j == 0))
            db.add(c)
            companies[c.name] = c
    skills = []
    for d in domains:
        for k in range(5):
            cap = Capability(name=f"{d.name} skill {k}", kind=CapabilityKind.SKILL, domain_id=d.id, source="curated")
            db.add(cap)
            skills.append(cap)
    db.flush()
    roles = []
    for d in domains:
        for k in range(2):
            r = Role(title=f"{d.name} Role {k}", domain_id=d.id, source="curated", taggable=True)
            db.add(r)
            roles.append(r)
    db.flush()
    for r in roles:
        for cap in [c for c in skills if c.domain_id == r.domain_id][:3]:
            db.add(RoleCapability(role_id=r.id, capability_id=cap.id))
    source = Source(name="Test Wire", feed_url="https://x.test/rss", authority=3)
    db.add(source)
    db.flush()
    now = datetime.now(timezone.utc)
    headlines = [
        ("FMCG Co 0 appoints new chief marketing officer", "FMCG Co 0"),
        ("Banking Co 1 launches a new savings campaign nationwide", "Banking Co 1"),
        ("Consulting Co 2 reports strong quarterly results this week", "Consulting Co 2"),
        ("Energy Co 0 plans a large expansion of its plants", "Energy Co 0"),
        ("IT Services Co 1 raises funding for its new venture", "IT Services Co 1"),
    ]
    for n, (title, company) in enumerate(headlines):
        a = Article(source_id=source.id, title=title, url=f"https://x.test/{n}", summary="", published_at=now)
        db.add(a)
        db.flush()
        db.add(ArticleTag(article_id=a.id, tag_type=TagType.COMPANY, ref_id=companies[company].id, weight=1.0))
    db.commit()
    return {"domains": domains, "industries": industries, "companies": companies, "roles": roles}


def batch(db, user="someone", count=12, level=1, seed=1, exclude=None):
    return make_questions(db, user, count, level, seed, exclude)


# ---- what every question must satisfy ---------------------------------------------------------------------------


@pytest.mark.parametrize("level", [1, 2, 3, 5, 8, 10])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_every_question_is_fair(db, arena, level, seed):
    for q in batch(db, level=level, seed=seed, count=15):
        assert len(q.options) == 4 and len({o.strip().lower() for o in q.options}) == 4
        assert 0 <= q.answer < 4 and q.prompt.strip() and q.explain.strip() and q.key
        assert 1 <= q.level <= MAX_LEVEL


def test_a_batch_has_no_repeated_questions_or_subjects(db, arena):
    qs = batch(db, count=15, level=3)
    assert len({q.key for q in qs}) == len(qs)
    subjects = [q.subject for q in qs if q.subject]
    assert len(subjects) == len(set(subjects))


def test_the_same_seed_gives_the_same_questions_and_another_seed_does_not(db, arena):
    a, b, c = batch(db, seed=5), batch(db, seed=5), batch(db, seed=6)
    assert [q.key for q in a] == [q.key for q in b]
    assert [q.key for q in a] != [q.key for q in c]


def test_the_count_is_respected(db, arena):
    assert len(batch(db, count=5)) == 5


def test_a_level_above_the_top_is_treated_as_the_top(db, arena):
    assert batch(db, level=99)  # clamps instead of failing


def test_questions_already_seen_are_left_out(db, arena):
    first = batch(db, count=10, seed=3)
    again = batch(db, count=10, seed=3, exclude={q.key for q in first})
    assert not {q.key for q in first} & {q.key for q in again}


def test_the_stream_does_not_run_dry_within_a_long_game(db, arena):
    seen: set[str] = set()
    for round_no in range(8):
        qs = batch(db, count=8, level=1 + round_no // 2, seed=round_no, exclude=seen)
        assert qs, f"ran out at batch {round_no}"
        seen |= {q.key for q in qs}
    assert len(seen) >= 40


def test_a_bare_database_still_produces_questions_from_the_hand_written_bank(db):
    qs = batch(db, count=6)
    assert len(qs) == 6 and {q.kind for q in qs} == {"concept"}


# ---- difficulty ---------------------------------------------------------------------------------------------------------


def test_level_one_is_only_easy_kinds(db, arena):
    kinds = {q.kind for s in range(6) for q in batch(db, level=1, seed=s, count=10)}
    assert kinds <= {"concept", "company_industry", "role_field"}


def test_headline_questions_appear_from_level_three(db, arena):
    kinds = {q.kind for s in range(8) for q in batch(db, level=3, seed=s, count=12)}
    assert {"headline_company", "headline_kind", "role_skill"} <= kinds


def test_concepts_get_harder_with_the_level(db, arena):
    by_prompt = {c[2]: c[1] for c in CONCEPTS}

    def concept_levels(level):
        return {by_prompt[q.prompt] for s in range(20) for q in batch(db, level=level, seed=s, count=10) if q.kind == "concept"}

    assert concept_levels(1) == {1}  # the first rounds only ask the basics
    assert concept_levels(2) <= {1, 2}
    assert 3 in concept_levels(3)  # the hard ones are reachable later on


# ---- headlines ----------------------------------------------------------------------------------------------------------


def test_the_company_is_hidden_in_the_headline_but_among_the_options(db, arena):
    found = [q for s in range(10) for q in batch(db, level=3, seed=s, count=12) if q.kind == "headline_company"]
    assert found
    for q in found:
        right = q.options[q.answer]
        assert "_____" in q.context and right.lower() not in q.context.lower()
        assert not any(o.lower() in q.context.lower() for o in q.options)


def test_the_story_kind_question_uses_only_clear_kinds(db, arena):
    found = [q for s in range(10) for q in batch(db, level=3, seed=s, count=12) if q.kind == "headline_kind"]
    assert found
    labels = set(KIND_LABELS.values())
    for q in found:
        assert set(q.options) <= labels and q.context
        assert not any("echnology" in o or "hare-price" in o for o in q.options)


def test_a_short_headline_is_not_turned_into_a_question(db, arena):
    db.query(ArticleTag).delete()
    db.query(Article).delete()
    src = db.query(Source).one()
    db.add(Article(source_id=src.id, title="Big deal today", url="https://x.test/short", summary="", published_at=datetime.now(timezone.utc)))
    db.commit()
    assert not [q for s in range(6) for q in batch(db, level=3, seed=s) if q.kind == "headline_kind"]


# ---- the player's own world ----------------------------------------------------------------------------------------------


def test_questions_lean_towards_the_players_targets(db, arena):
    target_role = arena["roles"][0]
    target_company = arena["companies"]["FMCG Co 0"]
    db.add_all([User(id="p1"), User(id="p2")])
    db.flush()
    db.add_all([UserProfile(user_id="p1"), UserProfile(user_id="p2")])
    db.add_all([UserTargetRole(user_id="p1", role_id=target_role.id), UserTargetCompany(user_id="p1", company_id=target_company.id)])
    db.commit()

    def about_targets(user):
        n = 0
        for s in range(20):
            for q in make_questions(db, user, 8, 2, s, None):
                n += q.subject in {target_role.title, target_company.name}
        return n

    assert about_targets("p1") > 2 * about_targets("p2")


def test_a_player_with_no_profile_still_gets_a_quiz(db, arena):
    assert len(batch(db, user="nobody-at-all")) == 12


# ---- the hand-written bank ---------------------------------------------------------------------------------------------------


def test_the_bank_is_well_formed():
    prompts = [c[2] for c in CONCEPTS]
    assert len(prompts) == len(set(prompts)) and len(CONCEPTS) >= 45
    for slug, level, prompt, right, wrong, explain in CONCEPTS:
        assert slug and 1 <= level <= 3 and prompt.endswith("?") and explain.endswith(".")
        assert len({right, *wrong}) == 4, prompt  # four different answers
        assert "—" not in prompt + right + explain + "".join(wrong)  # no em dashes in the copy


def test_the_bank_covers_the_fields_a_management_student_meets():
    assert {c[0] for c in CONCEPTS} >= {"marketing", "finance", "consulting", "operations", "hr", "digital-transformation"}


def test_the_bank_has_something_at_every_level_for_every_main_field():
    for slug in ("marketing", "finance", "consulting", "hr"):
        assert {c[1] for c in CONCEPTS if c[0] == slug} >= {1, 2}


# ---- the endpoint ---------------------------------------------------------------------------------------------------------------


def test_the_endpoint_returns_a_batch(client, arena):
    r = client.get("/quiz/u1", params={"count": 5, "level": 2}, headers=as_user("u1"))
    assert r.status_code == 200
    body = r.json()
    assert body["level"] == 2 and len(body["questions"]) == 5
    q = body["questions"][0]
    assert set(q) == {"id", "kind", "prompt", "context", "options", "answer", "explain", "field", "level"}


def test_the_endpoint_honours_the_exclude_list(client, arena):
    first = client.get("/quiz/u1", params={"count": 10, "seed": 4}, headers=as_user("u1")).json()["questions"]
    ids = ",".join(q["id"] for q in first)
    again = client.get("/quiz/u1", params={"count": 10, "seed": 4, "exclude": ids}, headers=as_user("u1")).json()["questions"]
    assert not {q["id"] for q in first} & {q["id"] for q in again}


@pytest.mark.parametrize("params", [{"count": 0}, {"count": 21}, {"level": 0}, {"level": 11}, {"count": "x"}, {"exclude": "a" * 6001}])
def test_the_endpoint_refuses_out_of_range_input(client, arena, params):
    assert client.get("/quiz/u1", params=params, headers=as_user("u1")).status_code == 422


def test_nobody_can_pull_a_quiz_for_someone_else_or_without_an_identity(client, arena):
    assert client.get("/quiz/u1", headers=as_user("u2")).status_code == 403
    assert client.get("/quiz/u1").status_code == 401


def test_hostile_text_in_the_exclude_list_is_harmless(client, arena):
    r = client.get("/quiz/u1", params={"exclude": "'; DROP TABLE roles;--,<script>,%"}, headers=as_user("u1"))
    assert r.status_code == 200 and r.json()["questions"]
    assert client.get("/taxonomy/domains").status_code == 200


def test_no_stack_trace_or_secret_leaks_in_a_response(client, arena):
    text = client.get("/quiz/u1", headers=as_user("u1")).text
    assert "Traceback" not in text and "password" not in text.lower()
