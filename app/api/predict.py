"""Event prediction, transit snapshot, double transit, Sade Sati, and Muhurta endpoints."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from supabase import Client

from app.api.deps import get_current_user, get_db
from app.db import queries
from app.models.predict import (
    PredictRequest,
    PredictResponse,
    PredictWindow,
    TransitSnapshotResponse,
    DoubleTansitResponse,
    SadeSatiResponse,
)
from app.agents.event_predictor_agent import run_prediction
from app.services.transit_service import get_transit_snapshot_from_db
from app.services.double_transit import compute_double_transit
from app.services.sadesati_service import get_sadesati_status
from app.services.muhurta_service import find_muhurta_dates


class MuhurtaRequest(BaseModel):
    target_houses: list[int]
    search_start: date
    search_end: date
    top_n: int = 5

router = APIRouter(prefix="/api/charts", tags=["predict"])


@router.post("/{chart_id}/predict", response_model=PredictResponse)
async def predict_event(
    chart_id: str,
    request: PredictRequest,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """
    Predict timing for a life event using Vimshottari dasha + transit confirmation.
    """
    chart_row = queries.get_chart_by_id(db, chart_id, current_user["id"])
    if not chart_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    end_date = request.end_date or (request.start_date + timedelta(days=365 * 15))

    result = await run_prediction(
        chart_id=chart_id,
        chart_row=chart_row,
        question=request.question,
        start_date=request.start_date,
        end_date=end_date,
    )

    ss = result["sadesati"]
    windows = [PredictWindow(**w) for w in result["confirmed_windows"]]

    return PredictResponse(
        chart_id=chart_id,
        question=request.question,
        target_houses=result["target_houses"],
        windows=windows,
        analysis=result["final_output"],
        sadesati_active=bool(ss.get("active")),
        sadesati_phase=ss.get("phase"),
    )


@router.get("/{chart_id}/transits")
async def get_transits(
    chart_id: str,
    target_date: date = Query(default=None, description="Date for transit snapshot (default: today)"),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """
    Fetch and return a transit snapshot (planet positions, transit houses, dignity) for a given date.
    """
    chart_row = queries.get_chart_by_id(db, chart_id, current_user["id"])
    if not chart_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    td = target_date or date.today()
    snapshot = get_transit_snapshot_from_db(chart_row)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transit data not loaded. Run POST /api/charts/{chart_id}/load first.",
        )
    if snapshot.get("date") != str(td):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transit data was loaded for {snapshot.get('date')}, not {td}. Re-run POST /api/charts/{chart_id}/load.",
        )

    return snapshot


@router.get("/{chart_id}/double-transit")
async def get_double_transit(
    chart_id: str,
    target_date: date = Query(default=None, description="Date to check double transit (default: today)"),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """
    Returns which houses are under Jupiter+Saturn double transit influence.
    """
    chart_row = queries.get_chart_by_id(db, chart_id, current_user["id"])
    if not chart_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    td = target_date or date.today()
    snapshot = get_transit_snapshot_from_db(chart_row)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transit data not loaded. Run POST /api/charts/{chart_id}/load first.",
        )
    if snapshot.get("date") != str(td):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transit data was loaded for {snapshot.get('date')}, not {td}. Re-run POST /api/charts/{chart_id}/load.",
        )

    double_transit = compute_double_transit(snapshot, chart_row)

    return {
        "date": str(td),
        "houses": {str(h): v for h, v in double_transit.items()},
    }


@router.get("/{chart_id}/sadesati", response_model=SadeSatiResponse)
async def get_sadesati(
    chart_id: str,
    target_date: date = Query(default=None, description="Date to check Sade Sati status (default: today)"),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """
    Returns Saturn's current relationship to natal Moon — active Sade Sati phase, severity factors.
    """
    chart_row = queries.get_chart_by_id(db, chart_id, current_user["id"])
    if not chart_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    td = target_date or date.today()
    snapshot = get_transit_snapshot_from_db(chart_row)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transit data not loaded. Run POST /api/charts/{chart_id}/load first.",
        )
    if snapshot.get("date") != str(td):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transit data was loaded for {snapshot.get('date')}, not {td}. Re-run POST /api/charts/{chart_id}/load.",
        )

    result = get_sadesati_status(chart_row, snapshot)
    return SadeSatiResponse(**result)


@router.post("/{chart_id}/muhurta")
async def find_muhurta(
    chart_id: str,
    request: MuhurtaRequest,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
):
    """
    Find auspicious dates (muhurta) within a search window for a given life-event purpose
    (determined by target house numbers).
    Returns top N dates ranked by nakshatra + tithi + vara + dasha suitability.
    """
    chart_row = queries.get_chart_by_id(db, chart_id, current_user["id"])
    if not chart_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    if request.search_end < request.search_start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="search_end must be after search_start")

    max_range = timedelta(days=365 * 2)
    if (request.search_end - request.search_start) > max_range:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Search range cannot exceed 2 years")

    dates = find_muhurta_dates(
        chart_row=chart_row,
        target_houses=request.target_houses,
        search_start=request.search_start,
        search_end=request.search_end,
        top_n=min(request.top_n, 20),
    )

    return {
        "chart_id": chart_id,
        "target_houses": request.target_houses,
        "search_start": str(request.search_start),
        "search_end": str(request.search_end),
        "auspicious_dates": dates,
        "note": "Nakshatra and tithi values are approximate. For precise muhurta, consult a Jyotish expert with exact ephemeris data.",
    }
