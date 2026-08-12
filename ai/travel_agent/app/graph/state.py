from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, TypeAlias

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.domain.models import (
    BookingDraft,
    BudgetEstimate,
    BudgetFeasibility,
    CandidateSelection,
    ClarificationReply,
    HardValidationResult,
    Intent,
    IntentTask,
    MemoryExtraction,
    MemoryOperation,
    ModifyAnalysis,
    NextAction,
    Phase1Research,
    Phase2Research,
    QueryToolCall,
    ReviewResult,
    SelectedOptions,
    ToolError,
    ToolResult,
    TravelEntities,
    TravelPlan,
    UserPreferences,
)


def merge_tool_results(
    current: Mapping[str, ToolResult] | None,
    update: Mapping[str, ToolResult] | None,
) -> dict[str, ToolResult]:
    """按工具名合并并行节点结果，同名工具以本轮更新为准。"""
    merged = dict(current or {})
    merged.update(update or {})
    return merged


def merge_query_task_results(
    current: Mapping[str, Mapping[str, ToolResult]] | None,
    update: Mapping[str, Mapping[str, ToolResult]] | None,
) -> dict[str, dict[str, ToolResult]]:
    """按任务 ID 和工具名两级合并复合查询的执行结果。"""
    merged = {
        task_id: dict(results)
        for task_id, results in (current or {}).items()
    }
    for task_id, results in (update or {}).items():
        merged.setdefault(task_id, {}).update(results)
    return merged


def merge_tool_errors(
    current: Sequence[ToolError] | None,
    update: Sequence[ToolError] | None,
) -> list[ToolError]:
    """追加各并行分支产生的工具错误，保留完整诊断信息。"""
    return [*(current or []), *(update or [])]


def merge_tool_attempts(
    current: Mapping[str, int] | None,
    update: Mapping[str, int] | None,
) -> dict[str, int]:
    """合并工具重试计数，并保留各工具已观察到的最大次数。"""
    merged = dict(current or {})
    for name, attempts in (update or {}).items():
        merged[name] = max(merged.get(name, 0), attempts)
    return merged


def merge_unique_strings(
    current: Sequence[str] | None,
    update: Sequence[str] | None,
) -> list[str]:
    """有序去重地合并字符串列表，避免并行分支重复登记工具。"""
    return list(dict.fromkeys([*(current or []), *(update or [])]))


def merge_abort_flag(current: bool | None, update: bool | None) -> bool:
    """只要任一并行分支要求中止，就保持全局中止状态。"""
    return bool(current) or bool(update)


class TravelState(TypedDict, total=False):
    """LangGraph 全流程共享状态。

    它除 ``entities`` 外，还保存消息、调研、方案、校验、工具、预订和路由状态；
    节点应只返回自己负责字段组成的 ``TravelStatePatch``。
    """

    conversation_id: str
    user_id: str
    ignore_user_preferences: bool
    messages: Annotated[list[AnyMessage], add_messages]
    intent: Intent
    intent_confidence: float
    intent_tasks: list[IntentTask]
    query_tool_calls: list[QueryToolCall]
    active_query_task: IntentTask | None
    entities: TravelEntities
    missing_fields: list[str]
    clarification_reply: ClarificationReply | None
    user_preferences: UserPreferences
    effective_preferences: UserPreferences
    memory_errors: list[str]
    memory_candidates: MemoryExtraction | None
    memory_operations: list[MemoryOperation]
    memory_updated: bool
    current_plan: TravelPlan | None
    plan_draft: TravelPlan | None
    plan_version: int | None
    phase1_research: Phase1Research | None
    budget_feasibility: BudgetFeasibility | None
    budget_estimate: BudgetEstimate | None
    candidate_selection: CandidateSelection | None
    candidate_validation_errors: list[str]
    phase2_research: Phase2Research | None
    planning_errors: list[str]
    modify_analysis: ModifyAnalysis | None
    modification_errors: list[str]
    hard_validation: HardValidationResult | None
    review_result: ReviewResult | None
    plan_saved: bool
    validation_exhausted: bool
    selected_options: SelectedOptions
    selected_tools: Annotated[list[str], merge_unique_strings]
    pending_tools: list[str]
    active_tool: str | None
    tool_results: Annotated[dict[str, ToolResult], merge_tool_results]
    query_task_results: Annotated[
        dict[str, dict[str, ToolResult]],
        merge_query_task_results,
    ]
    tool_errors: Annotated[list[ToolError], merge_tool_errors]
    tool_attempts: Annotated[dict[str, int], merge_tool_attempts]
    tool_abort_requested: Annotated[bool, merge_abort_flag]
    booking_draft: BookingDraft | None
    booking_errors: list[str]
    booking_confirmation: bool | None
    booking_interrupted: bool
    booking_completed: bool
    revision_count: int
    code_repair_attempted: bool
    next_action: NextAction
    checkpoint_version: int


TravelStatePatch: TypeAlias = TravelState


def build_initial_state(conversation_id: str, user_id: str) -> TravelState:
    """为新会话创建字段完整、可安全进入任意节点的初始状态。"""
    return {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "ignore_user_preferences": False,
        "messages": [],
        "intent": Intent.UNKNOWN,
        "intent_confidence": 0.0,
        "intent_tasks": [],
        "query_tool_calls": [],
        "active_query_task": None,
        "entities": TravelEntities(),
        "missing_fields": [],
        "clarification_reply": None,
        "user_preferences": UserPreferences(),
        "effective_preferences": UserPreferences(),
        "memory_errors": [],
        "memory_candidates": None,
        "memory_operations": [],
        "memory_updated": False,
        "current_plan": None,
        "plan_draft": None,
        "plan_version": None,
        "phase1_research": None,
        "budget_feasibility": None,
        "budget_estimate": None,
        "candidate_selection": None,
        "candidate_validation_errors": [],
        "phase2_research": None,
        "planning_errors": [],
        "modify_analysis": None,
        "modification_errors": [],
        "hard_validation": None,
        "review_result": None,
        "plan_saved": False,
        "validation_exhausted": False,
        "selected_options": SelectedOptions(),
        "selected_tools": [],
        "pending_tools": [],
        "active_tool": None,
        "tool_results": {},
        "query_task_results": {},
        "tool_errors": [],
        "tool_attempts": {},
        "tool_abort_requested": False,
        "booking_draft": None,
        "booking_errors": [],
        "booking_confirmation": None,
        "booking_interrupted": False,
        "booking_completed": False,
        "revision_count": 0,
        "code_repair_attempted": False,
        "next_action": NextAction.LOAD_USER_MEMORY,
        "checkpoint_version": 0,
    }
