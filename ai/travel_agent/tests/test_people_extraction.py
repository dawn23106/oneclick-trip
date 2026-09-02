from app.agents.intent_agent import RuleBasedIntentAgent
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
