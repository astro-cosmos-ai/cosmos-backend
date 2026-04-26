from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.api.deps import get_db, get_current_user, get_chart_or_404
from app.db import queries
from app.models.chart import BirthInput, ChartRow, LoadResponse
from app.services import chart_service
from app.services.load_service import load_chart_data

router = APIRouter(prefix="/api/charts", tags=["charts"])


@router.post("", response_model=ChartRow)
async def create_chart(
    body: BirthInput,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    row = await chart_service.create_chart(db, current_user["id"], body.model_dump())
    return row


@router.get("/{chart_id}", response_model=ChartRow)
async def get_chart(chart: dict = Depends(get_chart_or_404)):
    return chart



@router.post("/{chart_id}/load", response_model=LoadResponse)
async def load_chart(
    chart_id: str,
    year: int = Query(default=None, description="Varshaphal year to load (default: current year)"),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> LoadResponse:
    """
    Fetches all dynamic AstrologyAPI data for a chart in one shot:
    - Varshaphal raw planets for the requested year
    - Today's transit snapshot

    This is the only endpoint that calls AstrologyAPI after chart creation.
    Must be called before GET /varshaphal or any transit-dependent endpoint.
    """
    chart_row = queries.get_chart_full(db, chart_id, current_user["id"])
    if not chart_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    target_year = year or date.today().year

    try:
        result = await load_chart_data(db, chart_row, target_year)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return LoadResponse(**result)
