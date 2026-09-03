from datetime import date

import pytest

from app.domain.date_resolution import resolve_explicit_dates


REFERENCE = date(2026, 9, 3)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("元旦去南昌", date(2027, 1, 1)),
        ("今年国庆去北京", date(2026, 10, 1)),
        ("明年国庆前夕出发", date(2027, 9, 30)),
        ("后年劳动节第二天", date(2028, 5, 2)),
        ("2027年春节去成都", date(2027, 2, 6)),
        ("2027年除夕团圆", date(2027, 2, 5)),
        ("春节去哈尔滨", date(2027, 2, 6)),
        ("清明去踏青", date(2027, 4, 5)),
        ("端午去杭州", date(2027, 6, 9)),
        ("中秋去苏州", date(2026, 9, 25)),
        ("今年中秋去苏州", date(2026, 9, 25)),
        ("2027年腊八去北京", date(2027, 1, 15)),
        ("明年母亲节旅行", date(2027, 5, 9)),
        ("明年父亲节旅行", date(2027, 6, 20)),
        ("明年感恩节旅行", date(2027, 11, 25)),
        ("圣诞节去上海", date(2026, 12, 25)),
    ],
)
def test_resolves_named_festival_family(expression: str, expected: date) -> None:
    assert resolve_explicit_dates(expression, reference_date=REFERENCE) == [expected]


def test_resolves_multiple_named_festivals_in_text_order() -> None:
    assert resolve_explicit_dates(
        "国庆和明年春节都想去旅行",
        reference_date=REFERENCE,
    ) == [date(2026, 10, 1), date(2027, 2, 6)]


def test_invalid_numeric_date_is_not_allowed_to_crash_intent_processing() -> None:
    assert resolve_explicit_dates("2027年2月30日出发", reference_date=REFERENCE) == []
