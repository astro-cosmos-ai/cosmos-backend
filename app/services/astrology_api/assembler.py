"""
Calls all Phase 1 AstrologyAPI endpoints concurrently and assembles
the result into a dict matching the `charts` table columns.

When settings.chart_engine == "swiss", delegates to swiss.calculator instead.
"""
import asyncio
from app.core.config import settings
from .client import fetch_many

DIVISIONAL_CHARTS = ["D1", "D9", "D2", "D3", "D4", "D7", "D10", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"]
ASHTAK_PLANETS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]


def _build_calls(bd: dict) -> list[tuple[str, str, dict]]:
    """Returns list of (label, endpoint, payload)."""
    calls = []

    # Basics
    calls += [
        ("birth_details", "birth_details", bd),
        ("astro_details", "astro_details", bd),
        ("planets", "planets", bd),
        ("planets_extended", "planets/extended", bd),
        ("bhav_madhya", "bhav_madhya", bd),
        ("planet_nature", "planet_nature", bd),
    ]

    # Divisional charts
    for chart in DIVISIONAL_CHARTS:
        calls.append((f"chart_{chart}", f"horo_chart/{chart}", bd))

    # KP
    calls += [
        ("kp_planets", "kp_planets", bd),
        ("kp_house_cusps", "kp_house_cusps", bd),
        ("kp_birth_chart", "kp_birth_chart", bd),
        ("kp_house_significator", "kp_house_significator", bd),
        ("kp_planet_significator", "kp_planet_significator", bd),
    ]

    # Dasha
    calls += [
        ("major_vdasha", "major_vdasha", bd),
        ("current_vdasha", "current_vdasha", bd),
    ]

    # Doshas
    calls += [
        ("manglik", "manglik", bd),
        ("kalsarpa_details", "kalsarpa_details", bd),
        ("sadhesati_status", "sadhesati_current_status", bd),
        ("pitra_dosha", "pitra_dosha_report", bd),
    ]

    # Ashtakavarga
    for planet in ASHTAK_PLANETS:
        calls.append((f"ashtak_{planet}", f"planet_ashtak/{planet}", bd))
    calls.append(("sarvashtak", "sarvashtak", bd))

    return calls


def _birth_payload(birth_input: dict) -> dict:
    return {
        "day": birth_input["day"],
        "month": birth_input["month"],
        "year": birth_input["year"],
        "hour": birth_input["hour"],
        "min": birth_input["min"],
        "lat": birth_input["lat"],
        "lon": birth_input["lon"],
        "tzone": birth_input["tzone"],
    }


async def assemble_chart(birth_input: dict) -> dict:  # noqa: C901
    """
    birth_input: {day, month, year, hour, min, lat, lon, tzone}
    Returns a dict mapping to charts table columns.
    When chart_engine="swiss", runs locally via pyswisseph (no network call).
    """
    if settings.chart_engine == "swiss":
        from app.services.swiss.calculator import compute_chart
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, compute_chart, birth_input)

    bd = _birth_payload(birth_input)
    call_specs = _build_calls(bd)
    labels = [c[0] for c in call_specs]
    endpoint_payload = [(c[1], c[2]) for c in call_specs]

    results = await fetch_many(endpoint_payload)
    data = dict(zip(labels, results))

    # Build divisional_charts dict
    divisional_charts = {}
    for chart in DIVISIONAL_CHARTS:
        val = data.get(f"chart_{chart}")
        if val is not None:
            divisional_charts[chart] = val

    # Build ashtakavarga dict
    ashtakavarga = {}
    for planet in ASHTAK_PLANETS:
        val = data.get(f"ashtak_{planet}")
        if val is not None:
            ashtakavarga[planet] = val
    sarva = data.get("sarvashtak")
    if sarva is not None:
        ashtakavarga["sarvashtaka"] = sarva

    # Build doshas dict
    doshas = {
        "manglik": data.get("manglik"),
        "kalsarpa": data.get("kalsarpa_details"),
        "sadhesati": data.get("sadhesati_status"),
        "pitra": data.get("pitra_dosha"),
    }

    # Build panchang from astro_details
    astro = data.get("astro_details") or {}
    panchang = {
        "tithi": astro.get("tithi"),
        "nakshatra": astro.get("nakshatra") or astro.get("Naksahtra"),
        "yoga": astro.get("yoga"),
        "karana": astro.get("karana"),
        "vaara": astro.get("Weekday"),
    }

    return {
        "birth_details": data.get("birth_details"),
        "astro_details": astro,
        "planets": _merge_planet_data(data.get("planets"), data.get("planets_extended"), data.get("astro_details")),
        "divisional_charts": divisional_charts,
        "kp_planets": data.get("kp_planets"),
        "kp_cusps": data.get("kp_house_cusps"),
        "kp_house_significators": data.get("kp_house_significator"),
        "kp_planet_significators": data.get("kp_planet_significator"),
        "dashas": {"vimshottari": data.get("major_vdasha")},
        "current_dasha": data.get("current_vdasha"),
        "ashtakavarga": ashtakavarga,
        "doshas": doshas,
        "panchang": panchang,
    }


def _merge_planet_data(planets: list | None, extended: list | None, astro: dict | None) -> dict | None:
    if not planets:
        return None

    # Build lookup from extended data
    ext_map = {}
    if extended and isinstance(extended, list):
        for p in extended:
            if isinstance(p, dict) and "name" in p:
                ext_map[p["name"].lower()] = p

    # Get ascendant sign number for whole-sign house computation
    asc_sign_num = None
    if astro and "ascendant" in astro:
        asc_sign_num = _sign_name_to_num(astro["ascendant"])

    merged = {}
    for p in planets:
        if not isinstance(p, dict) or "name" not in p:
            continue
        name = p["name"].lower()
        ext = ext_map.get(name, {})
        planet_data = {**p, **ext}

        # Compute whole-sign house — fall back to sign name when current_sign integer is absent
        planet_sign_num = p.get("current_sign") or _sign_name_to_num(p.get("sign") or "")
        if planet_sign_num:
            planet_data["current_sign"] = planet_sign_num
        if asc_sign_num and planet_sign_num:
            planet_data["house_parashari"] = _whole_sign_house(planet_sign_num, asc_sign_num)

        merged[name] = planet_data

    return merged


SIGN_NAMES = ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
              "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]


def _sign_name_to_num(sign_name: str) -> int | None:
    try:
        return SIGN_NAMES.index(sign_name.lower()) + 1
    except ValueError:
        return None


def _whole_sign_house(planet_sign: int, asc_sign: int) -> int:
    return ((planet_sign - asc_sign) % 12) + 1
