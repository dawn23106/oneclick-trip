from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, timedelta

from lunar_python import Lunar, Solar


DateFactory = Callable[[int], date]


def _fixed(month: int, day: int) -> DateFactory:
    return lambda occurrence_year: date(occurrence_year, month, day)


def _lunar(month: int, day: int) -> DateFactory:
    """Return the lunar festival occurring in the requested Gregorian year."""

    def resolve(occurrence_year: int) -> date:
        # Lunar December belongs to the previous lunar year but is normally named
        # by its Gregorian occurrence year (for example, "2027 年腊八").
        for lunar_year in (occurrence_year - 1, occurrence_year):
            solar = Lunar.fromYmd(lunar_year, month, day).getSolar()
            candidate = date(solar.getYear(), solar.getMonth(), solar.getDay())
            if candidate.year == occurrence_year:
                return candidate
        raise ValueError(f"No lunar {month}/{day} occurrence in {occurrence_year}")

    return resolve


def _lunar_new_year_eve(occurrence_year: int) -> date:
    return _lunar(1, 1)(occurrence_year) - timedelta(days=1)


def _qingming(occurrence_year: int) -> date:
    # The solar term after the spring equinox is Qingming. Using the solar-term
    # calculation avoids hard-coding it as April 4 or April 5.
    solar = (
        Solar.fromYmd(occurrence_year, 3, 22)
        .getLunar()
        .getNextJieQi()
        .getSolar()
    )
    return date(solar.getYear(), solar.getMonth(), solar.getDay())


def _nth_weekday(month: int, weekday: int, occurrence: int) -> DateFactory:
    def resolve(occurrence_year: int) -> date:
        first = date(occurrence_year, month, 1)
        offset = (weekday - first.weekday()) % 7
        return first + timedelta(days=offset + 7 * (occurrence - 1))

    return resolve


# Travel-relevant Chinese statutory festivals, traditional festivals and common
# observances. Adding an alias or festival does not require changing parser logic.
_FESTIVALS: tuple[tuple[tuple[str, ...], DateFactory], ...] = (
    (("元旦节", "元旦"), _fixed(1, 1)),
    (("情人节",), _fixed(2, 14)),
    (("妇女节", "女神节"), _fixed(3, 8)),
    (("植树节",), _fixed(3, 12)),
    (("清明节", "清明"), _qingming),
    (("劳动节", "五一假期", "五一"), _fixed(5, 1)),
    (("青年节",), _fixed(5, 4)),
    (("儿童节", "六一儿童节"), _fixed(6, 1)),
    (("建党节",), _fixed(7, 1)),
    (("建军节",), _fixed(8, 1)),
    (("教师节",), _fixed(9, 10)),
    (("国庆节", "国庆假期", "十一国庆", "国庆"), _fixed(10, 1)),
    (("平安夜",), _fixed(12, 24)),
    (("圣诞节", "圣诞"), _fixed(12, 25)),
    (("春节", "大年初一", "正月初一"), _lunar(1, 1)),
    (("除夕夜", "除夕", "年三十"), _lunar_new_year_eve),
    (("元宵节", "元宵"), _lunar(1, 15)),
    (("龙抬头",), _lunar(2, 2)),
    (("端午节", "端午"), _lunar(5, 5)),
    (("七夕节", "七夕"), _lunar(7, 7)),
    (("中元节", "中元"), _lunar(7, 15)),
    (("中秋节", "中秋"), _lunar(8, 15)),
    (("重阳节", "重阳"), _lunar(9, 9)),
    (("腊八节", "腊八"), _lunar(12, 8)),
    (("北方小年", "小年"), _lunar(12, 23)),
    (("南方小年",), _lunar(12, 24)),
    (("母亲节",), _nth_weekday(5, 6, 2)),
    (("父亲节",), _nth_weekday(6, 6, 3)),
    (("感恩节",), _nth_weekday(11, 3, 4)),
)

_FACTORY_BY_ALIAS = {
    alias: factory for aliases, factory in _FESTIVALS for alias in aliases
}
_ALIASES_PATTERN = "|".join(
    re.escape(alias) for alias in sorted(_FACTORY_BY_ALIAS, key=len, reverse=True)
)
_FESTIVAL_PATTERN = re.compile(
    rf"(?:(?P<year>\d{{4}})年(?:的)?|(?P<relative>今年|明年|后年)(?:的)?)?"
    rf"(?P<alias>{_ALIASES_PATTERN})"
    rf"(?P<modifier>前夕|前一晚|前一天|后一天|第二天|次日|当天)?"
)


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _resolve_named_festivals(text: str, today: date) -> list[date]:
    resolved: list[date] = []
    for match in _FESTIVAL_PATTERN.finditer(text):
        explicit_year = match.group("year")
        relative_year = match.group("relative")
        factory = _FACTORY_BY_ALIAS[match.group("alias")]

        if explicit_year:
            candidate = factory(int(explicit_year))
        elif relative_year:
            candidate = factory(today.year + {"今年": 0, "明年": 1, "后年": 2}[relative_year])
        else:
            candidate = factory(today.year)
            if candidate < today:
                candidate = factory(today.year + 1)

        modifier = match.group("modifier")
        if modifier in {"前夕", "前一晚", "前一天"}:
            candidate -= timedelta(days=1)
        elif modifier in {"后一天", "第二天", "次日"}:
            candidate += timedelta(days=1)
        resolved.append(candidate)
    return resolved


def resolve_explicit_dates(
    text: str,
    *,
    reference_date: date | None = None,
) -> list[date]:
    """Resolve date expressions explicitly present in the current message.

    Named festivals resolve to their calendar anchor date. This function never
    invents an annual compensatory-work or extended-holiday schedule; those
    windows must come from the officially published schedule for that year.
    """
    today = reference_date or date.today()

    same_month_range = re.search(
        r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})[日号]?\s*(?:至|到|-|~)\s*(\d{1,2})[日号]",
        text,
    )
    if same_month_range:
        year, month, start_day, end_day = same_month_range.groups()
        resolved_year = int(year) if year else today.year
        start = _safe_date(resolved_year, int(month), int(start_day))
        end = _safe_date(resolved_year, int(month), int(end_day))
        return [value for value in (start, end) if value is not None]

    for marker, offset in (("今天", 0), ("明天", 1), ("后天", 2)):
        if marker in text:
            return [today + timedelta(days=offset)]

    iso_dates = [
        value
        for year, month, day in re.findall(
            r"(?<!\d)(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?!\d)",
            text,
        )
        if (value := _safe_date(int(year), int(month), int(day))) is not None
    ]
    if iso_dates:
        return iso_dates

    numeric_dates = [
        value
        for year, month, day in re.findall(
            r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})[日号]",
            text,
        )
        if (
            value := _safe_date(
                int(year) if year else today.year,
                int(month),
                int(day),
            )
        )
        is not None
    ]
    if numeric_dates:
        return numeric_dates

    return _resolve_named_festivals(text, today)
