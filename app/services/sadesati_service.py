"""
Sade Sati tracker: monitors Saturn's transit relative to natal Moon sign.
Sade Sati = Saturn transiting 12th, 1st (Moon sign), or 2nd from natal Moon.
Total duration ~7.5 years; each phase ~2.5 years.
"""

_SIGN_NAMES = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]

# Saturn spends ~2.5 years per sign → ~30 months
_SATURN_MONTHS_PER_SIGN = 30


def _sign_from_name(name: str) -> int | None:
    try:
        return _SIGN_NAMES.index(name.lower()) + 1
    except ValueError:
        return None


def _natal_moon_sign(chart_row: dict) -> int | None:
    planets = chart_row.get("planets") or {}
    moon = planets.get("moon") or {}
    sign = moon.get("current_sign")
    if sign and isinstance(sign, int):
        return sign
    astro = chart_row.get("astro_details") or {}
    sign_name = astro.get("moon_sign") or astro.get("moonsign") or ""
    return _sign_from_name(sign_name)


def _relative_position(from_sign: int, to_sign: int) -> int:
    """House of to_sign counted from from_sign (1-indexed)."""
    return ((to_sign - from_sign) % 12) + 1


def get_sadesati_status(chart_row: dict, transit_snapshot: dict) -> dict:
    """
    Returns current Sade Sati status based on Saturn's transit sign.
    """
    natal_moon = _natal_moon_sign(chart_row)
    if not natal_moon:
        return {"active": False, "phase": None, "error": "Natal Moon sign unavailable"}

    planets = transit_snapshot.get("planets") or {}
    saturn = planets.get("saturn") or {}
    saturn_transit_sign = saturn.get("transit_sign")

    if not saturn_transit_sign:
        return {"active": False, "phase": None, "error": "Saturn transit sign unavailable"}

    rel = _relative_position(natal_moon, saturn_transit_sign)

    phase: str | None = None
    active = False

    if rel == 12:
        active = True
        phase = "rising"  # Saturn in 12th from Moon — beginning of Sade Sati
    elif rel == 1:
        active = True
        phase = "peak"    # Saturn on natal Moon sign — most intense phase
    elif rel == 2:
        active = True
        phase = "setting" # Saturn in 2nd from Moon — winding down

    # Severity factors
    severity_factors = []
    natal_sat = (chart_row.get("planets") or {}).get("saturn") or {}
    sat_sign = natal_sat.get("current_sign")

    from app.services.harness.dignity import get_dignity
    if sat_sign:
        dignity = get_dignity("saturn", sat_sign)
        if dignity == "debilitated":
            severity_factors.append("Natal Saturn debilitated — amplifies Sade Sati effects")
        elif dignity in ("exalted", "own"):
            severity_factors.append("Natal Saturn strong — mitigates Sade Sati")

    doshas = chart_row.get("doshas") or {}
    if doshas.get("sadhesati", {}) and doshas["sadhesati"].get("is_sadhesati_now"):
        severity_factors.append("AstrologyAPI confirms active Sade Sati")

    return {
        "active": active,
        "phase": phase,
        "natal_moon_sign": natal_moon,
        "saturn_transit_sign": saturn_transit_sign,
        "saturn_transit_house_from_moon": rel,
        "severity_factors": severity_factors,
        "note": "Each Sade Sati phase lasts approximately 2.5 years (Saturn's sign transit duration)",
    }
