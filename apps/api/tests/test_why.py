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
    assert "Power BI shows up in requirements for roles you're targeting, and it isn't on your profile yet." in why
    assert action == "Read up on Power BI this week and write down one real example of using it, then add it to your profile."


def test_plural_gaps_use_plural_verb():
    why, _ = explain(ProfileStatus.TARGETING, Matched(gap_capabilities=["SQL", "Excel"]))
    assert why.startswith("SQL and Excel show up in requirements")
    assert why.endswith("and they aren't on your profile yet.")


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
    assert action == "Read up on Power BI this week and write down one real example of using it, then use it on your next task."


def test_owned_capability_is_acknowledged_without_a_gap_claim():
    why, action = explain(ProfileStatus.TARGETING, Matched(owned_capabilities=["Excel"]))
    assert why == "It relates to Excel, which you already have."
    assert action == "Prepare one line on how you have used Excel, and use this story as the example."


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


# ---- what the story is about ----------------------------------------------------------------------

import pytest

from app.why import _DO_PLACED, _DO_TARGETING, _WHY_PLACED, _WHY_TARGETING

KINDS = ["leadership", "deal", "results", "hiring", "policy", "launch", "expansion", "tech", "markets"]


def test_every_kind_has_a_line_for_both_kinds_of_reader():
    for table in (_WHY_TARGETING, _WHY_PLACED, _DO_TARGETING, _DO_PLACED):
        assert set(table) == set(KINDS)


@pytest.mark.parametrize("kind", KINDS)
def test_the_story_kind_shapes_both_lines_for_a_target_company(kind):
    why, action = explain(ProfileStatus.TARGETING, Matched(target_companies=["HUL"]), kind)
    assert why.startswith("HUL is one of your target companies.") and why.endswith(_WHY_TARGETING[kind])
    assert action == _DO_TARGETING[kind].format(c="HUL")


@pytest.mark.parametrize("kind", KINDS)
def test_the_story_kind_shapes_both_lines_for_someone_working(kind):
    why, action = explain(ProfileStatus.PLACED, Matched(current_company="HUL"), kind)
    assert why.endswith(_WHY_PLACED[kind]) and action == _DO_PLACED[kind].format(c="HUL")


def test_a_story_about_a_company_gets_a_company_action_even_when_a_skill_matches_too():
    _, action = explain(ProfileStatus.TARGETING, Matched(target_companies=["HUL"], gap_capabilities=["Power BI"]), "leadership")
    assert "new leader" in action and "Power BI" not in action


def test_without_a_recognised_kind_a_missing_skill_drives_the_action():
    _, action = explain(ProfileStatus.TARGETING, Matched(target_companies=["HUL"], gap_capabilities=["Power BI"]))
    assert action.startswith("Read up on Power BI")


def test_tools_and_skills_get_different_practice_advice():
    tool = explain(ProfileStatus.TARGETING, Matched(gap_capabilities=["Power BI"], gap_kinds={"Power BI": "tool"}))[1]
    skill = explain(ProfileStatus.TARGETING, Matched(gap_capabilities=["Negotiation"], gap_kinds={"Negotiation": "skill"}))[1]
    assert tool.startswith("Spend 30 minutes in Power BI") and skill.startswith("Read up on Negotiation")


def test_a_company_that_is_both_current_and_target_is_mentioned_once():
    why, _ = explain(ProfileStatus.PLACED, Matched(current_company="HUL", target_companies=["HUL"]))
    assert why == "It covers HUL, where you work."


def test_placed_reader_tracking_another_company_still_hears_about_it():
    why, _ = explain(ProfileStatus.PLACED, Matched(current_company="HUL", target_companies=["HUL", "ITC"]))
    assert why == "It covers HUL, where you work. It covers ITC, a company you're tracking."


@pytest.mark.parametrize(
    "matched, expected",
    [
        (Matched(target_roles=["Brand Manager"]), "Add one line about this to your notes for Brand Manager interviews."),
        (Matched(owned_capabilities=["Excel"]), "Prepare one line on how you have used Excel, and use this story as the example."),
        (Matched(topics=["Pricing"], domains=["Marketing"]), "Save it if you want a talking point for Pricing conversations."),
        (Matched(domains=["Marketing"]), "Save it if you want a talking point for Marketing conversations."),
        (Matched(industries=["FMCG"]), "Save it if you want a talking point for FMCG conversations."),
        (Matched(target_companies=["HUL"]), "Save this under HUL and reread it before your interview."),
    ],
)
def test_targeting_fallback_actions_are_concrete(matched, expected):
    assert explain(ProfileStatus.TARGETING, matched)[1] == expected


@pytest.mark.parametrize(
    "matched, expected",
    [
        (Matched(current_role="Brand Manager"), "Think about what this changes in your day as Brand Manager."),
        (Matched(owned_capabilities=["Excel"]), "Note one way you could use Excel on your next project."),
        (Matched(current_company="HUL"), "Share it with your team if it changes how you work at HUL."),
        (Matched(domains=["Marketing"]), "Save it for your next planning conversation."),
    ],
)
def test_placed_fallback_actions_are_concrete(matched, expected):
    assert explain(ProfileStatus.PLACED, matched)[1] == expected


def test_the_text_never_names_something_that_was_not_matched():
    why, action = explain(ProfileStatus.TARGETING, Matched(target_roles=["Brand Manager"]), "results")
    assert "HUL" not in why + action and "Excel" not in why + action


def test_no_line_uses_a_dash_or_a_list_of_three():
    for table in (_WHY_TARGETING, _WHY_PLACED, _DO_TARGETING, _DO_PLACED):
        for line in table.values():
            assert "\u2014" not in line and "\u2013" not in line and not (line.count(",") >= 2 and " and " in line)


def test_nothing_matched_still_means_no_explanation_even_with_a_kind():
    assert explain(ProfileStatus.TARGETING, Matched(), "results") is None
