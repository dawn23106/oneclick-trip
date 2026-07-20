from langchain_core.runnables import Runnable, RunnableLambda

from app.agents.research_agent import Phase1ResearchAgent, Phase2ResearchAgent
from app.domain.models import (
    RouteLeg,
    ToolDataMode,
    ToolName,
    TravelEntities,
    UserPreferences,
)
from app.graph.state import TravelState, TravelStatePatch
from app.tools.contracts import ToolContext
from app.tools.executor import ToolExecutor
from app.tools.provider_tools import apply_verified_coordinates
from app.graph.tool_runtime import context_from_state


def make_phase1_research_node(
    agent: Phase1ResearchAgent,
    executor: ToolExecutor,
) -> Runnable[TravelState, TravelStatePatch]:
    def arguments(
        state: TravelState,
        weather_summary: str,
        research_context: dict | None,
    ) -> dict:
        return {
            "entities": state.get("entities") or TravelEntities(),
            "preferences": state.get("effective_preferences") or UserPreferences(),
            "weather_summary": weather_summary,
            "research_context": research_context,
        }

    def execute_tools(state: TravelState):
        context = context_from_state(state)
        outcome = executor.execute(ToolName.WEATHER, context)
        summary = (
            str(outcome.result.data.get("summary", "天气信息待核实"))
            if outcome.result.success
            else "天气接口暂不可用，出行前请重新查询"
        )
        return outcome, summary

    def enrich_coordinates(state: TravelState, research):
        if ToolName.POI_COORDINATES not in executor.realtime_tools:
            return research, None
        coordinate_outcome = executor.execute(
            ToolName.POI_COORDINATES,
            ToolContext(
                entities=state.get("entities") or TravelEntities(),
                preferences=state.get("effective_preferences") or UserPreferences(),
                phase1_research=research,
            ),
        )
        return (
            apply_verified_coordinates(research, coordinate_outcome.result),
            coordinate_outcome,
        )

    def patch(research, outcome, coordinate_outcome) -> TravelStatePatch:
        selected_tools = [ToolName.WEATHER.value]
        results = {ToolName.WEATHER.value: outcome.result}
        errors = list(outcome.errors)
        attempts = {ToolName.WEATHER.value: outcome.attempts}
        if coordinate_outcome is not None:
            selected_tools.append(ToolName.POI_COORDINATES.value)
            results[ToolName.POI_COORDINATES.value] = coordinate_outcome.result
            errors.extend(coordinate_outcome.errors)
            attempts[ToolName.POI_COORDINATES.value] = coordinate_outcome.attempts
        return {
            "phase1_research": research,
            "selected_tools": selected_tools,
            "tool_results": results,
            "tool_errors": errors,
            "tool_attempts": attempts,
            "tool_abort_requested": False,
            "planning_errors": [],
        }

    def research(state: TravelState) -> TravelStatePatch:
        outcome, summary = execute_tools(state)
        phase1 = agent.research(**arguments(state, summary, None))
        phase1, coordinate_outcome = enrich_coordinates(state, phase1)
        return patch(phase1, outcome, coordinate_outcome)

    async def aresearch(state: TravelState) -> TravelStatePatch:
        outcome, summary = execute_tools(state)
        phase1 = await agent.aresearch(**arguments(state, summary, None))
        phase1, coordinate_outcome = enrich_coordinates(state, phase1)
        return patch(phase1, outcome, coordinate_outcome)

    return RunnableLambda(research, afunc=aresearch, name="phase1_research")


def make_phase2_research_node(
    agent: Phase2ResearchAgent,
    executor: ToolExecutor,
) -> Runnable[TravelState, TravelStatePatch]:
    def arguments(state: TravelState) -> dict:
        return {
            "entities": state.get("entities") or TravelEntities(),
            "phase1": state["phase1_research"],
            "selection": state["candidate_selection"],
        }

    def enrich_with_route(state: TravelState, research) -> TravelStatePatch:
        if ToolName.ROUTE_MATRIX not in executor.realtime_tools:
            return {"phase2_research": research}
        outcome = executor.execute(
            ToolName.ROUTE_MATRIX,
            ToolContext(
                entities=state.get("entities") or TravelEntities(),
                preferences=state.get("effective_preferences") or UserPreferences(),
                phase1_research=state.get("phase1_research"),
                candidate_selection=state.get("candidate_selection"),
            ),
        )
        if (
            outcome.result.success
            and outcome.result.data_mode is ToolDataMode.REALTIME
            and outcome.result.data.get("route_legs")
        ):
            research = research.model_copy(
                update={
                    "data_mode": "MIXED_REALTIME_AI",
                    "route_legs": [
                        RouteLeg.model_validate(leg)
                        for leg in outcome.result.data["route_legs"]
                    ],
                }
            )
        return {
            "phase2_research": research,
            "selected_tools": [ToolName.ROUTE_MATRIX.value],
            "tool_results": {ToolName.ROUTE_MATRIX.value: outcome.result},
            "tool_errors": outcome.errors,
            "tool_attempts": {ToolName.ROUTE_MATRIX.value: outcome.attempts},
        }

    def research(state: TravelState) -> TravelStatePatch:
        if not state.get("phase1_research") or not state.get("candidate_selection"):
            return {"planning_errors": ["PHASE2_INPUT_MISSING"]}
        return enrich_with_route(state, agent.research(**arguments(state)))

    async def aresearch(state: TravelState) -> TravelStatePatch:
        if not state.get("phase1_research") or not state.get("candidate_selection"):
            return {"planning_errors": ["PHASE2_INPUT_MISSING"]}
        return enrich_with_route(state, await agent.aresearch(**arguments(state)))

    return RunnableLambda(research, afunc=aresearch, name="phase2_research")
