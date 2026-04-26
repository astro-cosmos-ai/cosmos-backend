from fastapi import APIRouter, Depends
from app.api.deps import get_chart_or_404
from app.services.timeline_service import build_timeline

router = APIRouter(prefix="/api/charts", tags=["timeline"])


@router.get("/{chart_id}/timeline")
async def get_timeline(chart: dict = Depends(get_chart_or_404)):
    return build_timeline(chart)
