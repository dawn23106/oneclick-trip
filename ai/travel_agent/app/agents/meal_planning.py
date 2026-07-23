from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from app.domain.models import BudgetMode, ItineraryItem, TravelEntities


_FOOD_KEYWORDS = (
    "早餐",
    "午餐",
    "晚餐",
    "夜宵",
    "美食",
    "餐厅",
    "餐馆",
    "火锅",
    "串串",
    "小吃",
    "面",
    "粉",
    "菜",
    "饭",
    "汤",
    "咖啡",
)

_CITY_MEALS: dict[str, dict[str, tuple[str, ...]]] = {
    "成都": {
        "lunch": ("担担面与钟水饺", "红油抄手与甜水面", "川味家常菜"),
        "dinner": ("成都火锅", "串串香", "经典川菜"),
    },
    "杭州": {
        "lunch": ("片儿川与葱包桧", "杭州小笼与馄饨", "知味小吃"),
        "dinner": ("杭帮菜", "西湖醋鱼与龙井虾仁", "河坊街风味晚餐"),
    },
    "西安": {
        "lunch": ("肉夹馍与凉皮", "臊子面", "葫芦头泡馍"),
        "dinner": ("羊肉泡馍", "回民街风味小吃", "陕西家常菜"),
    },
    "大理": {
        "lunch": ("喜洲粑粑与饵丝", "大理砂锅鱼", "白族风味小吃"),
        "dinner": ("云南菌子火锅", "白族家常菜", "酸辣鱼晚餐"),
    },
    "长沙": {
        "lunch": ("长沙米粉", "臭豆腐与糖油粑粑", "湘味小炒"),
        "dinner": ("经典湘菜", "口味虾", "夜市风味晚餐"),
    },
}


def looks_like_food(item: ItineraryItem) -> bool:
    if (item.item_type or "").upper() == "FOOD":
        return True
    text = f"{item.name} {item.description or ''}"
    return any(keyword in text for keyword in _FOOD_KEYWORDS)


def ensure_daily_meals(
    items: list[ItineraryItem],
    *,
    day_index: int,
    destination: str,
    entities: TravelEntities,
    travel_date=None,
) -> list[ItineraryItem]:
    """Guarantee explicit lunch and dinner items in a generated itinerary day."""

    result = list(items)
    food_items: list[ItineraryItem] = []
    for item in result:
        if looks_like_food(item):
            item.item_type = "FOOD"
            item.ticket_option_id = None
            if not item.estimated_cost:
                item.estimated_cost = _meal_cost(_meal_period(item), entities)
            food_items.append(item)

    explicit_meals = [item for item in food_items if _is_explicit_meal(item)]
    has_lunch = any(_meal_period(item) == "lunch" for item in explicit_meals)
    has_dinner = any(_meal_period(item) == "dinner" for item in explicit_meals)
    anchors = [item for item in result if not looks_like_food(item)]

    if not has_lunch:
        result.append(
            _build_meal(
                period="lunch",
                day_index=day_index,
                destination=destination,
                entities=entities,
                anchor=_anchor_name(anchors, "lunch"),
                travel_date=travel_date,
                slot=_find_meal_slot(result, "lunch"),
            )
        )
    if not has_dinner:
        result.append(
            _build_meal(
                period="dinner",
                day_index=day_index,
                destination=destination,
                entities=entities,
                anchor=_anchor_name(anchors, "dinner"),
                travel_date=travel_date,
                slot=_find_meal_slot(result, "dinner"),
            )
        )

    result.sort(key=lambda item: item.start_time or time.max)
    for index, item in enumerate(result, start=1):
        item.item_id = f"D{day_index}-I{index}"
    return result


def _meal_period(item: ItineraryItem) -> str:
    text = f"{item.name} {item.description or ''}"
    if any(keyword in text for keyword in ("午餐", "午饭", "中餐")):
        return "lunch"
    if any(keyword in text for keyword in ("晚餐", "晚饭", "夜宵")):
        return "dinner"
    if item.start_time and item.start_time.hour < 15:
        return "lunch"
    return "dinner"


def _is_explicit_meal(item: ItineraryItem) -> bool:
    text = f"{item.name} {item.description or ''}"
    return any(keyword in text for keyword in _FOOD_KEYWORDS)


def _anchor_name(items: list[ItineraryItem], period: str) -> str:
    if not items:
        return "当天游览区域"
    if period == "lunch":
        before_lunch = [
            item for item in items if item.start_time and item.start_time.hour < 14
        ]
        return (before_lunch[-1] if before_lunch else items[0]).name
    return items[-1].name


def _meal_name(destination: str, period: str, day_index: int) -> str:
    city = next((name for name in _CITY_MEALS if name in destination), None)
    choices = (
        _CITY_MEALS[city][period]
        if city
        else (("当地特色午餐", "当地风味小吃", "本地家常午餐") if period == "lunch" else ("当地特色晚餐", "本地招牌菜", "当地夜市风味"))
    )
    return choices[(day_index - 1) % len(choices)]


def _meal_cost(period: str, entities: TravelEntities) -> Decimal:
    people = entities.people or 1
    if entities.budget_mode is BudgetMode.MINIMIZE:
        per_person = Decimal("20") if period == "lunch" else Decimal("35")
    else:
        per_person = Decimal("45") if period == "lunch" else Decimal("90")
    return per_person * people


def _find_meal_slot(items: list[ItineraryItem], period: str) -> tuple[time, time]:
    if period == "lunch":
        target, earliest, latest, duration = 12 * 60, 11 * 60, 15 * 60, 60
    else:
        target, earliest, latest, duration = 18 * 60, 17 * 60, 21 * 60, 90

    occupied = [
        (_minutes(item.start_time), _minutes(item.end_time))
        for item in items
        if item.start_time and item.end_time
    ]
    candidates = list(range(earliest, latest - duration + 1, 15))
    candidates.sort(key=lambda value: (abs(value - target), value))
    for start_minutes in candidates:
        end_minutes = start_minutes + duration
        if all(end_minutes <= start or start_minutes >= end for start, end in occupied):
            return _clock(start_minutes), _clock(end_minutes)

    # An unusually dense model schedule should not make the whole plan invalid.
    # Use the first free slot later in the day while retaining the explicit meal.
    for start_minutes in range(earliest, 22 * 60 - duration + 1, 15):
        end_minutes = start_minutes + duration
        if all(end_minutes <= start or start_minutes >= end for start, end in occupied):
            return _clock(start_minutes), _clock(end_minutes)
    return (_clock(target), _clock(target + duration))


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _clock(value: int) -> time:
    return time(hour=value // 60, minute=value % 60)


def _build_meal(
    *,
    period: str,
    day_index: int,
    destination: str,
    entities: TravelEntities,
    anchor: str,
    travel_date,
    slot: tuple[time, time],
) -> ItineraryItem:
    is_lunch = period == "lunch"
    start, end = slot
    label = "午餐" if is_lunch else "晚餐"
    name = _meal_name(destination, period, day_index)
    description = (
        f"{label}安排在“{anchor}”附近，优先选择步行可达、评价稳定的门店，"
        f"减少跨区域折返；推荐品尝{name}。具体门店、营业时间和排队情况请在出行前核实。"
    )
    return ItineraryItem(
        item_id="",
        name=f"{label} · {name}",
        item_type="FOOD",
        start_at=datetime.combine(travel_date, start) if travel_date else None,
        end_at=datetime.combine(travel_date, end) if travel_date else None,
        start_time=start,
        end_time=end,
        location_id=None,
        description=description,
        travel_minutes=15,
        visit_minutes=60 if is_lunch else 90,
        ticket_option_id=None,
        estimated_cost=_meal_cost(period, entities),
    )
