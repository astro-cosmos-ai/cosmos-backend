"""Reads stored chart JSON and returns significator maps."""


def get_full_significator_map(chart_row: dict) -> dict:
    return {
        "parashari": chart_row.get("parashari_significators") or {},
        "kp_by_house": chart_row.get("kp_house_significators") or {},
        "kp_by_planet": chart_row.get("kp_planet_significators") or {},
    }
