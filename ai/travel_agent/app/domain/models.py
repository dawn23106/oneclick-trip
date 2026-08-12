from __future__ import annotations

from datetime import UTC, date as Date, datetime as DateTime, time as Time
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Intent(StrEnum):
    """用户单轮输入的业务意图；该枚举限制 Supervisor 可接受的任务类型。"""

    UNKNOWN = "unknown"
    WEATHER_QUERY = "weather_query"
    HOTEL_QUERY = "hotel_query"
    TRANSPORT_QUERY = "transport_query"
    GENERAL_QA = "general_qa"
    TRIP_PLAN = "trip_plan"
    MODIFY_PLAN = "modify_plan"
    BOOKING = "booking"
    BOOKING_CONFIRM = "booking_confirm"
    MEMORY_MANAGE = "memory_manage"


class NextAction(StrEnum):
    """Supervisor 允许输出的下一步动作，防止模型直接指定任意图节点。"""
    LOAD_USER_MEMORY = "load_user_memory"
    RECOGNIZE_INTENT = "recognize_intent"
    NORMALIZE_STATE = "normalize_state"
    SUPERVISE = "supervise"
    ASK_USER = "ask_user"
    QUERY_FLOW = "query_flow"
    PLANNING_FLOW = "planning_flow"
    MODIFY_FLOW = "modify_flow"
    MEMORY_FLOW = "memory_flow"
    BOOKING_FLOW = "booking_flow"
    COMPLETE = "complete"
    ABORT = "abort"


class BudgetScope(StrEnum):
    """预算口径：整段行程总额或单人人均金额。"""
    TOTAL = "total"
    PER_PERSON = "per_person"


class BudgetMode(StrEnum):
    """预算输入方式：固定金额、由系统估算或尽可能节省。"""
    FIXED = "fixed"
    ESTIMATE = "estimate"
    MINIMIZE = "minimize"


class BookingStatus(StrEnum):
    """预订草稿从创建到确认、过期或取消的状态。"""
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ToolName(StrEnum):
    """Agent 可申请调用的工具白名单。"""
    KNOWLEDGE_SEARCH = "knowledge_search"
    TRAVEL_RESEARCH = "travel_research"
    XIAOHONGSHU_RESEARCH = "xiaohongshu_research"
    WEATHER = "weather"
    HOTEL_SEARCH = "hotel_search"
    TRAIN_SEARCH = "train_search"
    FLIGHT_SEARCH = "flight_search"
    POI_SEARCH = "poi_search"
    POI_COORDINATES = "poi_coordinates"
    ROUTE_MATRIX = "route_matrix"
    OPENING_HOURS = "opening_hours"
    TICKET = "ticket"


class ToolRecoveryAction(StrEnum):
    """工具失败后允许采用的受控恢复策略。"""
    RETRY = "retry"
    FALLBACK = "fallback"
    CONTINUE = "continue"
    ABORT = "abort"


class ToolDataMode(StrEnum):
    """Declares how fresh and authoritative a tool result is."""

    UNKNOWN = "UNKNOWN"
    REALTIME = "REALTIME"
    CACHE = "CACHE"
    MOCK = "MOCK"
    AI_KNOWLEDGE = "AI_KNOWLEDGE"
    FALLBACK = "FALLBACK"


class ReviewVerdict(StrEnum):
    """行程体验评审的最终判定。"""
    PASS = "pass"
    REVISE = "revise"


class ModifyImpact(StrEnum):
    """修改请求是否需要重新查询外部资料。"""
    SIMPLE = "simple"
    RESEARCH_REQUIRED = "research_required"


class DomainModel(BaseModel):
    """领域模型基类：拒绝未声明字段，避免 Agent 输出静默污染状态。"""
    model_config = ConfigDict(extra="forbid", frozen=False)


class TravelEntities(DomainModel):
    """从本轮自然语言中抽取的旅行槽位，而不是完整的 LangGraph 状态。

    该对象只描述用户明确表达的城市、日期、人数、预算、偏好及预订选择，
    随后作为 ``TravelState.entities`` 在节点之间传递。
    """

    destination: str | None = None
    origin: str | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    days: int | None = Field(default=None, ge=1, le=60)
    people: int | None = Field(default=None, ge=1, le=100)
    budget: Decimal | None = Field(default=None, ge=0)
    budget_scope: BudgetScope | None = None
    budget_mode: BudgetMode | None = None
    currency: str = "CNY"
    explicit_preferences: list[str] = Field(default_factory=list)
    explicit_dislikes: list[str] = Field(default_factory=list)
    selected_option_ids: list[str] = Field(default_factory=list)
    booking_types: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_date_order(self) -> TravelEntities:
        """阻止结束日期早于开始日期的无效实体进入后续规划流程。"""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date")
        return self


class MemoryItem(DomainModel):
    """一条可跨会话复用的用户旅行偏好。"""
    category: Literal[
        "pace", "budget_style", "food", "transport", "hotel", "activity", "avoidance", "tag"
    ]
    key: str
    value: str
    confidence: float = Field(ge=0, le=1)
    evidence: str


class MemoryOperation(MemoryItem):
    """对长期偏好执行新增、更新或删除的操作。"""
    action: Literal["upsert", "delete"]
    source: Literal["explicit", "repeated", "inferred"]


class MemoryExtraction(DomainModel):
    """记忆 Agent 从当前对话提取出的偏好变更集合。"""
    operations: list[MemoryOperation] = Field(default_factory=list)


class UserPreferences(DomainModel):
    """用户长期旅行画像及其持久化版本。"""
    liked_tags: list[str] = Field(default_factory=list)
    disliked_tags: list[str] = Field(default_factory=list)
    preferred_transport: list[str] = Field(default_factory=list)
    pace: str | None = None
    typical_budget_scope: BudgetScope | None = None
    memory_items: list[MemoryItem] = Field(default_factory=list)
    source_version: int = 0
    updated_at: DateTime = Field(default_factory=lambda: DateTime.now(UTC))


class IntentContext(DomainModel):
    """Compact conversation context supplied to the intent model."""

    recent_messages: list[str] = Field(default_factory=list)
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
    previous_intent: Intent = Intent.UNKNOWN
    pending_missing_fields: list[str] = Field(default_factory=list)
    current_plan_id: str | None = None
    current_plan_version: int | None = None
    booking_draft_id: str | None = None
    booking_status: BookingStatus | None = None


class IntentTask(DomainModel):
    """One independently answerable request extracted from the current turn."""

    task_id: str = ""
    query: str = Field(min_length=1, max_length=2000)
    intent: Intent
    entities: TravelEntities = Field(default_factory=TravelEntities)


class QueryToolCall(DomainModel):
    """复合查询中的一个任务与一个工具之间的调用关系。"""
    task_id: str
    tool_name: ToolName


class IntentDecision(DomainModel):
    """意图 Agent 的结构化输出，包含主意图、实体、置信度和复合任务。"""

    intent: Intent
    entities: TravelEntities = Field(default_factory=TravelEntities)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    advisory_missing_fields: list[str] = Field(default_factory=list)
    tasks: list[IntentTask] = Field(default_factory=list, max_length=8)


class ClarificationAction(DomainModel):
    """追问卡片中可直接选择的一项结构化操作。"""
    id: str = Field(min_length=1, max_length=48)
    field: str = Field(min_length=1, max_length=48)
    label: str = Field(min_length=1, max_length=24)
    message: str = Field(min_length=1, max_length=120)
    recommended: bool = False


class ClarificationReply(DomainModel):
    """缺失槽位时返回给用户的追问内容和快捷选项。"""
    kicker: str = Field(min_length=1, max_length=24)
    title: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=180)
    choice_prompt: str | None = Field(default=None, max_length=60)
    actions: list[ClarificationAction] = Field(default_factory=list, max_length=6)


class SelectedOptions(DomainModel):
    """当前方案中被选中且允许进入预订流程的候选 ID。"""
    poi_ids: list[str] = Field(default_factory=list)
    hotel_option_ids: list[str] = Field(default_factory=list)
    transport_option_ids: list[str] = Field(default_factory=list)
    ticket_option_ids: list[str] = Field(default_factory=list)


class POICandidate(DomainModel):
    """第一阶段调研得到的景点候选及其来源证据。"""
    poi_id: str
    name: str
    area: str
    tags: list[str] = Field(default_factory=list)
    suggested_duration_minutes: int = Field(ge=30)
    ticket_price: Decimal = Decimal("0")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coordinate_source: str | None = None
    coordinates_verified: bool = False
    source_document_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class HotelAreaCandidate(DomainModel):
    """住宿区域候选；这里只保存区域建议，不代表实时房型库存。"""
    area_id: str
    name: str
    reason: str
    nightly_price_hint: Decimal = Decimal("0")


class TransportCandidate(DomainModel):
    """跨城交通候选及其估算时长、价格。"""
    option_id: str
    mode: str
    name: str
    duration_minutes: int = Field(ge=0)
    price: Decimal = Decimal("0")


class ResearchSourceReference(DomainModel):
    """调研结论引用的外部资料及权威等级。"""
    title: str
    url: str
    source_tier: str
    authority_score: float = Field(ge=0, le=1)


class ResearchEvidenceClaim(DomainModel):
    """由多来源支持的可量化调研结论。"""
    metric: str
    lower: float
    upper: float
    unit: str
    source_count: int = Field(ge=1)
    source_urls: list[str] = Field(default_factory=list)
    corroborated: bool = False


class Phase1Research(DomainModel):
    """广度调研结果：天气、景点、住宿区域和交通候选。"""
    data_mode: str = "AI_KNOWLEDGE"
    destination: str
    weather_summary: str
    poi_candidates: list[POICandidate] = Field(default_factory=list)
    hotel_areas: list[HotelAreaCandidate] = Field(default_factory=list)
    transport_options: list[TransportCandidate] = Field(default_factory=list)
    research_sources: list[ResearchSourceReference] = Field(default_factory=list)
    evidence_claims: list[ResearchEvidenceClaim] = Field(default_factory=list)
    research_confidence: float | None = Field(default=None, ge=0, le=1)


class BudgetFeasibility(DomainModel):
    """用户预算与最低可行成本之间的确定性比较结果。"""
    feasible: bool
    budget_limit: Decimal = Field(ge=0)
    estimated_minimum: Decimal = Field(ge=0)
    transport_cost: Decimal = Field(default=Decimal("0"), ge=0)
    lodging_cost: Decimal = Field(default=Decimal("0"), ge=0)
    daily_basic_cost: Decimal = Field(default=Decimal("0"), ge=0)
    suggested_budget: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = "CNY"


class BudgetTierEstimate(DomainModel):
    """某一消费档次下按费用类别拆分的预算估算。"""
    name: str
    total: Decimal = Field(ge=0)
    intercity_transport: Decimal = Field(default=Decimal("0"), ge=0)
    lodging: Decimal = Field(default=Decimal("0"), ge=0)
    food: Decimal = Field(default=Decimal("0"), ge=0)
    local_transport: Decimal = Field(default=Decimal("0"), ge=0)
    tickets: Decimal = Field(default=Decimal("0"), ge=0)
    assumptions: list[str] = Field(default_factory=list)


class BudgetEstimate(DomainModel):
    """在用户未给出预算时提供的生存档与舒适档估算。"""
    survival: BudgetTierEstimate
    comfortable: BudgetTierEstimate
    currency: str = "CNY"
    data_mode: str = "AI_ESTIMATE"
    disclaimer: str = "基于 AI 通用知识的保守估算，不代表实时票价或房价。"


class CandidateVisit(DomainModel):
    """候选景点被安排到某日时的初步访问信息。"""
    poi_id: str
    visit_date: str
    estimated_duration_minutes: int = Field(ge=30)


class CandidateSelection(DomainModel):
    """预算和偏好筛选后进入深度调研的候选集合。"""
    selected_poi_ids: list[str] = Field(default_factory=list)
    selected_pois: list[CandidateVisit] = Field(default_factory=list)
    hotel_area_id: str | None = None
    transport_option_id: str | None = None
    destinations: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class RouteLeg(DomainModel):
    """两个行程地点之间的距离和预计通勤时间。"""
    from_id: str
    to_id: str
    distance_km: float = Field(ge=0)
    duration_minutes: int = Field(ge=0)


class POIVisitDetail(DomainModel):
    """深度调研得到的开放时间、门票和可用性信息。"""
    poi_id: str
    opening_hours: str
    ticket_option_id: str | None = None
    ticket_price: Decimal = Decimal("0")
    available: bool | None = None


class Phase2Research(DomainModel):
    """用于排程和硬校验的路线、开放时间与门票详情。"""
    data_mode: str = "AI_KNOWLEDGE"
    route_legs: list[RouteLeg] = Field(default_factory=list)
    poi_details: list[POIVisitDetail] = Field(default_factory=list)


class ItineraryItem(DomainModel):
    """逐日行程中的一个活动、餐饮、住宿或交通项目。"""
    item_id: str
    name: str
    item_type: str = "SPOT"
    start_at: DateTime | None = None
    end_at: DateTime | None = None
    start_time: Time | None = None
    end_time: Time | None = None
    location_id: str | None = None
    description: str | None = None
    travel_minutes: int = Field(default=0, ge=0)
    visit_minutes: int = Field(default=0, ge=0)
    ticket_option_id: str | None = None
    estimated_cost: Decimal = Decimal("0")


class ItineraryDay(DomainModel):
    """某一天的有序行程项目及当晚住宿选择。"""
    day_index: int = Field(ge=1)
    date: Date | None = None
    title: str | None = None
    summary: str | None = None
    items: list[ItineraryItem] = Field(default_factory=list)
    hotel_option_id: str | None = None


class TravelPlan(DomainModel):
    """经过规划与校验的完整版本化旅行方案。"""
    plan_id: str
    version: int = Field(ge=1)
    destination: str
    days: list[ItineraryDay] = Field(default_factory=list)
    hotel_area_id: str | None = None
    transport_option_id: str | None = None
    hotel_nights: int = Field(default=0, ge=0)
    assumptions: list[str] = Field(default_factory=list)
    total_cost: Decimal = Decimal("0")
    currency: str = "CNY"
    created_at: DateTime = Field(default_factory=lambda: DateTime.now(UTC))


class DirectPlanProposal(DomainModel):
    """缺少外部调研数据时由直接规划器给出的降级方案。"""
    feasible: bool
    plan: TravelPlan | None = None
    message: str = ""
    suggested_budget: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_plan_when_feasible(self) -> DirectPlanProposal:
        if self.feasible and self.plan is None:
            raise ValueError("plan is required when feasible is true")
        return self


class PersistedPlanState(DomainModel):
    """Validated business state required to modify or book a saved plan."""

    plan: TravelPlan
    entities: TravelEntities = Field(default_factory=TravelEntities)
    selected_options: SelectedOptions = Field(default_factory=SelectedOptions)
    candidate_selection: CandidateSelection | None = None
    phase1_research: Phase1Research | None = None
    phase2_research: Phase2Research | None = None


class ValidationIssue(DomainModel):
    """硬校验发现的结构化错误或警告。"""
    code: str
    message: str
    day_index: int | None = None
    item_id: str | None = None


class HardValidationResult(DomainModel):
    """代码规则对预算、日期、时间和路线等约束的校验结果。"""
    hard_pass: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class ReviewResult(DomainModel):
    """评审 Agent 对行程体验质量给出的评分和修订意见。"""
    verdict: ReviewVerdict
    score: int = Field(ge=0, le=100)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ModificationRequest(DomainModel):
    """从自然语言修改指令中解析出的确定性变更参数。"""
    target_day: int | None = Field(default=None, ge=1)
    target_period: str | None = None
    replacement_name: str | None = None
    budget_delta: Decimal | None = None
    new_budget: Decimal | None = Field(default=None, ge=0)
    remove_tags: list[str] = Field(default_factory=list)
    swap_days: tuple[int, int] | None = None


class ModifyAnalysis(DomainModel):
    """修改影响分析及其所需的重新调研工具。"""
    impact: ModifyImpact
    request: ModificationRequest = Field(default_factory=ModificationRequest)
    discovery_tools: list[ToolName] = Field(default_factory=list)
    dependent_tools: list[ToolName] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ModificationResult(DomainModel):
    """修改后尚待重新校验的方案、实体与候选集合。"""
    plan: TravelPlan
    entities: TravelEntities
    selection: CandidateSelection
    errors: list[str] = Field(default_factory=list)


class ToolResult(DomainModel):
    """所有外部工具统一返回的数据、来源、时效性和错误信封。"""
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    source: str = "unknown"
    data_mode: ToolDataMode = ToolDataMode.UNKNOWN
    confidence: float | None = Field(default=None, ge=0, le=1)
    fetched_at: DateTime = Field(default_factory=lambda: DateTime.now(UTC))
    bookable: bool = False
    error_code: str | None = None
    retryable: bool = False
    timestamp: DateTime = Field(default_factory=lambda: DateTime.now(UTC))

    @model_validator(mode="before")
    @classmethod
    def promote_legacy_metadata(cls, value: Any) -> Any:
        """Keep old tool adapters readable while metadata moves to the envelope."""
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        data = normalized.get("data")
        if isinstance(data, dict):
            normalized.setdefault("source", data.get("source", "unknown"))
            normalized.setdefault("data_mode", data.get("data_mode", ToolDataMode.UNKNOWN))
        return normalized


class ToolError(DomainModel):
    """可在图中累积并用于重试或降级判断的工具错误。"""
    tool_name: str
    error_code: str
    message: str
    retryable: bool = False
    attempt: int = Field(default=1, ge=1, le=2)
    timestamp: DateTime = Field(default_factory=lambda: DateTime.now(UTC))


class BookingDraft(DomainModel):
    """Reference returned by the Java backend; never stores security tokens."""

    draft_id: str
    status: BookingStatus
    conversation_id: str
    user_id: str
    plan_id: str
    plan_version: int = Field(ge=1)
    booking_types: list[str] = Field(default_factory=list)
    selected_option_ids: list[str] = Field(default_factory=list)
    created_at: DateTime = Field(default_factory=lambda: DateTime.now(UTC))
    expires_at: DateTime
