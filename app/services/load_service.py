"""
Chart load service: computes ALL dynamic Swiss Ephemeris data for a chart in one shot.
This is the ONLY place Swiss Ephemeris is called after initial chart creation.
"""
import asyncio
import logging
from datetime import date

from app.services.swiss.calculator import compute_chart

logger = logging.getLogger("app.load")
from app.services.transit_service import compute_transit_houses, _natal_asc_sign
from app.db import queries
from supabase import Client


def _annual_payload(chart_row: dict, year: int) -> dict:
    dob_str = chart_row.get("dob") or ""
    tob_str = chart_row.get("tob") or "00:00:00"
    try:
        dob = date.fromisoformat(str(dob_str)[:10])
        tob_parts = str(tob_str)[:5].split(":")
        hour = int(tob_parts[0])
        minute = int(tob_parts[1]) if len(tob_parts) > 1 else 0
    except Exception:
        raise ValueError("Invalid dob/tob in chart_row")
    return {
        "day": dob.day, "month": dob.month, "year": year,
        "hour": hour, "min": minute,
        "lat": chart_row.get("pob_lat") or 0.0,
        "lon": chart_row.get("pob_lon") or 0.0,
        "tzone": chart_row.get("timezone") or 5.5,
    }


def _transit_payload(chart_row: dict, target_date: date) -> dict:
    return {
        "day": target_date.day, "month": target_date.month, "year": target_date.year,
        "hour": 12, "min": 0,
        "lat": chart_row.get("pob_lat") or 0.0,
        "lon": chart_row.get("pob_lon") or 0.0,
        "tzone": chart_row.get("timezone") or 5.5,
    }


async def load_chart_data(db: Client, chart_row: dict, year: int) -> dict:
    """
    Computes varshaphal raw planets for `year` and today's transit snapshot via Swiss Ephemeris.
    Writes results to charts.varshaphal_raw and charts.transit_snapshot.
    Returns a summary dict.
    """
    today = date.today()
    annual_pl = _annual_payload(chart_row, year)
    transit_pl = _transit_payload(chart_row, today)

    loop = asyncio.get_running_loop()
    annual_chart, transit_chart = await asyncio.gather(
        loop.run_in_executor(None, compute_chart, annual_pl),
        loop.run_in_executor(None, compute_chart, transit_pl),
    )

    # Normalise Swiss planets dict → list so downstream consumers (compute_annual_houses,
    # compute_transit_houses) can iterate it uniformly.
    raw_annual = list((annual_chart.get("planets") or {}).values())
    raw_transit = list((transit_chart.get("planets") or {}).values())

    if not raw_annual:
        raise RuntimeError("Swiss Ephemeris failed to return varshaphal planets")
    if not raw_transit:
        raise RuntimeError("Swiss Ephemeris failed to return transit planets")

    logger.info("chart=%s  loaded varshaphal year=%s transit=%s", chart_row["id"], year, today)

    existing_raw = chart_row.get("varshaphal_raw") or {}
    existing_raw[str(year)] = raw_annual
    await loop.run_in_executor(
        None, queries.update_chart_field, db, chart_row["id"], "varshaphal_raw", existing_raw
    )

    asc_sign = _natal_asc_sign(chart_row)
    if not asc_sign:
        raise RuntimeError("Cannot determine natal ascendant — astro_details missing")
    transit_planets = compute_transit_houses(raw_transit, asc_sign)
    snapshot = {"date": str(today), "natal_asc_sign": asc_sign, "planets": transit_planets}
    await loop.run_in_executor(
        None, queries.update_chart_field, db, chart_row["id"], "transit_snapshot", snapshot
    )

    return {
        "loaded": True,
        "varshaphal_year": year,
        "transit_date": str(today),
    }
