from datetime import date, time
from decimal import Decimal

from app.agents.direct_planner_agent import RuleBasedDirectPlannerAgent
from app.agents.meal_planning import ensure_daily_meals
from app.domain.models import BudgetMode, ItineraryItem, TravelEntities, UserPreferences


def _spot(name: str = "宽窄巷子") -> ItineraryItem:
    return ItineraryItem(
        item_id="D1-I1",
        name=name,
        start_time=time(9),
        end_time=time(11),
        visit_minutes=120,
    )


def test_ensure_daily_meals_adds_destination_food_near_the_route() -> None:
    items = ensure_daily_meals(
        [_spot()],
        day_index=1,
        destination="成都",
        entities=TravelEntities(destination="成都", people=2),
        travel_date=date(2026, 8, 1),
    )

    foods = [item for item in items if item.item_type == "FOOD"]
    assert len(foods) == 2
    assert [item.start_time for item in foods] == [time(12), time(18)]
    assert foods[0].name == "午餐 · 担担面与钟水饺"
    assert "宽窄巷子" in foods[0].description
    assert foods[0].estimated_cost == Decimal("90")
    assert foods[1].estimated_cost == Decimal("180")
    assert all(item.location_id is None for item in foods)


def test_existing_lunch_is_preserved_and_only_dinner_is_added() -> None:
    lunch = ItineraryItem(
        item_id="D1-I2",
        name="午餐 · 本地小吃",
        item_type="FOOD",
        start_time=time(12),
        end_time=time(13),
        visit_minutes=60,
        estimated_cost=Decimal("30"),
    )
    items = ensure_daily_meals(
        [_spot(), lunch],
        day_index=1,
        destination="成都",
        entities=TravelEntities(destination="成都"),
    )

    foods = [item for item in items if item.item_type == "FOOD"]
    assert len(foods) == 2
    assert lunch in foods
    assert any(item.name.startswith("晚餐") for item in foods)


def test_meal_uses_a_free_gap_instead_of_overlapping_an_attraction() -> None:
    long_spot = ItineraryItem(
        item_id="D1-I1",
        name="上午景点",
        start_time=time(9, 30),
        end_time=time(12, 30),
        visit_minutes=180,
    )
    afternoon_spot = ItineraryItem(
        item_id="D1-I2",
        name="下午景点",
        start_time=time(13, 30),
        end_time=time(17),
        visit_minutes=210,
    )
    items = ensure_daily_meals(
        [long_spot, afternoon_spot],
        day_index=1,
        destination="成都",
        entities=TravelEntities(destination="成都"),
    )

    lunch = next(item for item in items if item.name.startswith("午餐"))
    assert lunch.start_time == time(12, 30)
    assert lunch.end_time == time(13, 30)


def test_minimize_budget_uses_lower_meal_estimates() -> None:
    items = ensure_daily_meals(
        [_spot()],
        day_index=1,
        destination="西安",
        entities=TravelEntities(
            destination="西安",
            people=2,
            budget_mode=BudgetMode.MINIMIZE,
        ),
    )
    foods = [item for item in items if item.item_type == "FOOD"]
    assert [item.estimated_cost for item in foods] == [Decimal("40"), Decimal("70")]


def test_offline_direct_planner_also_contains_two_meals_per_day() -> None:
    proposal = RuleBasedDirectPlannerAgent().propose(
        query="帮我规划成都两日游",
        conversation_id="food-test",
        current_version=None,
        entities=TravelEntities(destination="成都", days=2, people=1),
        preferences=UserPreferences(),
    )

    assert proposal.plan is not None
    assert len(proposal.plan.days) == 2
    assert all(
        len([item for item in day.items if item.item_type == "FOOD"]) == 2
        for day in proposal.plan.days
    )
