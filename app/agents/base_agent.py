"""
Base LangGraph agent for Vedic analysis sections.

Flow: LOAD → EXTRACT → COMPUTE → SYNTHESIZE → VALIDATE
                                      ↑              |
                                      └──── retry ───┘ (max 2)
"""
from typing import TypedDict, Any, Callable
import anthropic
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.agents.validators.position_validator import validate_output

SYNTHESIS_MODEL = "claude-sonnet-4-6"


class AgentState(TypedDict):
    chart_id: str
    chart_json: dict
    section: str
    extracted_data: dict
    derived_data: dict
    context_string: str
    system_prompt: str
    llm_output: str
    validation_result: dict
    final_output: str
    retry_count: int


def _make_load_node(db_fn: Callable[[str], dict | None]):
    def load_node(state: AgentState) -> AgentState:
        chart = db_fn(state["chart_id"])
        if chart is None:
            raise ValueError(f"Chart {state['chart_id']} not found")
        return {**state, "chart_json": chart}
    return load_node


def _make_extract_node(context_builder_fn: Callable[[dict], str]):
    def extract_node(state: AgentState) -> AgentState:
        ctx = context_builder_fn(state["chart_json"])
        return {**state, "context_string": ctx, "extracted_data": {}}
    return extract_node


def _make_compute_node():
    def compute_node(state: AgentState) -> AgentState:
        # Derived data (yogas, atmakaraka etc.) is already embedded in chart_json
        # by the harness at chart creation time. Nothing extra to compute here.
        return {**state, "derived_data": {}}
    return compute_node


def _make_synthesize_node():
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def synthesize_node(state: AgentState) -> AgentState:
        system = state["system_prompt"]
        if state["retry_count"] > 0:
            violations = state.get("validation_result", {}).get("violations", [])
            system += (
                f"\n\nIMPORTANT — YOUR PREVIOUS RESPONSE HAD ERRORS:\n"
                + "\n".join(f"- {v}" for v in violations)
                + "\n\nFix these specifically. Only reference planetary positions that appear in the chart data."
            )

        resp = client.messages.create(
            model=SYNTHESIS_MODEL,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": state["context_string"]}],
            cache_control={"type": "ephemeral"},  # cache the system prompt
        )
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return {**state, "llm_output": text}

    return synthesize_node


def _make_validate_node():
    def validate_node(state: AgentState) -> AgentState:
        result = validate_output(state["llm_output"], state["chart_json"])
        if result["passed"] or state["retry_count"] >= 2:
            output = state["llm_output"]
            if not result["passed"]:
                # Mark as unverified after exhausting retries
                output = "[UNVERIFIED — some positional references could not be confirmed]\n\n" + output
            return {
                **state,
                "validation_result": result,
                "final_output": output,
            }
        return {
            **state,
            "validation_result": result,
            "retry_count": state["retry_count"] + 1,
        }
    return validate_node


def _should_retry(state: AgentState) -> str:
    if not state["validation_result"].get("passed", True) and state["retry_count"] > 0 and state["final_output"] == "":
        return "synthesize"
    return "end"


def build_analysis_graph(
    context_builder_fn: Callable[[dict], str],
    system_prompt: str,
    db_fn: Callable[[str], dict | None],
) -> Any:
    """
    Returns a compiled LangGraph graph.
    context_builder_fn: takes chart_json → returns context string for LLM
    db_fn: takes chart_id → returns chart_row dict (or None)
    """
    graph = StateGraph(AgentState)

    graph.add_node("load", _make_load_node(db_fn))
    graph.add_node("extract", _make_extract_node(context_builder_fn))
    graph.add_node("compute", _make_compute_node())
    graph.add_node("synthesize", _make_synthesize_node())
    graph.add_node("validate", _make_validate_node())

    graph.set_entry_point("load")
    graph.add_edge("load", "extract")
    graph.add_edge("extract", "compute")
    graph.add_edge("compute", "synthesize")
    graph.add_edge("synthesize", "validate")

    graph.add_conditional_edges(
        "validate",
        _should_retry,
        {"synthesize": "synthesize", "end": END},
    )

    return graph.compile()


async def run_analysis(
    chart_id: str,
    chart_json: dict,
    section: str,
    system_prompt: str,
    context_builder_fn: Callable[[dict], str],
    db_fn: Callable[[str], dict | None],
) -> str:
    """
    Runs the full LOAD→EXTRACT→COMPUTE→SYNTHESIZE→VALIDATE pipeline.
    Returns the final validated output string.
    """
    compiled = build_analysis_graph(context_builder_fn, system_prompt, db_fn)

    initial_state: AgentState = {
        "chart_id": chart_id,
        "chart_json": chart_json,
        "section": section,
        "extracted_data": {},
        "derived_data": {},
        "context_string": "",
        "system_prompt": system_prompt,
        "llm_output": "",
        "validation_result": {},
        "final_output": "",
        "retry_count": 0,
    }

    final_state = await compiled.ainvoke(initial_state)
    return final_state["final_output"]
