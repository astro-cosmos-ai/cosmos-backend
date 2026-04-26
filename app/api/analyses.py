from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.api.deps import get_db, get_chart_or_404
from app.agents.registry import get_agent_config, AGENT_REGISTRY
from app.agents.base_agent import run_analysis, SYNTHESIS_MODEL
from app.db import queries
from app.models.analysis import VALID_SECTIONS, AnalysisResult

router = APIRouter(prefix="/api/charts", tags=["analyses"])


@router.post("/{chart_id}/analyze/{section}", response_model=AnalysisResult)
async def analyze_section(
    section: str,
    chart: dict = Depends(get_chart_or_404),
    db: Client = Depends(get_db),
):
    if section not in VALID_SECTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown section '{section}'. Valid: {VALID_SECTIONS}",
        )

    agent_config = get_agent_config(section)
    if agent_config is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Section '{section}' is not yet implemented. Available: {list(AGENT_REGISTRY.keys())}",
        )

    # Check cache
    cached = queries.get_cached_analysis(db, chart["id"], section, chart)
    if cached:
        return AnalysisResult(
            id=cached["id"],
            chart_id=cached["chart_id"],
            section=cached["section"],
            content=cached["content"],
            model=cached["model"],
            cached=True,
            created_at=cached.get("created_at"),
        )

    # Run the harness → LLM pipeline
    def db_fn(chart_id: str) -> dict | None:
        return chart  # already loaded

    content = await run_analysis(
        chart_id=chart["id"],
        chart_json=chart,
        section=section,
        system_prompt=agent_config["system_prompt"],
        context_builder_fn=agent_config["context_builder"],
        db_fn=db_fn,
    )

    row = queries.insert_analysis(db, chart["id"], section, content, SYNTHESIS_MODEL, chart)

    return AnalysisResult(
        id=row["id"],
        chart_id=row["chart_id"],
        section=row["section"],
        content=row["content"],
        model=row["model"],
        cached=False,
        created_at=row.get("created_at"),
    )


@router.get("/{chart_id}/analyses", response_model=list[AnalysisResult])
async def get_all_analyses(chart: dict = Depends(get_chart_or_404), db: Client = Depends(get_db)):
    rows = queries.get_all_analyses(db, chart["id"])
    return rows
