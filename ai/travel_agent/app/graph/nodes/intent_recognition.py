import re
from datetime import timedelta
from decimal import Decimal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable, RunnableLambda

from app.agents.intent_agent import (
    IntentAgent,
    RuleBasedIntentAgent,
    enforce_code_owned_intent,
    infer_query_tasks,
)
from app.domain.date_resolution import resolve_explicit_dates
from app.domain.models import (
    BudgetMode,
    BudgetScope,
    Intent,
    IntentContext,
    IntentTask,
    NextAction,
    TravelEntities,
    UserPreferences,
)
from app.graph.state import TravelState, TravelStatePatch
from app.graph.tool_runtime import reset_tool_execution


FRESH_TRIP_MARKERS = (
    "新的旅行",
    "新旅行",
    "重新规划",
    "重新安排",
    "想出去旅游",
    "想出去玩",
    "想去旅游",
    "推荐一个地方",
    "换个目的地",
)

DESTINATION_REFERENCE_MARKERS = (
    "那",
    "那里",
    "当地",
    "这里",
    "这儿",
    "这座城市",
    "这个地方",
)

PENDING_PLAN_ADJUSTMENT_MARKERS = (
    "预算改",
    "总预算",
    "人均",
    "缩短",
    "延长",
    "改成",
    "换成",
    "人数改",
    "保持预算",
    "继续规划",
    "继续生成",
    "接着规划",
    "接着生成",
    "重新尝试",
    "再试一次",
)

EXISTING_PLAN_OPTIMIZATION_MARKERS = (
    "优化",
    "完善行程",
    "改进行程",
    "继续调整",
)

QUERY_INTENTS = {
    Intent.WEATHER_QUERY,
    Intent.HOTEL_QUERY,
    Intent.TRANSPORT_QUERY,
    Intent.GENERAL_QA,
}


def make_intent_recognition_node(
    agent: IntentAgent,
) -> Runnable[TravelState, TravelStatePatch]:
    """把意图 Agent 包装为同时支持同步和异步调用的 LangGraph 节点。

    节点负责读取最近一次用户消息、构造会话上下文、修复不安全的模型路由，
    并把本轮显式实体与允许继承的历史槽位合并到共享状态。
    """

    def query_from(state: TravelState) -> str:
        """从消息历史中取得最近一条用户输入。"""
        return next(
            (
                str(message.content)
                for message in reversed(state.get("messages", []))
                if isinstance(message, HumanMessage)
            ),
            "",
        )

    def context_from(state: TravelState) -> IntentContext:
        """构造供意图 Agent 消解指代的最小会话上下文。"""
        recent_messages = []
        for message in state.get("messages", [])[-20:]:
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                continue
            recent_messages.append(f"{role}: {message.content}")
        plan = state.get("current_plan")
        draft = state.get("booking_draft")
        return IntentContext(
            recent_messages=recent_messages,
            user_preferences=state.get("user_preferences") or UserPreferences(),
            previous_intent=state.get("intent") or Intent.UNKNOWN,
            pending_missing_fields=list(state.get("missing_fields", [])),
            current_plan_id=plan.plan_id if plan else None,
            current_plan_version=plan.version if plan else None,
            booking_draft_id=draft.draft_id if draft else None,
            booking_status=draft.status if draft else None,
        )

    def patch_from(state: TravelState, decision, query: str) -> TravelStatePatch:
        """校正意图结果并生成本轮状态补丁，清理上一轮临时执行数据。"""
        decision = _repair_intent_decision(state, query, decision)
        previous = state.get("entities") or TravelEntities()
        explicit_update = _sanitize_explicit_update(
            state,
            query,
            decision.entities.model_dump(exclude_unset=True),
        )
        intent = _resolve_intent_for_slot_follow_up(
            state,
            decision.intent,
            explicit_update,
            query,
        )
        inherited = _entity_base_for_turn(
            state,
            previous,
            intent,
            query,
            explicit_update,
        )
        base = inherited.model_copy(
            update={
                "explicit_preferences": [],
                "explicit_dislikes": [],
                "selected_option_ids": [],
                "booking_types": [],
            }
        )
        merged_entities = base.model_copy(update=explicit_update)
        intent_tasks = _normalize_intent_tasks(
            state,
            query,
            decision.tasks,
            intent,
            merged_entities,
        )
        return {
            **reset_tool_execution(),
            "intent": intent,
            "intent_confidence": decision.confidence,
            "intent_tasks": intent_tasks,
            "entities": merged_entities,
            "missing_fields": decision.advisory_missing_fields,
            "clarification_reply": None,
            "budget_feasibility": None,
            "plan_draft": None,
            "hard_validation": None,
            "review_result": None,
            "planning_errors": [],
            "modification_errors": [],
            "booking_errors": [],
            "plan_saved": False,
            "validation_exhausted": False,
            "revision_count": 0,
            "next_action": NextAction.NORMALIZE_STATE,
        }

    def recognize_intent(state: TravelState) -> TravelStatePatch:
        query = query_from(state)
        return patch_from(
            state,
            agent.classify(query, context=context_from(state)),
            query,
        )

    async def arecognize_intent(state: TravelState) -> TravelStatePatch:
        query = query_from(state)
        return patch_from(
            state,
            await agent.aclassify(query, context=context_from(state)),
            query,
        )

    return RunnableLambda(recognize_intent, afunc=arecognize_intent, name="recognize_intent")


def _repair_intent_decision(state: TravelState, query: str, decision):
    """Reject structurally valid but unusable LLM routing decisions."""
    repaired = enforce_code_owned_intent(query, decision)
    if (
        state.get("current_plan") is not None
        and any(marker in query for marker in EXISTING_PLAN_OPTIMIZATION_MARKERS)
        and not any(marker in query for marker in FRESH_TRIP_MARKERS)
    ):
        return repaired.model_copy(
            update={
                "intent": Intent.MODIFY_PLAN,
                "tasks": [],
            }
        )
    return repaired


def _normalize_intent_tasks(
    state: TravelState,
    query: str,
    model_tasks: list[IntentTask],
    primary_intent: Intent,
    primary_entities: TravelEntities,
) -> list[IntentTask]:
    """规范复合只读查询；受控业务意图始终保持为单任务。"""
    if primary_intent not in QUERY_INTENTS:
        return [
            IntentTask(
                task_id="task-1",
                query=query,
                intent=primary_intent,
                entities=primary_entities,
            )
        ]

    code_tasks = infer_query_tasks(query)
    valid_model_tasks = [item for item in model_tasks if item.intent in QUERY_INTENTS]
    candidates = (
        code_tasks
        if len(code_tasks) > 1
        else valid_model_tasks
        if len(valid_model_tasks) > 1
        else code_tasks or valid_model_tasks
    )
    normalized: list[IntentTask] = []
    for index, task in enumerate(candidates or []):
        task_query = task.query.strip() or query
        explicit = _sanitize_explicit_update(
            state,
            task_query,
            task.entities.model_dump(exclude_unset=True),
        )
        entities = _query_task_entities(primary_entities, explicit, task.intent)
        normalized.append(
            IntentTask(
                task_id=f"task-{index + 1}",
                query=task_query,
                intent=task.intent,
                entities=entities,
            )
        )
    return normalized or [
        IntentTask(
            task_id="task-1",
            query=query,
            intent=primary_intent,
            entities=primary_entities,
        )
    ]


def _query_task_entities(
    shared: TravelEntities,
    explicit: dict,
    intent: Intent,
) -> TravelEntities:
    """为复合查询子任务补充可共享的城市、日期等上下文。"""
    values = dict(explicit)
    shared_fields = ["destination", "start_date", "end_date", "days", "currency"]
    if intent is Intent.TRANSPORT_QUERY:
        shared_fields.append("origin")
    for field in shared_fields:
        value = getattr(shared, field)
        if values.get(field) in (None, "") and value is not None:
            values[field] = value
    return TravelEntities(**values)


def _resolve_intent_for_slot_follow_up(
    state: TravelState,
    detected_intent,
    explicit_update: dict,
    query: str,
):
    """识别用户是否只是在补充上一轮缺失槽位，并延续原业务意图。"""
    previous_intent = state.get("intent")
    missing_fields = set(state.get("missing_fields", []))
    if not missing_fields:
        return detected_intent

    if (
        previous_intent is Intent.TRIP_PLAN
        and detected_intent in {Intent.GENERAL_QA, Intent.MODIFY_PLAN}
        and _looks_like_trip_preference_update(query, explicit_update)
    ):
        return previous_intent

    if detected_intent.value != "general_qa":
        return detected_intent

    slot_keys = {
        "destination": {"destination"},
        "destination_detail": {"destination"},
        "origin": {"origin"},
        "duration": {"days", "start_date", "end_date"},
        "people": {"people"},
        "budget": {"budget", "budget_scope", "budget_mode"},
        "budget_confirmation": {"budget", "budget_scope", "budget_mode"},
        "booking_type": {"booking_types"},
        "selected_option_ids": {"selected_option_ids"},
    }
    expected_keys = set().union(*(slot_keys.get(field, set()) for field in missing_fields))
    if expected_keys.intersection(explicit_update):
        return previous_intent
    return detected_intent


def _should_inherit_entities(
    state: TravelState,
    intent: Intent,
    query: str,
    explicit_update: dict,
) -> bool:
    """Carry slots only while completing the same pending task.

    Completed queries and plans must not leak their dates, people or budget into
    a new request. Modify and booking flows intentionally operate on the current
    structured plan, so they retain the saved entities.
    """
    if intent in {Intent.MODIFY_PLAN, Intent.BOOKING, Intent.BOOKING_CONFIRM}:
        return True
    if intent is Intent.TRIP_PLAN and any(marker in query for marker in FRESH_TRIP_MARKERS):
        return False
    if (
        intent is Intent.TRIP_PLAN
        and state.get("intent") is Intent.TRIP_PLAN
        and any(marker in query for marker in PENDING_PLAN_ADJUSTMENT_MARKERS)
    ):
        return True
    feasibility = state.get("budget_feasibility")
    if (
        intent is Intent.TRIP_PLAN
        and feasibility is not None
        and not feasibility.feasible
        and "budget" not in explicit_update
        and set(explicit_update).intersection(
            {"destination", "days", "start_date", "end_date", "people"}
        )
        and not any(marker in query for marker in PENDING_PLAN_ADJUSTMENT_MARKERS)
    ):
        return False
    return bool(
        state.get("missing_fields")
        and state.get("intent") == intent
    )


def _entity_base_for_turn(
    state: TravelState,
    previous: TravelEntities,
    intent: Intent,
    query: str,
    explicit_update: dict,
) -> TravelEntities:
    if _should_inherit_entities(state, intent, query, explicit_update):
        return previous
    if (
        intent in QUERY_INTENTS
        and previous.destination
        and any(marker in query for marker in DESTINATION_REFERENCE_MARKERS)
    ):
        return TravelEntities(
            destination=previous.destination,
            origin=previous.origin,
            currency=previous.currency,
        )
    return TravelEntities(currency=previous.currency)


def _sanitize_explicit_update(
    state: TravelState,
    query: str,
    explicit_update: dict,
) -> dict:
    """Reject volatile slots copied by an LLM from conversation context.

    Context helps resolve intent and references, but a budget or party size is
    considered explicit only when the current user message actually says it.
    """
    sanitized = _apply_explicit_budget_update(state, query, dict(explicit_update))
    if not _query_sets_budget(state, query):
        sanitized.pop("budget", None)
    sanitized = _apply_explicit_date_update(state, query, sanitized)
    if not _query_sets_people(query):
        sanitized.pop("people", None)
    if not _query_sets_duration(query):
        sanitized.pop("days", None)
    if not _query_sets_destination(state, query, sanitized.get("destination")):
        sanitized.pop("destination", None)
    if not _query_sets_origin(state, query, sanitized.get("origin")):
        sanitized.pop("origin", None)
    return sanitized


def _query_sets_people(query: str) -> bool:
    ordinary = (
        r"(?:\d{1,3}|[一二两三四五六七八九十])\s*(?:个|名)?(?:成年)?人|"
        r"独自|单人|情侣|夫妻|一家|亲子"
    )
    family_composition = (
        r"(?:\d{1,2}|[一二两三四五六七八九十])\s*(?:个)?(?:大人|成人|成年人|大)"
        r"\s*(?:[、,，和加+与]\s*)?"
        r"(?:\d{1,2}|[一二两三四五六七八九十])\s*(?:个)?(?:小孩|孩子|儿童|小)"
    )
    return bool(re.search(rf"(?:{ordinary})|(?:{family_composition})", query))


def _query_sets_duration(query: str) -> bool:
    return bool(
        resolve_explicit_dates(query)
        or re.search(
            r"(?:\d{1,2}|[一二两三四五六七八九十])\s*(?:天|日|个?周|个?星期)",
            query,
        )
    )


def _query_sets_destination(
    state: TravelState,
    query: str,
    destination: object | None,
) -> bool:
    if set(state.get("missing_fields", [])).intersection({"destination", "destination_detail"}):
        return True
    if destination and str(destination) in query:
        return True
    return bool(
        re.search(
            r"(?:想|要|准备|计划|打算)?(?:去|到|前往|飞往|改去|换去)|"
            r"目的地|(?:旅游|旅行|游玩|周边玩|日游|天游)",
            query,
        )
    )


def _query_sets_origin(
    state: TravelState,
    query: str,
    origin: object | None,
) -> bool:
    if "origin" in set(state.get("missing_fields", [])):
        return True
    if origin and str(origin) in query and re.search(r"从|由|出发", query):
        return True
    return bool(re.search(r"(?:从|由).{1,20}(?:出发|去|到|前往)|出发地", query))


def _query_sets_budget(state: TravelState, query: str) -> bool:
    if _is_relative_budget_change(query):
        return False
    return (
        _confirms_current_budget_cap(state, query)
        or _extract_budget_amount(state, query) is not None
        or _selected_estimate_tier(state, query) is not None
    )


def _apply_explicit_budget_update(
    state: TravelState,
    query: str,
    sanitized: dict,
) -> dict:
    if _confirms_current_budget_cap(state, query):
        previous = state.get("entities") or TravelEntities()
        sanitized["budget"] = previous.budget
        sanitized["budget_scope"] = previous.budget_scope
        sanitized["budget_mode"] = BudgetMode.MINIMIZE
        return sanitized
    if _is_relative_budget_change(query):
        sanitized.pop("budget", None)
        sanitized.pop("budget_scope", None)
        sanitized.pop("budget_mode", None)
        return sanitized
    estimate = state.get("budget_estimate")
    selected_tier = _selected_estimate_tier(state, query)
    amount = _extract_budget_amount(state, query)
    if selected_tier == "survival" and estimate is not None:
        amount = estimate.survival.total
    elif selected_tier == "comfortable" and estimate is not None:
        amount = estimate.comfortable.total

    if amount is not None:
        sanitized["budget"] = amount
        sanitized["budget_mode"] = (
            BudgetMode.MINIMIZE if selected_tier == "survival" else BudgetMode.FIXED
        )
        if _budget_scope_from_query(query) is not None:
            sanitized["budget_scope"] = _budget_scope_from_query(query)
        elif estimate is not None or set(state.get("missing_fields", [])).intersection(
            {"budget", "budget_confirmation"}
        ):
            sanitized["budget_scope"] = BudgetScope.TOTAL
    else:
        sanitized.pop("budget", None)
        scope = _budget_scope_from_query(query)
        if scope is not None:
            sanitized["budget_scope"] = scope
        else:
            sanitized.pop("budget_scope", None)
        if _requests_budget_estimate(query):
            sanitized["budget_mode"] = (
                BudgetMode.MINIMIZE if _requests_minimum_budget(query) else BudgetMode.ESTIMATE
            )
            sanitized.pop("budget_scope", None)
        elif "budget_mode" in sanitized:
            sanitized.pop("budget_mode", None)
    return sanitized


def _extract_budget_amount(state: TravelState, query: str) -> Decimal | None:
    if _is_relative_budget_change(query):
        return None
    number_token = r"\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百千万]+"
    budget_range = re.search(
        rf"(?:总预算|预算|费用)[^，。；]{{0,8}}?({number_token})\s*(?:元|块)?\s*"
        rf"(?:到|至|[-~～—])\s*({number_token})\s*(?:元|块)?",
        query,
    )
    if budget_range:
        return max(
            _parse_budget_number(budget_range.group(1)),
            _parse_budget_number(budget_range.group(2)),
        )

    number = rf"({number_token})"
    separator = r"[^，。；\d零〇一二两三四五六七八九十百千万]"
    patterns = [
        rf"(?:总预算|预算|人均|每人|总共){separator}{{0,8}}{number}",
        rf"{number}\s*(?:元|块)(?:左右|以内|上下)?",
    ]
    if set(state.get("missing_fields", [])).intersection({"budget", "budget_confirmation"}):
        patterns.extend(
            [
                rf"(?:那就|就按|就|按|控制在|定在|选)\s*{number}",
                rf"^\s*{number}\s*(?:元|块)?\s*(?:左右|以内|上下)?\s*(?:吧|就行|可以)?\s*$",
            ]
        )
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            return _parse_budget_number(match.group(1))
    return None


def _is_relative_budget_change(query: str) -> bool:
    return bool(re.search(r"预算.{0,4}(?:降低|减少|下调|提高|增加|上调)\s*\d", query))


def _confirms_current_budget_cap(state: TravelState, query: str) -> bool:
    previous = state.get("entities") or TravelEntities()
    if previous.budget is None:
        return False
    return bool(
        re.search(
            r"(?:我)?(?:就|只)?有这(?:点|些|么多)预算|"
            r"预算(?:不能|不再|没法|无法)(?:再)?(?:提高|增加|加)|"
            r"(?:不加|不提高|保持|按当前|就按这个)(?:预算|金额)|"
            r"预算不变|就这么多(?:钱|预算)|按这(?:点|个)预算",
            query,
        )
    )


def _budget_scope_from_query(query: str) -> BudgetScope | None:
    if re.search(r"人均|每人", query):
        return BudgetScope.PER_PERSON
    if re.search(r"总预算|总共|全部预算|整体预算|预算", query):
        return BudgetScope.TOTAL
    return None


def _requests_budget_estimate(query: str) -> bool:
    return bool(
        re.search(
            r"(?:估计|估算|估一下|算算|帮我算).{0,12}(?:预算|费用|多少钱)|"
            r"(?:预算|费用).{0,12}(?:估|算|多少|怎么定)|"
            r"(?:不知道|不清楚|没概念).{0,8}(?:预算|多少钱)|"
            r"需要多少(?:预算|钱)",
            query,
        )
    )


def _requests_minimum_budget(query: str) -> bool:
    return bool(
        re.search(
            r"尽可能少|越少越好|越省越好|最低预算|最省|穷游|能省则省|"
            r"只有这(?:点|些|么多)预算|预算不变|按当前预算",
            query,
        )
    )


def _selected_estimate_tier(state: TravelState, query: str) -> str | None:
    if state.get("budget_estimate") is None:
        return None
    if re.search(
        r"极限穷游|穷游版|最低预算|最省(?:方案|那档|版)?|预算再省(?:一)?点|再省(?:一)?点|便宜的",
        query,
    ):
        return "survival"
    if re.search(r"正常舒适|舒适版|舒服(?:一点|那档|版)?|正常玩", query):
        return "comfortable"
    return None


def _looks_like_trip_preference_update(query: str, explicit_update: dict) -> bool:
    if {"explicit_preferences", "explicit_dislikes"}.intersection(explicit_update):
        return True
    return bool(
        re.search(
            r"喜欢|不喜欢|不要|避开|多安排|少安排|想吃|爱吃|清淡|辣|海鲜|美食|徒步|拍照|早起|购物",
            query,
        )
    )


def _parse_budget_number(raw: str) -> Decimal:
    if re.fullmatch(r"\d+(?:\.\d+)?", raw):
        return Decimal(raw)
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    small_units = {"十": 10, "百": 100, "千": 1000}
    total = 0
    section = 0
    number = 0
    for character in raw:
        if character in digits:
            number = digits[character]
        elif character in small_units:
            section += (number or 1) * small_units[character]
            number = 0
        elif character == "万":
            total += (section + number or 1) * 10000
            section = 0
            number = 0
    return Decimal(total + section + number)


def _apply_explicit_date_update(
    state: TravelState,
    query: str,
    sanitized: dict,
) -> dict:
    del state
    resolved_dates = resolve_explicit_dates(query)
    if not resolved_dates:
        sanitized.pop("start_date", None)
        sanitized.pop("end_date", None)
        return sanitized

    start = resolved_dates[0]
    sanitized["start_date"] = start
    if len(resolved_dates) > 1:
        sanitized["end_date"] = resolved_dates[1]
    elif sanitized.get("days"):
        sanitized["end_date"] = start + timedelta(days=int(sanitized["days"]) - 1)
    else:
        sanitized.pop("end_date", None)
    return sanitized
