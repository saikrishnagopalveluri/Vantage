from app.models import ProfileStatus
from app.relevance import ArticleTags, ProfileTags, recency_multiplier, score_article

HUL_BRAND_ARTICLE = ArticleTags(
    roles=frozenset({"brand-manager"}),
    companies=frozenset({"hul"}),
    industries=frozenset({"fmcg"}),
    capabilities=frozenset({"power-bi"}),
)

PROFILE = ProfileTags(
    current_role="brand-manager",
    current_company="hul",
    current_industry="fmcg",
    target_roles=frozenset({"product-manager"}),
    target_companies=frozenset({"google"}),
    target_industries=frozenset({"saas"}),
)


def test_same_profile_scores_differently_by_status():
    targeting = score_article(PROFILE, HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 0)
    placed = score_article(PROFILE, HUL_BRAND_ARTICLE, ProfileStatus.PLACED, 0)
    # Article matches only current-* dimensions: worthless while targeting, strong once placed.
    assert targeting == 0.0
    assert placed > 70


def test_student_scores_on_target_dimensions():
    student = ProfileTags(
        target_roles=frozenset({"brand-manager"}),
        target_companies=frozenset({"hul", "itc"}),
        target_industries=frozenset({"fmcg"}),
    )
    assert score_article(student, HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 0) == 100.0


def test_no_data_dimensions_dont_cap_the_score():
    only_role = ProfileTags(target_roles=frozenset({"brand-manager"}))
    # One perfect match on a profile with one dimension is strong, though not stretched to a full 100.
    assert score_article(only_role, HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 0) == 83.3
    with_more = ProfileTags(target_roles=frozenset({"brand-manager"}), target_companies=frozenset({"itc"}))
    assert score_article(with_more, HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 0) >= 80  # a second, unmatched dimension barely matters


FIVE = ProfileTags(
    target_roles=frozenset({"r"}),
    target_companies=frozenset({"c"}),
    target_industries=frozenset({"i"}),
    capabilities=frozenset({"gap", "own"}),
    owned_capabilities=frozenset({"own"}),
    domains=frozenset({"d"}),
)


def _score(**tags) -> float:
    return score_article(FIVE, ArticleTags(**tags), ProfileStatus.TARGETING, 0)


def test_one_strong_match_is_worth_reading():
    # A story that names a target company says nothing about the other four dimensions,
    # which used to drag it under the "relevant" line (25 of 100).
    assert _score(companies={"c": 1.0}) >= 40
    assert _score(roles={"r": 1.0}) >= 70


def test_dimensions_are_ordered_by_how_much_the_reader_cares():
    order = [
        _score(roles={"r": 1.0}),
        _score(companies={"c": 1.0}),
        _score(capabilities={"gap": 1.0}),
        _score(industries={"i": 1.0}),
        _score(domains={"d": 1.0}),
    ]
    assert order == sorted(order, reverse=True) and len(set(order)) == 5


def test_every_extra_match_raises_the_score():
    one = _score(companies={"c": 1.0})
    two = _score(companies={"c": 1.0}, roles={"r": 1.0})
    three = _score(companies={"c": 1.0}, roles={"r": 1.0}, capabilities={"gap": 1.0})
    assert one < two < three <= 100


def test_matching_every_dimension_is_a_perfect_score():
    everything = dict(roles={"r": 1.0}, companies={"c": 1.0}, industries={"i": 1.0}, capabilities={"gap": 1.0}, domains={"d": 1.0})
    assert _score(**everything) == 100.0


def test_a_teaser_mention_is_worth_less_than_a_headline():
    assert _score(companies={"c": 0.6}) < _score(companies={"c": 1.0})


def test_a_skill_the_reader_already_has_counts_for_less_than_one_they_lack():
    assert _score(capabilities={"own": 1.0}) < _score(capabilities={"gap": 1.0})


def test_score_never_exceeds_one_hundred():
    stacked = dict(roles={"r": 5.0}, companies={"c": 5.0}, industries={"i": 5.0}, capabilities={"gap": 5.0}, domains={"d": 5.0})
    assert _score(**stacked) <= 100.0


def test_empty_profile_scores_zero():
    assert score_article(ProfileTags(), HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 0) == 0.0


def test_recency_decays_towards_a_floor():
    assert recency_multiplier(0) == 1.0
    assert recency_multiplier(7) == 0.75
    assert 0.5 < recency_multiplier(365) < 0.51
    assert recency_multiplier(-3) == 1.0
    student = ProfileTags(target_roles=frozenset({"brand-manager"}))
    fresh = score_article(student, HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 0)
    stale = score_article(student, HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 30)
    assert fresh > stale
