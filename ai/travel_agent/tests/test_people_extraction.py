from datetime import date, timedelta
from decimal import Decimal

from app.agents.intent_agent import RuleBasedIntentAgent
from app.domain.date_resolution import resolve_explicit_dates
from app.graph.nodes.intent_recognition import _sanitize_explicit_update


def test_extracts_named_adult_count() -> None:
    decision = RuleBasedIntentAgent().classify(
        "1名成年人，2026年9月10日至11日游成都，预算1500元"
    )

    assert decision.entities.people == 1


def test_extracts_solo_travel_as_one_person() -> None:
    decision = RuleBasedIntentAgent().classify("我准备独自出行，去成都玩两天")

    assert decision.entities.people == 1


def test_keeps_named_adult_count_during_llm_sanitization() -> None:
    sanitized = _sanitize_explicit_update(
        {},
        "1名成年人，2026年9月10日至11日游成都",
        {"people": 1},
    )

    assert sanitized["people"] == 1


def test_extracts_two_adults_and_three_children_as_five_people() -> None:
    decision = RuleBasedIntentAgent().classify("从昆明出发，香港旅游十天，两大三小")

    assert decision.entities.people == 5


def test_keeps_family_composition_during_llm_sanitization() -> None:
    sanitized = _sanitize_explicit_update(
        {},
        "这次还是两大三小",
        {"people": 5},
    )

    assert sanitized["people"] == 5


def test_date_range_does_not_become_eleven_day_trip() -> None:
    decision = RuleBasedIntentAgent().classify(
        "1名成年人，2026年9月10日至11日游成都，共2天，预算1500元"
    )

    assert decision.entities.days == 2
    assert decision.entities.start_date.isoformat() == "2026-09-10"
    assert decision.entities.end_date.isoformat() == "2026-09-11"


def test_resolves_yearless_new_year_to_next_occurrence() -> None:
    reference = date(2026, 9, 3)

    assert resolve_explicit_dates("元旦节去", reference_date=reference) == [date(2027, 1, 1)]
    assert resolve_explicit_dates("元旦节前夕出发", reference_date=reference) == [date(2026, 12, 31)]


def test_keeps_iso_date_support() -> None:
    assert resolve_explicit_dates("2026-09-10 到 2026-09-12") == [
        date(2026, 9, 10),
        date(2026, 9, 12),
    ]


def test_new_year_overrides_wrong_llm_date_and_sets_trip_end() -> None:
    expected_start = resolve_explicit_dates("元旦节去南昌玩三天")[0]
    sanitized = _sanitize_explicit_update(
        {},
        "元旦节一个人从昆明到南昌玩三天",
        {"start_date": date.today(), "days": 3},
    )

    assert sanitized["start_date"] == expected_start
    assert sanitized["end_date"] == expected_start + timedelta(days=2)


def test_rule_agent_extracts_new_year_date() -> None:
    expected_start = resolve_explicit_dates("元旦节去")[0]
    decision = RuleBasedIntentAgent().classify(
        "元旦节一个人从昆明到南昌玩三天，预算1800元"
    )

    assert decision.entities.start_date == expected_start
    assert decision.entities.days == 3


def test_rule_agent_uses_budget_range_upper_limit() -> None:
    decision = RuleBasedIntentAgent().classify(
        "从昆明到南昌玩三天，一个人，总预算在1500到2500之间"
    )

    assert decision.entities.budget == Decimal("2500")
