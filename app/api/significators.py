from fastapi import APIRouter, Depends
from app.api.deps import get_chart_or_404
from app.services.significator_service import get_full_significator_map

router = APIRouter(prefix="/api/charts", tags=["significators"])


@router.get("/{chart_id}/significators")
async def full_significator_map(chart: dict = Depends(get_chart_or_404)):
    return get_full_significator_map(chart)
