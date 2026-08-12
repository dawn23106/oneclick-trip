from datetime import time

from app.agents.plan_preference_agent import (
    RuleBasedPlanPreferenceAgent,
    merge_inferred_plan_preferences,
)
from app.domain.models import (
    ItineraryDay,
    ItineraryItem,
    TravelEntities,
    TravelPlan,
    UserPreferences,
)


def _plan() -> TravelPlan:
    return TravelPlan(
        plan_id="plan-1",
        version=1,
        destination="成都",
        days=[
            ItineraryDay(
                day_index=1,
                items=[
                    ItineraryItem(
                        item_id="spot-1",
                        name="博物馆与历史街区",
                        start_time=time(9),
                        end_time=time(11),
                    ),
                    ItineraryItem(
                        item_id="food-1",
                        name="本地午餐",
                        item_type="FOOD",
                        start_time=time(12),
                        end_time=time(13),
                    ),
                ],
            )
        ],
    )


def test_single_saved_plan_is_kept_as_weak_evidence() -> None:
    agent = RuleBasedPlanPreferenceAgent()
    extraction = agent.extract(
        plan=_plan(), entities=TravelEntities(destination="成都"), preferences=UserPreferences()
    )

    updated = merge_inferred_plan_preferences(UserPreferences(), extraction)

    assert updated.memory_items
    assert updated.liked_tags == []
    assert updated.pace is None


def test_repeated_plan_pattern_promotes_recommendation_preference() -> None:
    agent = RuleBasedPlanPreferenceAgent()
    extraction = agent.extract(
        plan=_plan(), entities=TravelEntities(destination="成都"), preferences=UserPreferences()
    )
    preferences = UserPreferences()

    preferences = merge_inferred_plan_preferences(preferences, extraction)
    preferences = merge_inferred_plan_preferences(preferences, extraction)

    assert "本地美食" in preferences.liked_tags
    assert "历史文化" in preferences.liked_tags
    assert preferences.pace == "轻松"
    assert preferences.source_version == 2
