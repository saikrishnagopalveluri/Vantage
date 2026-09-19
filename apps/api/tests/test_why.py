from app.models import ProfileStatus
from app.why import Matched, explain


def test_nothing_matched_means_no_explanation():
    assert explain(ProfileStatus.TARGETING, Matched()) is None


def test_target_company_and_gap_capability():
    why, action = explain(
        ProfileStatus.TARGETING,
        Matched(target_companies=["HUL"], gap_capabilities=["Power BI"]),
    )
    assert why.startswith("HUL is one of your target companies.")
    assert "Power BI shows up in requirements for roles you're targeting" in why
    assert action == "Try Power BI on a small task this week and add it to your prep."


def test_plural_gaps_use_plural_verb():
    why, _ = explain(ProfileStatus.TARGETING, Matched(gap_capabilities=["SQL", "Excel"]))
    assert why.startswith("SQL and Excel show up in requirements")


def test_only_two_reasons_are_shown():
    why, _ = explain(
        ProfileStatus.TARGETING,
        Matched(target_companies=["HUL"], gap_capabilities=["Power BI"], industries=["FMCG"]),
    )
    assert "FMCG" not in why


def test_placed_users_get_present_tense_framing():
    why, action = explain(
        ProfileStatus.PLACED, Matched(current_company="HUL", gap_capabilities=["Power BI"])
    )
    assert why.startswith("It covers HUL, where you work.")
    assert "your role" in why
    assert action == "Try Power BI on a small task this week."


def test_owned_capability_is_acknowledged_without_a_gap_claim():
    why, action = explain(ProfileStatus.TARGETING, Matched(owned_capabilities=["Excel"]))
    assert why == "It relates to Excel, which you already have."
    assert "skim" in action.lower()


def test_many_names_are_summarised():
    why, _ = explain(
        ProfileStatus.TARGETING, Matched(target_companies=["A", "B", "C", "D"])
    )
    assert why == "A, B and 2 more are among your target companies."


def test_role_and_industry_fallbacks():
    assert explain(ProfileStatus.TARGETING, Matched(target_roles=["Brand Manager"]))[0] == (
        "It mentions Brand Manager, a role you're targeting."
    )
    assert explain(ProfileStatus.PLACED, Matched(industries=["FMCG"]))[0] == (
        "It's about FMCG, your industry."
    )
