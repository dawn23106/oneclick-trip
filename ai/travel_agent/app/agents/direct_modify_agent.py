from __future__ import annotations

import json
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.direct_planner_agent import LangChainDirectPlannerAgent
from app.agents.modify_agent import RuleBasedModifyAgent, RuleBasedModifyAnalyzerAgent
from app.domain.models import (
    DirectPlanProposal,
    POICandidate,
    TravelEntities,
    TravelPlan,
    UserPreferences,
)


class DirectModifyAgent(Protocol):
    def modify(
        self,
        *,
        query: str,
        conversation_id: str,
        current_plan: TravelPlan,
        entities: TravelEntities,
        preferences: UserPreferences,
        conversation_context: list[str] | None = None,
        research_context: dict | None = None,
    ) -> TravelPlan:
        """Modify a plan directly without synthetic discovery tools."""

    async def amodify(self, **kwargs) -> TravelPlan:
        """Asynchronous direct modification."""


class LangChainDirectModifyAgent:
    def __init__(self, model: BaseChatModel) -> None:
        self._runner = model.with_structured_output(TravelPlan, method="json_mode")

    def modify(self, **kwargs) -> TravelPlan:
        result = self._runner.invoke(self._messages(**kwargs))
        plan = result if isinstance(result, TravelPlan) else TravelPlan.model_validate(result)
        return self._normalize(plan, **kwargs)

    async def amodify(self, **kwargs) -> TravelPlan:
        result = await self._runner.ainvoke(self._messages(**kwargs))
        plan = result if isinstance(result, TravelPlan) else TravelPlan.model_validate(result)
        return self._normalize(plan, **kwargs)

    @staticmethod
    def _messages(
        *,
        query: str,
        conversation_id: str,
        current_plan: TravelPlan,
        entities: TravelEntities,
        preferences: UserPreferences,
        conversation_context: list[str] | None = None,
        research_context: dict | None = None,
    ) -> list[SystemMessage | HumanMessage]:
        del conversation_id
        return [
            SystemMessage(
                content=(
                    "你是一键游的行程修改 Agent。根据用户要求定位具体 day_index、时段或活动，修改当前 TravelPlan。"
                    "保留未受影响的安排；需要替换地点时可以使用通用知识补充用户点名的真实地点，但不得"
                    "宣称营业时间、价格、余量或路线为实时信息。输出完整新方案，不要只返回差异。"
                    "提供联网研究证据时优先依据官方与可信来源；若证据不支持用户点名地点，"
                    "不得凭空补造该地点的营业状态、路线和价格。"
                    "保留 plan_id，version 在当前版本基础上加 1。"
                    "未受修改影响的 hotel_area_id、transport_option_id、hotel_option_id 和 ticket_option_id"
                    "必须从当前方案原样保留；只有被替换项目自己的 ticket_option_id 才清空。价格只能是 AI 估算。"
                    "只输出 JSON，不要使用 Markdown。输出必须符合以下 JSON Schema："
                    f"{json.dumps(TravelPlan.model_json_schema(), ensure_ascii=False)}"
                )
            ),
            HumanMessage(
                content=(
                    f"修改要求：{query}\n需求：{entities.model_dump_json()}\n"
                    f"最近 20 轮对话：{conversation_context or []}\n"
                    f"偏好：{preferences.model_dump_json()}\n"
                    f"联网研究证据：{json.dumps(research_context or {}, ensure_ascii=False)}\n"
                    f"当前方案：{current_plan.model_dump_json()}"
                )
            ),
        ]

    @staticmethod
    def _normalize(
        plan: TravelPlan,
        *,
        query: str,
        conversation_id: str,
        current_plan: TravelPlan,
        entities: TravelEntities,
        preferences: UserPreferences,
        conversation_context: list[str] | None = None,
        research_context: dict | None = None,
    ) -> TravelPlan:
        del conversation_context, research_context
        proposal = LangChainDirectPlannerAgent._normalize(
            DirectPlanProposal(feasible=True, plan=plan),
            query=query,
            conversation_id=conversation_id,
            current_version=current_plan.version,
            entities=entities,
            preferences=preferences,
        )
        normalized = proposal.plan
        if normalized is None:
            raise ValueError("direct modifier did not return a plan")
        normalized = normalized.model_copy(update={"plan_id": current_plan.plan_id})
        normalized = LangChainDirectModifyAgent._enforce_named_replacement(
            normalized,
            query=query,
            current_plan=current_plan,
            entities=entities,
        )
        return LangChainDirectModifyAgent._preserve_unaffected_options(
            normalized,
            current_plan,
        )

    @staticmethod
    def _enforce_named_replacement(
        plan: TravelPlan,
        *,
        query: str,
        current_plan: TravelPlan,
        entities: TravelEntities,
    ) -> TravelPlan:
        analyzer = RuleBasedModifyAnalyzerAgent()
        analysis = analyzer.analyze(query, current_plan, entities)
        request = analysis.request
        if not request.replacement_name:
            return plan
        target_day = next(
            (day for day in plan.days if day.day_index == request.target_day),
            None,
        )
        if target_day and any(
            request.replacement_name in item.name for item in target_day.items
        ):
            return plan
        candidate = POICandidate(
            poi_id="AI-REPLACEMENT",
            name=request.replacement_name,
            area="待核实",
            tags=[],
            suggested_duration_minutes=120,
        )
        modifier = RuleBasedModifyAgent()
        result = modifier.apply(plan, analysis, entities, [candidate])
        if not result.errors:
            return result.plan
        fallback = modifier.apply(
            current_plan.model_copy(deep=True),
            analysis,
            entities,
            [candidate],
        )
        if fallback.errors:
            raise ValueError(",".join(fallback.errors))
        fallback.plan.version = plan.version
        fallback.plan.total_cost = plan.total_cost
        return fallback.plan

    @staticmethod
    def _preserve_unaffected_options(
        plan: TravelPlan,
        current_plan: TravelPlan,
    ) -> TravelPlan:
        revised = plan.model_copy(deep=True)
        revised.hotel_area_id = revised.hotel_area_id or current_plan.hotel_area_id
        revised.transport_option_id = (
            revised.transport_option_id or current_plan.transport_option_id
        )
        current_days = {day.day_index: day for day in current_plan.days}
        for day in revised.days:
            current_day = current_days.get(day.day_index)
            if current_day is None:
                continue
            day.hotel_option_id = day.hotel_option_id or current_day.hotel_option_id
            current_items = {
                item.location_id: item
                for item in current_day.items
                if item.location_id
            }
            for item in day.items:
                previous = current_items.get(item.location_id or "")
                if previous and item.ticket_option_id is None:
                    item.ticket_option_id = previous.ticket_option_id
        return revised


class RuleBasedDirectModifyAgent:
    def __init__(self) -> None:
        self._analyzer = RuleBasedModifyAnalyzerAgent()
        self._modifier = RuleBasedModifyAgent()

    def modify(
        self,
        *,
        query: str,
        conversation_id: str,
        current_plan: TravelPlan,
        entities: TravelEntities,
        preferences: UserPreferences,
        conversation_context: list[str] | None = None,
        research_context: dict | None = None,
    ) -> TravelPlan:
        del conversation_id, preferences, conversation_context, research_context
        analysis = self._analyzer.analyze(query, current_plan, entities)
        candidates = []
        if analysis.request.replacement_name:
            candidates.append(
                POICandidate(
                    poi_id="AI-REPLACEMENT",
                    name=analysis.request.replacement_name,
                    area="待核实",
                    tags=[],
                    suggested_duration_minutes=120,
                )
            )
        result = self._modifier.apply(current_plan, analysis, entities, candidates)
        if result.errors:
            raise ValueError(",".join(result.errors))
        result.plan.version = current_plan.version + 1
        return result.plan

    async def amodify(self, **kwargs) -> TravelPlan:
        return self.modify(**kwargs)
