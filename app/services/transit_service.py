"""
Transit engine: fetch real-time planet positions for any date and compute
whole-sign transit houses against a natal chart.
Reuses the same AstrologyAPI client path (Semaphore(5) respected).
"""
from app.services.harness.dignity import get_dignity

_SIGN_NAMES = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]


def _sign_name_to_num(sign_name: str) -> int | None:
    try:
        return _SIGN_NAMES.index(sign_name.lower()) + 1
    except ValueError:
        return None


def _natal_asc_sign(chart_row: dict) -> int | None:
    astro = chart_row.get("astro_details") or {}
    asc_name = astro.get("ascendant") or ""
    return _sign_name_to_num(asc_name)


def _whole_sign_house(planet_sign: int, asc_sign: int) -> int:
    return ((planet_sign - asc_sign) % 12) + 1


def compute_transit_houses(
    transit_planets: list[dict],
    natal_asc_sign: int,
) -> dict[str, dict]:
    """
    Given the raw AstrologyAPI planets list for a transit date,
    returns a dict keyed by planet name with transit sign and house.
    """
    result: dict[str, dict] = {}
    for p in (transit_planets or []):
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").lower()
        sign = p.get("current_sign")
        sign_name = p.get("sign_name") or p.get("sign") or ""
        nakshatra = p.get("nakshatra") or ""
        retro = bool(p.get("isRetro") or p.get("retro"))
        if not name or not sign:
            continue
        house = _whole_sign_house(sign, natal_asc_sign)
        dignity = get_dignity(name, sign)
        result[name] = {
            "transit_sign": sign,
            "sign_name": sign_name,
            "transit_house": house,
            "nakshatra": nakshatra,
            "retrograde": retro,
            "dignity": dignity,
        }
    return result


def get_transit_snapshot_from_db(chart_row: dict) -> dict | None:
    """
    Returns the pre-loaded transit snapshot from chart_row, or None if not loaded.
    Call POST /api/charts/{id}/load first.
    """
    return chart_row.get("transit_snapshot") or None
