from __future__ import annotations

import json
from datetime import UTC, datetime as DateTime
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from app.prompt_policy import AGENT_SECURITY_POLICY

from app.domain.models import (
    MemoryExtraction,
    MemoryItem,
    MemoryOperation,
    TravelEntities,
    TravelPlan,
    UserPreferences,
)


class PlanPreferenceAgent(Protocol):
    def extract(
        self,
        *,
        plan: TravelPlan,
        entities: TravelEntities,
        preferences: UserPreferences,
    ) -> MemoryExtraction: ...

    async def aextract(self, **kwargs) -> MemoryExtraction: ...


class LangChainPlanPreferenceAgent:
    def __init__(self, model: BaseChatModel) -> None:
        self._runner = model.with_structured_output(MemoryExtraction, method="json_mode")

    def extract(self, **kwargs) -> MemoryExtraction:
        return self._normalize(self._runner.invoke(self._messages(**kwargs)))

    async def aextract(self, **kwargs) -> MemoryExtraction:
        return self._normalize(await self._runner.ainvoke(self._messages(**kwargs)))

    @staticmethod
    def _messages(
        *, plan: TravelPlan, entities: TravelEntities, preferences: UserPreferences
    ) -> list:
        return [
            SystemMessage(
                content=AGENT_SECURITY_POLICY + (
                    "你负责从用户保存的旅行行程中提取可复用的旅行倾向。"
                    "只提取节奏、预算风格、美食、交通、住宿、活动和避雷倾向；"
                    "不要把目的地本身当成长期偏好，不要推断敏感属性。"
                    "行程只是弱行为证据，置信度必须在0.55到0.75之间。"
                    "最多返回6个upsert操作，source固定为inferred，不得返回delete。"
                    f"输出结构：{json.dumps(MemoryExtraction.model_json_schema(), ensure_ascii=False)}"
                )
            ),
            HumanMessage(
                content=(
                    f"行程：{plan.model_dump_json()}\n"
                    f"本次需求：{entities.model_dump_json()}\n"
                    f"已有长期偏好：{preferences.model_dump_json()}"
                )
            ),
        ]

    @staticmethod
    def _normalize(value) -> MemoryExtraction:
        extraction = (
            value
            if isinstance(value, MemoryExtraction)
            else MemoryExtraction.model_validate(value)
        )
        safe = []
        for operation in extraction.operations[:6]:
            if operation.action != "upsert":
                continue
            operation.source = "inferred"
            operation.confidence = min(0.75, max(0.55, operation.confidence))
            safe.append(operation)
        return MemoryExtraction(operations=safe)


class RuleBasedPlanPreferenceAgent:
    def extract(self, *, plan, entities, preferences) -> MemoryExtraction:
        del preferences
        items = [item for day in plan.days for item in day.items]
        operations: list[MemoryOperation] = []
        days = max(len(plan.days), 1)
        food_count = sum(item.item_type.upper() == "FOOD" for item in items)
        activity_count = sum(item.item_type.upper() not in {"FOOD", "HOTEL", "TRANSPORT"} for item in items)
        if food_count >= days:
            operations.append(_operation("food", "本地美食", 0.65, plan))
        average_activities = activity_count / days
        if average_activities <= 3:
            operations.append(_operation("pace", "轻松", 0.62, plan))
        elif average_activities >= 5:
            operations.append(_operation("pace", "紧凑", 0.62, plan))
        text = " ".join(f"{item.name} {item.description or ''}" for item in items)
        for value, markers in {
            "自然风光": ("山", "湖", "公园", "徒步", "森林", "海滩"),
            "历史文化": ("博物馆", "古城", "遗址", "寺", "历史", "文化"),
            "城市漫游": ("街区", "步行", "老街", "市集", "夜市"),
        }.items():
            if any(marker in text for marker in markers):
                operations.append(_operation("activity", value, 0.62, plan))
        transport = plan.transport_option_id or ""
        if transport.startswith("TRAIN-"):
            operations.append(_operation("transport", "高铁", 0.6, plan))
        elif transport.startswith("FLIGHT-"):
            operations.append(_operation("transport", "飞机", 0.6, plan))
        if entities.budget_mode is not None:
            value = "性价比" if entities.budget_mode.value == "minimize" else "品质优先"
            operations.append(_operation("budget_style", value, 0.58, plan))
        return MemoryExtraction(operations=operations[:6])

    async def aextract(self, **kwargs) -> MemoryExtraction:
        return self.extract(**kwargs)


def merge_inferred_plan_preferences(
    current: UserPreferences,
    extraction: MemoryExtraction,
) -> UserPreferences:
    updated = current.model_copy(deep=True)
    items = list(updated.memory_items)
    changed = False
    for operation in extraction.operations[:6]:
        if operation.action != "upsert" or operation.source != "inferred":
            continue
        value = operation.value.strip()
        if not value:
            continue
        key = f"plan:{operation.category}:{value}"
        existing = next(
            (item for item in items if item.category == operation.category and item.key == key),
            None,
        )
        confidence = min(
            0.95,
            max(operation.confidence, existing.confidence + 0.2 if existing else 0.0),
        )
        learned = MemoryItem(
            category=operation.category,
            key=key,
            value=value,
            confidence=confidence,
            evidence=operation.evidence,
        )
        items = [
            item for item in items
            if not (item.category == learned.category and item.key == learned.key)
        ]
        items.append(learned)
        changed = True
        if confidence < 0.8:
            continue
        if operation.category == "pace" and updated.pace is None:
            updated.pace = value
        elif operation.category == "transport" and value not in updated.preferred_transport:
            updated.preferred_transport.append(value)
        elif operation.category in {"food", "hotel", "activity", "tag"} and value not in updated.liked_tags:
            updated.liked_tags.append(value)
    if changed:
        updated.memory_items = items
        updated.source_version = current.source_version + 1
        updated.updated_at = DateTime.now(UTC)
    return updated


def _operation(category: str, value: str, confidence: float, plan: TravelPlan) -> MemoryOperation:
    return MemoryOperation(
        action="upsert",
        source="inferred",
        category=category,
        key=f"plan:{category}:{value}",
        value=value,
        confidence=confidence,
        evidence=f"已保存行程“{plan.destination}”V{plan.version}中反复体现该倾向",
    )
