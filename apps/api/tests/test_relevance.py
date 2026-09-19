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
    assert score_article(only_role, HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 0) == 100.0


def test_partial_match_is_weight_proportional():
    student = ProfileTags(
        target_roles=frozenset({"brand-manager"}), target_companies=frozenset({"itc"})
    )
    # role (30) matched, company (25) not: 30/55
    assert score_article(student, HUL_BRAND_ARTICLE, ProfileStatus.TARGETING, 0) == 54.5


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
