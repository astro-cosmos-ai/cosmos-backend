"""
Main entrypoint: compute_chart(birth_input) → chart_json matching the assembler contract.

birth_input: {day, month, year, hour, min, lat, lon, tzone}
Returns same structure as astrology_api/assembler.assemble_chart().
"""
from datetime import datetime, timedelta

from app.core.config import settings
from . import configure
from .ephemeris import (
    birth_to_jd_ut, compute_ascendant, compute_planets,
    compute_placidus_cusps, get_ayanamsa,
    sign_from_lon, nakshatra_from_lon, SIGN_LORDS, NAKSHATRA_INFO,
)
from .vimshottari import compute_vimshottari
from .ashtakavarga import compute_ashtakavarga
from .kp import build_kp_planets, build_kp_cusps
from .doshas import compute_doshas
from .calendar import compute_panchang
from .divisional import build_d1, build_d9, build_moon_chart


def compute_chart(birth_input: dict) -> dict:
    """
    Compute full Vedic natal chart using Swiss Ephemeris (Moshier, Lahiri ayanamsa, mean node).
    Produces chart_json matching the assembler.assemble_chart() contract.
    """
    configure(settings.ayanamsa)

    year = birth_input["year"]
    month = birth_input["month"]
    day = birth_input["day"]
    hour = birth_input["hour"]
    minute = birth_input["min"]
    lat = birth_input["lat"]
    lon = birth_input["lon"]
    tzone = birth_input["tzone"]

    jd_ut = birth_to_jd_ut(year, month, day, hour, minute, tzone)

    # Ascendant
    asc_lon, asc_sign_name, asc_sign_num, asc_deg_in_sign = compute_ascendant(jd_ut, lat, lon)

    # Planets (9 Jyotish planets + Ketu)
    planets = compute_planets(jd_ut, asc_sign_num, node_mode=settings.node_mode)

    # Ayanamsa
    ayanamsa_val = get_ayanamsa(jd_ut)

    # Moon details for astro_details
    moon = planets["moon"]
    moon_nak = moon["nakshatra"]
    moon_nak_pada = moon["nakshatra_pad"]
    moon_nak_info = NAKSHATRA_INFO.get(moon_nak, {})
    sun = planets["sun"]

    # Panchang
    panchang = compute_panchang(
        sun_lon=sun["fullDegree"],
        moon_lon=moon["fullDegree"],
        year=year, month=month, day=day,
        moon_nakshatra=moon_nak,
    )

    # astro_details — matches AstrologyAPI shape (mixed-case keys preserved for harness compat)
    astro_details = {
        "ascendant": asc_sign_name,
        "ascendant_lord": SIGN_LORDS[asc_sign_name],
        "sign": sun["sign"],                          # sun sign
        "SignLord": SIGN_LORDS[sun["sign"]],
        "moon_sign": moon["sign"],
        "moonsign": moon["sign"],
        "Naksahtra": moon_nak,                        # legacy key harness reads
        "nakshatra": moon_nak,
        "NaksahtraLord": moon["nakshatraLord"],
        "Charan": moon_nak_pada,
        "Yoni": moon_nak_info.get("yoni", ""),
        "Gan": moon_nak_info.get("gana", ""),
        "Nadi": moon_nak_info.get("nadi", ""),
        "name_alphabet": (moon_nak_info.get("syllables") or [""])[moon_nak_pada - 1],
        "Tithi": str(panchang["tithi"]),
        "Yog": str(panchang["yoga"]),
        "Karan": str(panchang["karana"]),
        "Weekday": panchang["vaara"],
        "ayanamsha": ayanamsa_val,
    }

    # Birth details
    birth_details = {
        "day": day, "month": month, "year": year,
        "hour": hour, "min": minute,
        "lat": lat, "lon": lon, "tzone": tzone,
        "ayanamsha": ayanamsa_val,
    }

    # Vimshottari dasha — pass birth UTC
    birth_utc = datetime(year, month, day, hour, minute, 0) - timedelta(hours=tzone)
    mahadashas, current_dasha = compute_vimshottari(birth_utc, moon["fullDegree"])

    # Ashtakavarga
    ashtakavarga, sarvashtaka = compute_ashtakavarga(planets, asc_sign_num)
    ashtakavarga_out = {**ashtakavarga, "sarvashtaka": sarvashtaka}

    # KP
    cusps12 = compute_placidus_cusps(jd_ut, lat, lon)
    kp_planets = build_kp_planets(planets, cusps12)
    kp_cusps = build_kp_cusps(cusps12)

    # Doshas
    doshas = compute_doshas(planets, asc_sign_num)

    # Divisional charts
    d1 = build_d1(planets, asc_sign_num)
    d9 = build_d9(planets, asc_lon)
    moon_chart = build_moon_chart(planets)

    return {
        "birth_details": birth_details,
        "astro_details": astro_details,
        "planets": planets,
        "divisional_charts": {
            "D1": d1,
            "D9": d9,
            "Moon": moon_chart,
        },
        "kp_planets": kp_planets,
        "kp_cusps": kp_cusps,
        "kp_house_significators": [],
        "kp_planet_significators": [],
        "dashas": {"vimshottari": mahadashas},
        "current_dasha": current_dasha,
        "ashtakavarga": ashtakavarga_out,
        "doshas": doshas,
        "panchang": {
            "tithi": panchang["tithi"],
            "nakshatra": moon_nak,
            "yoga": panchang["yoga"],
            "karana": panchang["karana"],
            "vaara": panchang["vaara"],
        },
    }
