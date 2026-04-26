"""PDF report generation endpoint."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from supabase import Client

from app.api.deps import get_current_user, get_db
from app.db import queries
from app.services.report_service import generate_report

router = APIRouter(prefix="/api/charts", tags=["report"])


@router.get("/{chart_id}/report.pdf")
async def download_report(
    chart_id: str,
    sections: Optional[str] = Query(
        default=None,
        description="Comma-separated list of analysis sections to include (default: all)",
    ),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """
    Download a full PDF report for a chart.
    Includes chart overview, planet positions, yogas, dasha timeline, and cached AI analyses.
    Pass ?sections=personality,career to limit which analysis sections appear.
    """
    chart_row = queries.get_chart_by_id(db, chart_id, current_user["id"])
    if not chart_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    analyses = queries.get_all_analyses(db, chart_id)

    include_sections = [s.strip() for s in sections.split(",")] if sections else None

    try:
        pdf_bytes = generate_report(chart_row, analyses, include_sections)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Report generation failed: {e}")

    name = (chart_row.get("name") or "chart").replace(" ", "_").lower()
    filename = f"cosmos_report_{name}_{chart_id[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
