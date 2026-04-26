"""
Event predictor agent.
Flow: CLASSIFY → SCAN → CONFIRM → SYNTHESIZE → VALIDATE
classify_node uses lightweight Haiku if keyword matching fails.
confirm_node fetches real transit data for each candidate window midpoint.
"""
from datetime import date, timedelta
from typing import TypedDict, Optional
import anthropic
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.agents.prompts.event_predictor import SYSTEM_PROMPT
from app.agents.validators.position_validator import validate_output
from app.services.dasha_scanner import classify_question_to_houses, scan_dasha_windows, rank_windows
from app.services.transit_service import get_transit_snapshot_from_db
from app.services.double_transit import compute_double_transit
from app.services.ashtakavarga_service import assess_transit_quality
from app.services.sadesati_service import get_sadesati_status

CLASSIFY_MODEL = "claude-haiku-4-5"
SYNTHESIS_MODEL = "claude-sonnet-4-6"


class PredictState(TypedDict):
    chart_id: str
    chart_row: dict
    question: str
    start_date: date
    end_date: date
    target_houses: list[int]
    raw_windows: list[dict]
    confirmed_windows: list[dict]
    sadesati: dict
    context_string: str
    llm_output: str
    validation_result: dict
    final_output: str
    retry_count: int
    error: Optional[str]


def _classify_node(state: PredictState) -> PredictState:
    target = classify_question_to_houses(state["question"])
    if target:
        return {**state, "target_houses": target}

    # Fallback: ask Haiku to identify the topic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=CLASSIFY_MODEL,
        max_tokens=100,
        system=(
            "You are a Vedic astrology assistant. Given a question about a life event, "
            "reply with ONLY a JSON array of 2–4 house numbers (integers 1–12) that "
            "Jyotish associates with this topic. No explanation. Example: [2,7,11]"
        ),
        messages=[{"role": "user", "content": state["question"]}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "").strip()
    try:
        import json
        houses = json.loads(text)
        if isinstance(houses, list) and all(isinstance(h, int) for h in houses):
            return {**state, "target_houses": houses}
    except Exception:
        pass
    # Last resort: generic life quality houses
    return {**state, "target_houses": [1, 5, 9, 11]}


def _scan_node(state: PredictState) -> PredictState:
    if not state["target_houses"]:
        return {**state, "raw_windows": []}
    windows = scan_dasha_windows(
        state["chart_row"],
        state["target_houses"],
        state["start_date"],
        state["end_date"],
    )
    return {**state, "raw_windows": windows}


async def _confirm_node(state: PredictState) -> PredictState:
    windows = state["raw_windows"]
    if not windows:
        return {**state, "confirmed_windows": [], "sadesati": {}}

    transit_snapshot = get_transit_snapshot_from_db(state["chart_row"])
    if not transit_snapshot:
        # Transit data not loaded — skip transit confirmation, return windows unconfirmed
        return {**state, "confirmed_windows": state["raw_windows"], "sadesati": {}}

    double_transit = compute_double_transit(transit_snapshot, state["chart_row"])
    av_assessments = assess_transit_quality(state["chart_row"], transit_snapshot)
    sadesati = get_sadesati_status(state["chart_row"], transit_snapshot)

    confirmed = rank_windows(windows, double_transit, av_assessments, state["target_houses"])
    return {**state, "confirmed_windows": confirmed, "sadesati": sadesati}


def _build_context(state: PredictState) -> str:
    chart = state["chart_row"]
    astro = chart.get("astro_details") or {}
    current_dasha = chart.get("current_dasha") or {}

    lines = [
        f"QUESTION: {state['question']}",
        f"TARGET HOUSES: {state['target_houses']}",
        f"PREDICTION WINDOW: {state['start_date']} to {state['end_date']}",
        "",
        "NATAL CHART:",
        f"  Ascendant: {astro.get('ascendant', '?')}",
        f"  Current Dasha: {current_dasha.get('major_dasha', '?')} MD / {current_dasha.get('antar_dasha', '?')} AD",
        "",
    ]

    planets = chart.get("planets") or {}
    for pname, pdata in planets.items():
        sign = pdata.get("sign_name") or "?"
        house = pdata.get("house_parashari", "?")
        retro = " (R)" if pdata.get("isRetro") else ""
        lines.append(f"  {pname.title()}{retro}: {sign}, House {house}")

    ss = state.get("sadesati") or {}
    lines += [
        "",
        f"SADE SATI: {'Active — ' + ss.get('phase', '') if ss.get('active') else 'Not active'}",
    ]

    windows = (state.get("confirmed_windows") or [])[:5]
    if windows:
        lines += ["", "CANDIDATE DASHA WINDOWS (pre-screened):"]
        for w in windows:
            tc = "Transit-confirmed" if w.get("transit_confirmed") else "Transit not confirmed"
            av = f", AV score {w['ashtakavarga_score']}" if w.get("ashtakavarga_score") is not None else ""
            lines.append(
                f"  {w['md_lord']}/{w['ad_lord']}: {w['start']} – {w['end']} "
                f"| score={w['match_score']} | houses={w['houses_activated']} | {tc}{av}"
            )
    else:
        lines.append("\nNo matching dasha windows found in the requested period.")

    return "\n".join(lines)


def _synthesize_node(state: PredictState) -> PredictState:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system = SYSTEM_PROMPT
    if state["retry_count"] > 0:
        violations = state.get("validation_result", {}).get("violations", [])
        system += (
            "\n\nIMPORTANT — YOUR PREVIOUS RESPONSE HAD ERRORS:\n"
            + "\n".join(f"- {v}" for v in violations)
            + "\n\nFix these specifically."
        )

    context = _build_context(state)
    resp = client.messages.create(
        model=SYNTHESIS_MODEL,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": context}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return {**state, "context_string": context, "llm_output": text}


def _validate_node(state: PredictState) -> PredictState:
    result = validate_output(state["llm_output"], state["chart_row"])
    if result["passed"] or state["retry_count"] >= 2:
        output = state["llm_output"]
        if not result["passed"]:
            output = "[UNVERIFIED — some positional references could not be confirmed]\n\n" + output
        return {**state, "validation_result": result, "final_output": output}
    return {**state, "validation_result": result, "retry_count": state["retry_count"] + 1}


def _should_retry(state: PredictState) -> str:
    if (
        not state["validation_result"].get("passed", True)
        and state["retry_count"] > 0
        and not state.get("final_output")
    ):
        return "synthesize"
    return "end"


def _build_graph() -> any:
    graph = StateGraph(PredictState)
    graph.add_node("classify", _classify_node)
    graph.add_node("scan", _scan_node)
    graph.add_node("confirm", _confirm_node)
    graph.add_node("synthesize", _synthesize_node)
    graph.add_node("validate", _validate_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "scan")
    graph.add_edge("scan", "confirm")
    graph.add_edge("confirm", "synthesize")
    graph.add_edge("synthesize", "validate")
    graph.add_conditional_edges(
        "validate",
        _should_retry,
        {"synthesize": "synthesize", "end": END},
    )
    return graph.compile()


_GRAPH = None


def _get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


async def run_prediction(
    chart_id: str,
    chart_row: dict,
    question: str,
    start_date: date,
    end_date: date,
) -> dict:
    """
    Returns dict with: final_output, confirmed_windows, target_houses, sadesati.
    """
    initial: PredictState = {
        "chart_id": chart_id,
        "chart_row": chart_row,
        "question": question,
        "start_date": start_date,
        "end_date": end_date,
        "target_houses": [],
        "raw_windows": [],
        "confirmed_windows": [],
        "sadesati": {},
        "context_string": "",
        "llm_output": "",
        "validation_result": {},
        "final_output": "",
        "retry_count": 0,
        "error": None,
    }

    final = await _get_graph().ainvoke(initial)
    return {
        "final_output": final["final_output"],
        "confirmed_windows": final["confirmed_windows"],
        "target_houses": final["target_houses"],
        "sadesati": final["sadesati"],
    }
