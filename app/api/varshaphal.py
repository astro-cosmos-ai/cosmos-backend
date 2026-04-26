"""Varshaphal (annual solar return) analysis endpoint."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.api.deps import get_current_user, get_db
from app.db import queries
from app.agents.varshaphal_agent import run_varshaphal_analysis
from app.services.varshaphal_service import get_varshaphal

router = APIRouter(prefix="/api/charts", tags=["varshaphal"])


@router.get("/{chart_id}/varshaphal")
async def get_varshaphal_analysis(
    chart_id: str,
    year: int = Query(default=None, description="Year for solar return (default: current year)"),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """
    Compute and interpret the Varshaphal (annual solar return chart) for a given year.
    Results are cached in the chart's varshaphal JSONB column.
    """
    chart_row = queries.get_chart_full(db, chart_id, current_user["id"])
    if not chart_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    target_year = year or date.today().year

    # Check cache
    cached_varshaphal = chart_row.get("varshaphal") or {}
    year_key = str(target_year)
    if year_key in cached_varshaphal:
        return cached_varshaphal[year_key]

    # Confirm raw data is present before entering the agent pipeline
    varsha = get_varshaphal(chart_row, target_year)
    if not varsha:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Varshaphal data for {target_year} not loaded. Run POST /api/charts/{chart_id}/load?year={target_year} first.",
        )

    # Run synthesis through the 5-node LangGraph pipeline
    try:
        content = await run_varshaphal_analysis(chart_row, target_year, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    result = {
        "chart_id": chart_id,
        "year": target_year,
        "age": varsha.get("age"),
        "natal_ascendant": varsha["natal_ascendant"],
        "year_lord": varsha["year_lord"],
        "annual_planets": varsha["planets"],
        "content": content,
        "cached": False,
    }

    # Cache result
    updated_varshaphal = {**cached_varshaphal, year_key: result}
    queries.update_chart_field(db, chart_id, "varshaphal", updated_varshaphal)

    return result
