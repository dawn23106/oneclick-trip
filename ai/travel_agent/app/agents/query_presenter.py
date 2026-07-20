from __future__ import annotations

import json
import re
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.domain.models import Intent, ToolName, ToolResult, TravelEntities


class QueryPresenterAgent(Protocol):
    def present(
        self,
        query: str,
        intent: Intent,
        entities: TravelEntities,
        results: dict[str, ToolResult],
        conversation_context: list[str] | None = None,
    ) -> str:
        """Turn grounded tool data into a direct user-facing answer."""

    async def apresent(
        self,
        query: str,
        intent: Intent,
        entities: TravelEntities,
        results: dict[str, ToolResult],
        conversation_context: list[str] | None = None,
    ) -> str:
        """Asynchronous result presentation."""


class LangChainQueryPresenterAgent:
    """Flash-class presenter for narrow information queries."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    def present(
        self,
        query: str,
        intent: Intent,
        entities: TravelEntities,
        results: dict[str, ToolResult],
        conversation_context: list[str] | None = None,
    ) -> str:
        reply = self._content(
            self._model.invoke(
                self._messages(query, intent, entities, results, conversation_context)
            )
        )
        self._validate_grounding(reply, results)
        return reply

    async def apresent(
        self,
        query: str,
        intent: Intent,
        entities: TravelEntities,
        results: dict[str, ToolResult],
        conversation_context: list[str] | None = None,
    ) -> str:
        response = await self._model.ainvoke(
            self._messages(query, intent, entities, results, conversation_context)
        )
        reply = self._content(response)
        self._validate_grounding(reply, results)
        return reply

    @staticmethod
    def _messages(
        query: str,
        intent: Intent,
        entities: TravelEntities,
        results: dict[str, ToolResult],
        conversation_context: list[str] | None = None,
    ) -> list[SystemMessage | HumanMessage]:
        successful = {
            name: _presenter_result_payload(name, result)
            for name, result in results.items()
            if result.success
        }
        has_web_research = any(
            name in successful
            for name in (
                ToolName.TRAVEL_RESEARCH.value,
                ToolName.XIAOHONGSHU_RESEARCH.value,
            )
        )
        source_rule = (
            (
                "当前有联网研究结果，只能依据结果中的标题、摘要、正文和来源链接回答。"
                "优先使用 official 来源，并在答案末尾按官网/全网与小红书分组列出实际使用的来源链接。"
                "小红书内容是社区经验，不能覆盖官方安全规定。"
                "联网攻略不等于供应商实时库存，不能据此声称实时价格、余量、班次或可预订。"
            )
            if has_web_research
            else "当前有接口结果时只能依据结果回答，不得补造任何事实。"
            if successful
            else (
                "当前没有调用数据接口，请直接使用你的通用知识回答。必须明确说明这是 AI 知识建议，"
                "不是实时搜索；不得编造实时价格、余量、班次、营业状态或预订结果。"
            )
        )
        return [
            SystemMessage(
                content=(
                    "你是一键游的旅行咨询 Agent。只回答用户当前的单项问题，不要强行生成完整行程，"
                    "也不要追问与本次查询无关的预算、人数或旅行天数。"
                    f"{source_rule}"
                    "数据模式为 MOCK/DEMO 时，只针对该接口结果说明这是演示数据。"
                    "保留用户原话中的相对日期；工具结果没有具体日期时，绝不能自行换算或补充年月日。"
                    "回答使用自然、简洁的中文，先给结论，再列两三条有用信息；不要提内部节点、JSON 或工具名。"
                )
            ),
            HumanMessage(
                content=(
                    f"意图：{intent.value}\n"
                    f"用户原始问题：{query}\n"
                    f"查询条件：{entities.model_dump_json()}\n"
                    f"最近 20 轮对话：{conversation_context or []}\n"
                    f"可用结果：{successful}"
                )
            ),
        ]

    @staticmethod
    def _content(response) -> str:
        content = response.content
        if isinstance(content, str) and content.strip():
            return content.strip()
        raise ValueError("query presenter returned empty content")

    @staticmethod
    def _validate_grounding(reply: str, results: dict[str, ToolResult]) -> None:
        """Reject concrete dates that are absent from every tool result."""
        if not any(result.success for result in results.values()):
            return
        dates = list(
            re.finditer(r"(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日", reply)
        )
        if not dates:
            return
        source = json.dumps(
            {
                name: result.data
                for name, result in results.items()
                if result.success
            },
            ensure_ascii=False,
        )
        source_dates = {
            (int(year), int(month), int(day))
            for year, month, day in re.findall(r"(20\d{2})-(\d{2})-(\d{2})", source)
        }
        source_dates.update(
            (int(year), int(month), int(day))
            for year, month, day in re.findall(
                r"(20\d{2})年(\d{1,2})月(\d{1,2})日", source
            )
        )
        for match in dates:
            year = int(match.group(1)) if match.group(1) else None
            month = int(match.group(2))
            day = int(match.group(3))
            grounded = (
                (year, month, day) in source_dates
                if year is not None
                else any(
                    source_month == month and source_day == day
                    for _, source_month, source_day in source_dates
                )
            )
            if not grounded:
                raise ValueError("query presenter introduced an ungrounded date")


class RuleBasedQueryPresenterAgent:
    """Grounded deterministic fallback for query presentation."""

    def present(
        self,
        query: str,
        intent: Intent,
        entities: TravelEntities,
        results: dict[str, ToolResult],
        conversation_context: list[str] | None = None,
    ) -> str:
        del conversation_context
        if not results:
            return (
                "当前没有可用的大模型回答，且我没有使用 Mock 景点、交通或酒店数据。"
                "请确认 DeepSeek 服务后再试。"
            )
        del entities
        if intent is Intent.WEATHER_QUERY:
            return self._weather(results)
        if intent is Intent.HOTEL_QUERY:
            return self._hotel(results)
        if intent is Intent.TRANSPORT_QUERY:
            return self._transport(results)
        return self._research(query, results)

    async def apresent(
        self,
        query: str,
        intent: Intent,
        entities: TravelEntities,
        results: dict[str, ToolResult],
        conversation_context: list[str] | None = None,
    ) -> str:
        return self.present(query, intent, entities, results, conversation_context)

    @staticmethod
    def _weather(results: dict[str, ToolResult]) -> str:
        result = results.get(ToolName.WEATHER.value)
        if not result or not result.success:
            return "暂时没有可用的天气信息，请稍后再试。"
        source = result.source if result.source != "unknown" else "天气服务"
        return f"{result.data.get('summary', '暂无天气摘要')}（来源：{source}）"

    @staticmethod
    def _hotel(results: dict[str, ToolResult]) -> str:
        result = results.get(ToolName.HOTEL_SEARCH.value)
        if not result or not result.success:
            return "暂时没有可用的住宿区域信息，请稍后再试。"
        lines = ["以下是 MOCK 演示数据，住宿区域可以优先看看："]
        lines.extend(
            f"- {area['name']}：{area['reason']}，参考每晚 {area['nightly_price_hint']} 元"
            for area in result.data.get("areas", [])
        )
        return "\n".join(lines)

    @staticmethod
    def _transport(results: dict[str, ToolResult]) -> str:
        options = []
        for tool in (ToolName.TRAIN_SEARCH, ToolName.FLIGHT_SEARCH):
            result = results.get(tool.value)
            if result and result.success:
                options.extend(result.data.get("options", []))
        if not options:
            return "暂时没有可用的城际交通方案，请稍后再试。"
        lines = ["以下是 MOCK 演示数据，交通方案可以这样比较："]
        lines.extend(
            f"- {option['name']}：约 {option['duration_minutes']} 分钟，参考价 {option['price']} 元"
            for option in options
        )
        return "\n".join(lines)

    @staticmethod
    def _research(query: str, results: dict[str, ToolResult]) -> str:
        research = results.get(ToolName.TRAVEL_RESEARCH.value)
        xiaohongshu = results.get(ToolName.XIAOHONGSHU_RESEARCH.value)
        lines = []
        if xiaohongshu and xiaohongshu.success:
            items = xiaohongshu.data.get("items", [])
            detailed = [
                item
                for item in items
                if item.get("summary")
                and not str(item["summary"]).startswith("作者：")
            ][:2]
            lines.append(f"关于“{query}”，先看这次检索到的游客经验：")
            if detailed:
                lines.extend(
                    f"- {item['title']}：{_compact_text(item['summary'], 90)}"
                    for item in detailed
                )
            else:
                lines.extend(f"- {item['title']}" for item in items[:3])
            lines.append("这些是社区个人经历，体力、季节和路线不同会造成明显差异。")
        if research and research.success:
            items = research.data.get("items", [])[:4]
            lines.append("官网与全网资料：")
            lines.extend(
                f"- {item['title']}：{item['url']}"
                for item in items
                if item.get("title") and item.get("url")
            )
        if xiaohongshu and xiaohongshu.success:
            items = xiaohongshu.data.get("items", [])[:4]
            lines.append(
                f"小红书已搜索 {xiaohongshu.data.get('count', 0)} 篇，"
                f"精读 {xiaohongshu.data.get('detail_count', 0)} 篇："
            )
            lines.extend(
                f"- {item['title']}（{item.get('author', '未知作者')}，"
                f"{item.get('likes', 0)} 赞）：{item['url']}"
                for item in items
                if item.get("title") and item.get("url")
            )
        if lines:
            return "\n".join(lines)
        result = results.get(ToolName.POI_SEARCH.value)
        if not result or not result.success:
            return "暂时没有可用的旅游资料，请稍后再试。"
        lines = ["以下是 MOCK 演示数据，可以先关注这些地方："]
        lines.extend(
            f"- {poi['name']}：{', '.join(poi.get('tags', []))}"
            for poi in result.data.get("candidates", [])[:5]
        )
        return "\n".join(lines)


def _presenter_result_payload(name: str, result: ToolResult) -> dict:
    payload = result.model_dump(mode="json")
    if name not in {
        ToolName.TRAVEL_RESEARCH.value,
        ToolName.XIAOHONGSHU_RESEARCH.value,
    }:
        return payload
    data = result.data
    payload["data"] = {
        "query": data.get("query"),
        "count": data.get("count", 0),
        "detail_count": data.get("detail_count", 0),
        "items": [
            {
                key: (_compact_text(value, 500) if key == "summary" else value)
                for key, value in item.items()
                if key
                in {
                    "title",
                    "url",
                    "summary",
                    "published_at",
                    "source_tier",
                    "authority_score",
                    "author",
                    "likes",
                    "collects",
                    "comments",
                    "tags",
                }
            }
            for item in data.get("items", [])[:6]
        ],
        "quality": data.get("quality", {}),
        "platform_status": data.get("platform_status", {}),
    }
    return payload


def _compact_text(value, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."
