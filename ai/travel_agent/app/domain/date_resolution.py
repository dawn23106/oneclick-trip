from __future__ import annotations

import re
from datetime import date, timedelta


def resolve_explicit_dates(
    text: str,
    *,
    reference_date: date | None = None,
) -> list[date]:
    """Resolve only date expressions explicitly present in the current message.

    The result is code-owned so an LLM cannot silently replace a named holiday
    with the current date. A yearless New Year's Day means the next occurrence;
    on January 1 itself it means today.
    """
    today = reference_date or date.today()

    same_month_range = re.search(
        r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})[日号]?\s*(?:至|到|-|~)\s*(\d{1,2})[日号]",
        text,
    )
    if same_month_range:
        year, month, start_day, end_day = same_month_range.groups()
        resolved_year = int(year) if year else today.year
        return [
            date(resolved_year, int(month), int(start_day)),
            date(resolved_year, int(month), int(end_day)),
        ]

    for marker, offset in (("今天", 0), ("明天", 1), ("后天", 2)):
        if marker in text:
            return [today + timedelta(days=offset)]

    iso_dates = [
        date(int(year), int(month), int(day))
        for year, month, day in re.findall(
            r"(?<!\d)(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?!\d)",
            text,
        )
    ]
    if iso_dates:
        return iso_dates

    numeric_dates = [
        date(int(year) if year else today.year, int(month), int(day))
        for year, month, day in re.findall(
            r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})[日号]",
            text,
        )
    ]
    if numeric_dates:
        return numeric_dates

    new_year_match = re.search(r"(?:(\d{4})年|(今年|明年))?元旦(?:节)?", text)
    if not new_year_match:
        return []

    explicit_year, relative_year = new_year_match.groups()
    if explicit_year:
        holiday = date(int(explicit_year), 1, 1)
    elif relative_year == "今年":
        holiday = date(today.year, 1, 1)
    elif relative_year == "明年":
        holiday = date(today.year + 1, 1, 1)
    else:
        holiday = date(today.year, 1, 1)
        if holiday < today:
            holiday = date(today.year + 1, 1, 1)

    if re.search(r"元旦(?:节)?前(?:夕|一晚|一天)", text):
        holiday -= timedelta(days=1)
    return [holiday]
