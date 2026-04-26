"""
Varshaphal (annual solar return) agent.

Runs the full 5-node LOAD→EXTRACT→COMPUTE→SYNTHESIZE→VALIDATE pipeline
for the varshaphal section using base_agent.run_analysis.

Usage:
    content = await run_varshaphal_analysis(chart_row, year, db)
"""
from datetime import date

from app.agents.base_agent import run_analysis
from app.agents.prompts.varshaphal import SYSTEM_PROMPT
from app.services.harness.context_builder import build_varshaphal_context
from app.services.varshaphal_service import get_varshaphal


async def run_varshaphal_analysis(
    chart_row: dict,
    year: int,
    db: object,  # supabase Client — not used directly, kept for call-site symmetry
) -> str:
    """
    Run the varshaphal analysis pipeline via base_agent.run_analysis.

    Raises:
        ValueError: if varshaphal_raw is not loaded for the requested year,
                    or if chart_id is absent from chart_row.

    Returns:
        Validated LLM output string (may be prefixed with [UNVERIFIED] after
        2 failed retries, per the base agent contract).
    """
    # Pre-flight: confirm raw data is present before entering the graph.
    # build_varshaphal_context always uses date.today().year, so we must
    # ensure the year requested matches what the context builder will use.
    # For non-current-year requests the route still returns the cached result
    # before reaching here, so in practice year == date.today().year on this
    # code path.  We still guard explicitly.
    varsha = get_varshaphal(chart_row, year)
    if varsha is None:
        raise ValueError("Varshaphal data not loaded")

    chart_id: str = chart_row.get("id") or chart_row.get("chart_id") or ""

    # db_fn is a lambda that ignores chart_id and returns the already-loaded
    # chart_row directly.  This avoids a redundant DB round-trip because the
    # route already fetched and ownership-checked the row.
    return await run_analysis(
        chart_id=chart_id,
        chart_json=chart_row,
        section="varshaphal",
        system_prompt=SYSTEM_PROMPT,
        context_builder_fn=build_varshaphal_context,
        db_fn=lambda _: chart_row,
    )
