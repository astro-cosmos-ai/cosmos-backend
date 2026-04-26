"""Compatibility endpoint: Ashtakoot computation + LLM interpretation."""
import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.db import queries
from app.services.compatibility_service import compute_ashtakoot
from app.agents.prompts.compatibility import SYSTEM_PROMPT

COMPAT_MODEL = "claude-sonnet-4-6"

router = APIRouter(prefix="/api/compatibility", tags=["compatibility"])


class CompatibilityRequest(BaseModel):
    chart_id_1: str
    chart_id_2: str


def _build_compat_context(chart_a: dict, chart_b: dict, ashtakoot: dict) -> str:
    name_a = chart_a.get("name") or "Person A"
    name_b = chart_b.get("name") or "Person B"
    scores = ashtakoot["scores"]
    lines = [
        f"COMPATIBILITY: {name_a} ↔ {name_b}",
        f"Moon Nakshatra A: {ashtakoot['moon_nakshatra_a'] or '?'} (sign {ashtakoot['moon_sign_a']})",
        f"Moon Nakshatra B: {ashtakoot['moon_nakshatra_b'] or '?'} (sign {ashtakoot['moon_sign_b']})",
        "",
        "ASHTAKOOT SCORES:",
    ]
    for koota, data in scores.items():
        lines.append(f"  {koota.replace('_', ' ').title()}: {data['score']}/{data['max']}")
    lines += [
        f"  TOTAL: {ashtakoot['total']}/36",
        f"  Active Doshas: {', '.join(ashtakoot['doshas']) or 'none'}",
        "",
        f"PERSON A — Ascendant: {(chart_a.get('astro_details') or {}).get('ascendant', '?')}, "
        f"Current Dasha: {(chart_a.get('current_dasha') or {}).get('major_dasha', '?')}",
        f"PERSON B — Ascendant: {(chart_b.get('astro_details') or {}).get('ascendant', '?')}, "
        f"Current Dasha: {(chart_b.get('current_dasha') or {}).get('major_dasha', '?')}",
    ]
    return "\n".join(lines)


@router.post("/")
async def compute_compatibility(
    request: CompatibilityRequest,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """Compute Ashtakoot and generate LLM compatibility interpretation."""
    chart_a = queries.get_chart_by_id(db, request.chart_id_1, current_user["id"])
    if not chart_a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chart {request.chart_id_1} not found")

    chart_b = queries.get_chart_by_id(db, request.chart_id_2, current_user["id"])
    if not chart_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chart {request.chart_id_2} not found")

    # Canonical ordering to ensure cache hits regardless of input order
    id_1, id_2 = sorted([request.chart_id_1, request.chart_id_2])
    c_a = chart_a if chart_a["id"] == id_1 else chart_b
    c_b = chart_b if chart_b["id"] == id_2 else chart_a

    # Check cache
    cached = queries.get_comparison(db, id_1, id_2)
    if cached:
        return {
            "chart_id_1": id_1,
            "chart_id_2": id_2,
            "ashtakoot": cached.get("ashtakoot_data"),
            "analysis": cached.get("analysis"),
            "cached": True,
        }

    # Compute Ashtakoot
    ashtakoot = compute_ashtakoot(c_a, c_b)
    context = _build_compat_context(c_a, c_b, ashtakoot)

    # LLM interpretation
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=COMPAT_MODEL,
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )
    analysis = next((b.text for b in resp.content if b.type == "text"), "")

    row = queries.insert_comparison(db, id_1, id_2, ashtakoot, analysis)

    return {
        "chart_id_1": id_1,
        "chart_id_2": id_2,
        "ashtakoot": ashtakoot,
        "analysis": analysis,
        "cached": False,
    }


@router.get("/{chart_id_1}/{chart_id_2}")
async def get_compatibility(
    chart_id_1: str,
    chart_id_2: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """Retrieve a cached compatibility report."""
    id_1, id_2 = sorted([chart_id_1, chart_id_2])
    cached = queries.get_comparison(db, id_1, id_2)
    if not cached:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No compatibility report found. Run POST /api/compatibility/ first.")
    return {
        "chart_id_1": id_1,
        "chart_id_2": id_2,
        "ashtakoot": cached.get("ashtakoot_data"),
        "analysis": cached.get("analysis"),
        "cached": True,
    }
