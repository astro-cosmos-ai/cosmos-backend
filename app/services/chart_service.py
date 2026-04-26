"""Orchestrates chart creation: compute → harness → store in Supabase."""
import asyncio
import logging
from datetime import date, time

from app.services.swiss.calculator import compute_chart
from app.services.harness.parashari import compute_all_significators
from app.services.harness.yogas import detect_yogas
from app.services.load_service import load_chart_data
from app.db import queries
from supabase import Client

logger = logging.getLogger("app.chart")


def _birth_input_from_request(req: dict) -> dict:
    dob: date = req["dob"]
    tob: time = req["tob"]
    return {
        "day": dob.day,
        "month": dob.month,
        "year": dob.year,
        "hour": tob.hour,
        "min": tob.minute,
        "lat": req["pob_lat"],
        "lon": req["pob_lon"],
        "tzone": req["timezone"],
    }


async def create_chart(db: Client, user_id: str, birth_req: dict) -> dict:
    existing = queries.find_chart_by_birth(
        db, user_id,
        str(birth_req["dob"]), str(birth_req["tob"]),
        birth_req["pob_lat"], birth_req["pob_lon"],
    )
    if existing:
        logger.info("chart exists  id=%s  user=%s — returning existing", existing.get("id"), user_id)
        return existing

    birth_input = _birth_input_from_request(birth_req)
    loop = asyncio.get_running_loop()
    assembled = await loop.run_in_executor(None, compute_chart, birth_input)

    # Compute Parashari significators from assembled data
    parashari_sig = compute_all_significators(assembled)
    assembled["parashari_significators"] = parashari_sig

    # Detect yogas from harness output
    planets = assembled.get("planets") or {}
    assembled["yogas"] = detect_yogas(parashari_sig, planets)

    chart_data = {
        "name": birth_req["name"],
        "dob": str(birth_req["dob"]),
        "tob": str(birth_req["tob"]),
        "pob_name": birth_req["pob_name"],
        "pob_lat": birth_req["pob_lat"],
        "pob_lon": birth_req["pob_lon"],
        "timezone": birth_req["timezone"],
        **assembled,
    }

    chart_row = queries.insert_chart(db, user_id, chart_data)
    logger.info("chart created  id=%s  user=%s  name=%s", chart_row.get("id"), user_id, birth_req["name"])

    try:
        await load_chart_data(db, chart_row, date.today().year)
    except Exception as e:
        logger.warning("load_chart_data failed after chart creation: %s", e)

    return chart_row
