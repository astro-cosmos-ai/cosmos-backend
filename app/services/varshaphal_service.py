"""
Varshaphal (Annual Chart / Solar Return) service.
Reads pre-loaded raw planet data from chart_row['varshaphal_raw'].
Call POST /api/charts/{id}/load before calling get_varshaphal().
"""
from datetime import date

from app.services.harness.dignity import get_dignity
from app.services.harness.parashari import compute_all_significators

_SIGN_NAMES = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]


def _whole_sign_house(planet_sign: int, asc_sign: int) -> int:
    return ((planet_sign - asc_sign) % 12) + 1


def _sign_name_to_num(name: str) -> int | None:
    try:
        return _SIGN_NAMES.index(name.lower()) + 1
    except ValueError:
        return None


def compute_annual_houses(transit_planets: list[dict], natal_asc_sign: int) -> dict[str, dict]:
    """Compute transit houses for the annual chart planets relative to natal ascendant."""
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
            "sign": sign,
            "sign_name": sign_name,
            "house": house,
            "nakshatra": nakshatra,
            "retrograde": retro,
            "dignity": dignity,
        }
    return result


def _year_lord(annual_planets: dict) -> str:
    """
    Varshapati (year lord): the planet ruling the sign occupied by the Sun in the annual chart.
    Uses a simplified sign → natural lord mapping.
    """
    _SIGN_LORD = {
        1: "mars", 2: "venus", 3: "mercury", 4: "moon", 5: "sun",
        6: "mercury", 7: "venus", 8: "mars", 9: "jupiter", 10: "saturn",
        11: "saturn", 12: "jupiter",
    }
    sun = annual_planets.get("sun") or {}
    sun_sign = sun.get("sign")
    if sun_sign:
        return _SIGN_LORD.get(sun_sign, "sun")
    return "sun"


def get_varshaphal(chart_row: dict, year: int) -> dict | None:
    """
    Builds the varshaphal dict for a given year from pre-loaded raw planet data.
    Returns None if varshaphal_raw has not been loaded for this year.
    Call POST /api/charts/{id}/load first.
    """
    from app.db.queries import get_varshaphal_raw
    raw = get_varshaphal_raw(chart_row, year)
    if not raw:
        return None

    astro = chart_row.get("astro_details") or {}
    asc_name = astro.get("ascendant") or ""
    natal_asc_sign = _sign_name_to_num(asc_name)
    if not natal_asc_sign:
        return None

    annual_planets = compute_annual_houses(raw, natal_asc_sign)

    annual_chart_stub = {
        "planets": {
            name: {
                "house_parashari": data["house"],
                "current_sign": data["sign"],
                "sign_name": data["sign_name"],
                "isRetro": data["retrograde"],
            }
            for name, data in annual_planets.items()
        }
    }
    annual_sig = compute_all_significators(annual_chart_stub)

    try:
        dob = date.fromisoformat(str(chart_row.get("dob", ""))[:10])
        age = year - dob.year
    except Exception:
        age = None

    return {
        "year": year,
        "age": age,
        "natal_ascendant": asc_name,
        "planets": annual_planets,
        "year_lord": _year_lord(annual_planets),
        "significators": annual_sig,
    }
