import hashlib
import json
from typing import Any
from supabase import Client


def _chart_hash(chart_row: dict) -> str:
    serialized = json.dumps(chart_row, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def insert_chart(db: Client, user_id: str, chart_data: dict) -> dict:
    result = db.table("charts").insert({"user_id": user_id, **chart_data}).execute()
    return result.data[0]


_CHART_COLUMNS = (
    "id, user_id, name, dob, tob, pob_name, pob_lat, pob_lon, timezone, "
    "birth_details, astro_details, planets, divisional_charts, "
    "kp_planets, kp_cusps, kp_house_significators, kp_planet_significators, "
    "parashari_significators, dashas, current_dasha, ashtakavarga, "
    "doshas, panchang, created_at"
)


def get_chart_by_id(db: Client, chart_id: str, user_id: str) -> dict | None:
    result = (
        db.table("charts")
        .select(_CHART_COLUMNS)
        .eq("id", chart_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return result.data


def get_chart_full(db: Client, chart_id: str, user_id: str) -> dict | None:
    """Fetch all columns including varshaphal_raw and transit_snapshot.
    Use only from routes that need the blob columns (/load, /varshaphal).
    """
    result = (
        db.table("charts")
        .select("*")
        .eq("id", chart_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return result.data


def find_chart_by_user(db: Client, user_id: str) -> dict | None:
    """Return the user's single chart, or None if not yet created."""
    result = (
        db.table("charts")
        .select(_CHART_COLUMNS)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_charts_by_user(db: Client, user_id: str) -> list[dict]:
    result = (
        db.table("charts")
        .select("id, name, dob, tob, pob_name, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def update_chart_field(db: Client, chart_id: str, field: str, value: Any) -> None:
    db.table("charts").update({field: value}).eq("id", chart_id).execute()


def get_varshaphal_raw(chart_row: dict, year: int) -> list[dict] | None:
    raw = chart_row.get("varshaphal_raw") or {}
    return raw.get(str(year))



def get_cached_analysis(db: Client, chart_id: str, section: str, chart_row: dict) -> dict | None:
    h = _chart_hash(chart_row)
    result = (
        db.table("analyses")
        .select("*")
        .eq("chart_id", chart_id)
        .eq("section", section)
        .eq("input_hash", h)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def insert_analysis(
    db: Client, chart_id: str, section: str, content: str, model: str, chart_row: dict
) -> dict:
    h = _chart_hash(chart_row)
    result = (
        db.table("analyses")
        .upsert(
            {
                "chart_id": chart_id,
                "section": section,
                "content": content,
                "input_hash": h,
                "model": model,
            },
            on_conflict="chart_id,section,input_hash",
        )
        .execute()
    )
    return result.data[0]


def get_all_analyses(db: Client, chart_id: str) -> list[dict]:
    result = (
        db.table("analyses")
        .select("id, chart_id, section, content, model, created_at")
        .eq("chart_id", chart_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def insert_chat_message(db: Client, chart_id: str, role: str, content: str) -> dict:
    result = (
        db.table("chat_messages")
        .insert({"chart_id": chart_id, "role": role, "content": content})
        .execute()
    )
    return result.data[0]


def get_chat_history(db: Client, chart_id: str, limit: int = 50) -> list[dict]:
    result = (
        db.table("chat_messages")
        .select("role, content, created_at")
        .eq("chart_id", chart_id)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return result.data or []


def get_comparison(db: Client, chart_id_1: str, chart_id_2: str) -> dict | None:
    result = (
        db.table("comparisons")
        .select("*")
        .eq("chart_id_1", chart_id_1)
        .eq("chart_id_2", chart_id_2)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def insert_comparison(
    db: Client,
    chart_id_1: str,
    chart_id_2: str,
    ashtakoot_data: dict,
    analysis: str,
) -> dict:
    result = (
        db.table("comparisons")
        .upsert(
            {
                "chart_id_1": chart_id_1,
                "chart_id_2": chart_id_2,
                "ashtakoot_data": ashtakoot_data,
                "analysis": analysis,
            },
            on_conflict="chart_id_1,chart_id_2",
        )
        .execute()
    )
    return result.data[0]
