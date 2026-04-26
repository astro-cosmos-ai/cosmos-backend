"""
Builds section-specific structured context strings for LLM consumption.
Each function returns a clean, token-efficient string.
"""
from .dignity import get_dignity
from .atmakaraka import get_atmakaraka


def _planet_line(name: str, data: dict, house_label: str = "") -> str:
    sign = data.get("sign_name") or data.get("sign") or "?"
    house = data.get("house_parashari", "?")
    nakshatra = data.get("nakshatra") or "?"
    is_retro = data.get("isRetro")
    retro = " (R)" if (is_retro is True or is_retro == "true" or data.get("retro") is True) else ""
    dignity = get_dignity(name, data.get("current_sign") or 0)
    return f"{name.title()}{retro}: {sign}, House {house}, {nakshatra} nakshatra, {dignity}{' — ' + house_label if house_label else ''}"


def _current_dasha(dasha: dict | None) -> str:
    if not dasha:
        return "Current dasha: unknown"
    md = (dasha.get("major") or {}).get("planet") or dasha.get("major_dasha") or dasha.get("maha_dasha") or "?"
    ad = (dasha.get("minor") or {}).get("planet") or dasha.get("antar_dasha") or dasha.get("antar") or "?"
    return f"Current Dasha: {md} (MD) — {ad} (AD)"


def _significators_for_houses(sig_map: dict, houses: list[int]) -> str:
    lines = []
    for h in houses:
        data = sig_map.get(str(h)) or {}
        lord = data.get("lord", "?")
        occ = ", ".join(data.get("occupants", [])) or "none"
        asp = ", ".join(data.get("aspecting", [])) or "none"
        lines.append(f"  House {h}: Lord={lord.title()}, Occupants=[{occ}], Aspecting=[{asp}]")
    return "\n".join(lines)


def _kp_cusp_info(kp_sig: dict | None, house: int) -> str:
    if not kp_sig:
        return ""
    house_data = None
    if isinstance(kp_sig, list):
        for item in kp_sig:
            if isinstance(item, dict) and str(item.get("house")) == str(house):
                house_data = item
                break
    elif isinstance(kp_sig, dict):
        house_data = kp_sig.get(str(house))
    if not house_data:
        return ""
    sub_lord = house_data.get("sub_lord") or house_data.get("SubLord") or "?"
    signifies = house_data.get("significators") or []
    return f"KP House {house} sub-lord: {sub_lord} → signifies houses {signifies}"


def build_personality_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")

    asc = astro.get("ascendant", "?")
    moon_sign = astro.get("moon_sign") or astro.get("moonsign") or (planets.get("moon") or {}).get("sign") or "?"
    nakshatra = astro.get("nakshatra") or astro.get("Naksahtra") or (planets.get("moon") or {}).get("nakshatra") or "?"

    atmakaraka = get_atmakaraka(planets)
    house1_sig = _significators_for_houses(sig, [1])

    lines = [
        f"ASCENDANT: {asc}",
        f"MOON SIGN: {moon_sign}",
        f"BIRTH NAKSHATRA: {nakshatra}",
        f"ATMAKARAKA: {atmakaraka or 'unknown'}",
        "",
        "RELEVANT PLANETS:",
    ]

    for planet in ["sun", "moon", "ascendant_lord"]:
        if planet == "ascendant_lord":
            # find ascendant lord from 1st house significator
            asc_lord = (sig.get("1") or {}).get("lord")
            if asc_lord and asc_lord in planets:
                lines.append(f"  Ascendant Lord ({asc_lord.title()}): " + _planet_line(asc_lord, planets[asc_lord]))
        elif planet in planets:
            lines.append(f"  {_planet_line(planet, planets[planet])}")

    planets_in_1st = (sig.get("1") or {}).get("occupants", [])
    if planets_in_1st:
        for p in planets_in_1st:
            if p in planets:
                lines.append(f"  {_planet_line(p, planets[p], '1st house occupant')}")

    lines += [
        "",
        "HOUSE 1 SIGNIFICATORS (Parashari):",
        house1_sig,
        "",
        _kp_cusp_info(kp_house_sig, 1) or "",
        "",
        _current_dasha(dasha),
    ]

    return "\n".join(l for l in lines if l is not None)


def build_career_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}
    kp_planet_sig = chart_json.get("kp_planet_significators")

    house_sig = _significators_for_houses(sig, [6, 10, 11, 2])

    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "CAREER-RELEVANT HOUSES (Parashari significators):",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 10) or "  KP 10th cusp: unavailable",
        _kp_cusp_info(kp_house_sig, 6) or "",
        "",
        "KEY PLANETS:",
    ]

    for planet in ["sun", "mercury", "saturn", "mars", "jupiter"]:
        if planet in planets:
            lines.append(f"  {_planet_line(planet, planets[planet])}")

    # D10 summary
    d10 = div.get("D10")
    if d10:
        lines += ["", "D10 DASAMSA: available (see chart data)"]

    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_marriage_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    doshas = chart_json.get("doshas") or {}

    house_sig = _significators_for_houses(sig, [2, 7, 11])
    manglik = doshas.get("manglik") or {}

    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "MARRIAGE HOUSES (2, 7, 11) — Parashari Significators:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 7) or "  KP 7th cusp: unavailable",
        "",
        "VENUS (Marriage Karaka):",
    ]

    venus = planets.get("venus")
    if venus:
        lines.append(f"  {_planet_line('venus', venus)}")

    lines += [
        "",
        f"MANGLIK: {manglik.get('present', manglik.get('is_manglik_present', 'unknown'))} (severity: {manglik.get('status', manglik.get('manglik_status', 'unknown'))})",
        "",
        _current_dasha(dasha),
    ]

    return "\n".join(l for l in lines if l is not None)


def build_mind_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")

    house_sig = _significators_for_houses(sig, [4])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        f"MOON SIGN: {astro.get('moon_sign') or astro.get('moonsign') or (planets.get('moon') or {}).get('sign') or '?'}",
        f"BIRTH NAKSHATRA: {astro.get('nakshatra') or astro.get('Naksahtra') or (planets.get('moon') or {}).get('nakshatra') or '?'}",
        "",
        "MOON (Mind Karaka):",
    ]
    if "moon" in planets:
        lines.append(f"  {_planet_line('moon', planets['moon'])}")
    if "mercury" in planets:
        lines.append(f"  {_planet_line('mercury', planets['mercury'])}")
    lines += [
        "",
        "4th HOUSE (Emotional Foundation) — Parashari:",
        house_sig,
        "",
        _kp_cusp_info(kp_house_sig, 4) or "",
        "",
        _current_dasha(dasha),
    ]
    return "\n".join(l for l in lines if l is not None)


def build_skills_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    dasha = chart_json.get("current_dasha")

    house_sig = _significators_for_houses(sig, [2, 3, 5])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "SKILL HOUSES (2, 3, 5) — Parashari:",
        house_sig,
        "",
        "KEY PLANETS FOR SKILLS:",
    ]
    for p in ["mercury", "jupiter", "venus", "mars", "saturn", "rahu"]:
        if p in planets:
            lines.append(f"  {_planet_line(p, planets[p])}")
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_wealth_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}

    house_sig = _significators_for_houses(sig, [2, 5, 8, 9, 11])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "WEALTH HOUSES (2, 5, 8, 9, 11) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 2) or "  KP 2nd cusp: unavailable",
        _kp_cusp_info(kp_house_sig, 11) or "",
        "",
        "JUPITER (Wealth Karaka):",
    ]
    if "jupiter" in planets:
        lines.append(f"  {_planet_line('jupiter', planets['jupiter'])}")
    if div.get("D2"):
        lines += ["", "D2 HORA: available (see chart data)"]
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_foreign_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}

    house_sig = _significators_for_houses(sig, [3, 7, 9, 12])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "FOREIGN TRAVEL HOUSES (3, 7, 9, 12) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 12) or "  KP 12th cusp: unavailable",
        _kp_cusp_info(kp_house_sig, 9) or "",
        "",
        "RAHU (Foreign Karaka):",
    ]
    if "rahu" in planets:
        lines.append(f"  {_planet_line('rahu', planets['rahu'])}")
    if div.get("D4"):
        lines += ["", "D4 CHATURTHAMSA: available (see chart data)"]
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_romance_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")

    house_sig = _significators_for_houses(sig, [5, 8, 11])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "ROMANCE HOUSES (5, 8, 11) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 5) or "  KP 5th cusp: unavailable",
        "",
        "VENUS (Romance Karaka):",
    ]
    if "venus" in planets:
        lines.append(f"  {_planet_line('venus', planets['venus'])}")
    moon = planets.get("moon") or {}
    nakshatra = moon.get("nakshatra") or astro.get("nakshatra", "?")
    lines += [
        "",
        f"MOON NAKSHATRA: {nakshatra}",
        "",
        _current_dasha(dasha),
    ]
    return "\n".join(l for l in lines if l is not None)


def build_business_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}

    house_sig = _significators_for_houses(sig, [3, 7, 10, 11])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "BUSINESS HOUSES (3, 7, 10, 11) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 7) or "  KP 7th cusp: unavailable",
        _kp_cusp_info(kp_house_sig, 10) or "",
        "",
        "KEY PLANETS:",
    ]
    for p in ["mercury", "saturn", "mars", "jupiter"]:
        if p in planets:
            lines.append(f"  {_planet_line(p, planets[p])}")
    if div.get("D10"):
        lines += ["", "D10 DASAMSA: available — check 7th house of D10 for business"]
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_property_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}

    house_sig = _significators_for_houses(sig, [4, 11])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "PROPERTY HOUSES (4, 11) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 4) or "  KP 4th cusp: unavailable",
        "",
        "MARS & VENUS (Property Karakas):",
    ]
    for p in ["mars", "venus"]:
        if p in planets:
            lines.append(f"  {_planet_line(p, planets[p])}")
    if div.get("D4"):
        lines += ["", "D4 CHATURTHAMSA: available (property/fixed assets chart)"]
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_health_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    ashtakavarga = chart_json.get("ashtakavarga") or {}

    house_sig = _significators_for_houses(sig, [1, 6, 8, 12])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "HEALTH HOUSES (1, 6, 8, 12) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 6) or "  KP 6th cusp: unavailable",
        _kp_cusp_info(kp_house_sig, 8) or "",
        "",
        "LAGNA LORD (Vitality Indicator):",
    ]
    asc_lord = (sig.get("1") or {}).get("lord")
    if asc_lord and asc_lord in planets:
        lines.append(f"  {_planet_line(asc_lord, planets[asc_lord])}")
    if "sun" in planets:
        lines.append(f"  {_planet_line('sun', planets['sun'])}")
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_education_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}

    house_sig = _significators_for_houses(sig, [4, 5, 9])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "EDUCATION HOUSES (4, 5, 9) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 5) or "  KP 5th cusp: unavailable",
        _kp_cusp_info(kp_house_sig, 9) or "",
        "",
        "JUPITER & MERCURY (Education Karakas):",
    ]
    for p in ["jupiter", "mercury"]:
        if p in planets:
            lines.append(f"  {_planet_line(p, planets[p])}")
    if div.get("D24"):
        lines += ["", "D24 SIDDHAMSA: available (higher education chart)"]
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_parents_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")

    mother_sig = _significators_for_houses(sig, [4])
    father_sig = _significators_for_houses(sig, [9])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "4th HOUSE — MOTHER (Parashari):",
        mother_sig,
        _kp_cusp_info(kp_house_sig, 4) or "",
        "",
        "9th HOUSE — FATHER (Parashari):",
        father_sig,
        _kp_cusp_info(kp_house_sig, 9) or "",
        "",
        "MOON (Mother Karaka):",
    ]
    if "moon" in planets:
        lines.append(f"  {_planet_line('moon', planets['moon'])}")
    lines.append("SUN (Father Karaka):")
    if "sun" in planets:
        lines.append(f"  {_planet_line('sun', planets['sun'])}")
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_siblings_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}

    house_sig = _significators_for_houses(sig, [3, 11])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "SIBLINGS HOUSES (3=younger, 11=elder) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 3) or "  KP 3rd cusp: unavailable",
        "",
        "MARS (Siblings Karaka):",
    ]
    if "mars" in planets:
        lines.append(f"  {_planet_line('mars', planets['mars'])}")
    if div.get("D3"):
        lines += ["", "D3 DREKKANA: available (siblings chart)"]
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_children_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}

    house_sig = _significators_for_houses(sig, [5])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "5th HOUSE (Children) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 5) or "  KP 5th cusp: unavailable",
        "",
        "JUPITER (Putrakaraka — Child Significator):",
    ]
    if "jupiter" in planets:
        lines.append(f"  {_planet_line('jupiter', planets['jupiter'])}")
    if div.get("D7"):
        lines += ["", "D7 SAPTAMSA: available (children chart)"]
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_spirituality_context(chart_json: dict) -> str:
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    kp_house_sig = chart_json.get("kp_house_significators")
    dasha = chart_json.get("current_dasha")
    div = chart_json.get("divisional_charts") or {}

    house_sig = _significators_for_houses(sig, [4, 8, 9, 12])
    lines = [
        f"ASCENDANT: {astro.get('ascendant', '?')}",
        "",
        "SPIRITUAL HOUSES (4, 8, 9, 12) — Parashari:",
        house_sig,
        "",
        "KP CUSP SUB-LORDS:",
        _kp_cusp_info(kp_house_sig, 12) or "  KP 12th cusp: unavailable",
        _kp_cusp_info(kp_house_sig, 9) or "",
        "",
        "KETU (Moksha Karaka):",
    ]
    if "ketu" in planets:
        lines.append(f"  {_planet_line('ketu', planets['ketu'])}")
    if "jupiter" in planets:
        lines.append(f"  {_planet_line('jupiter', planets['jupiter'])}")
    if div.get("D20"):
        lines += ["", "D20 VIMSHAMSA: available (spiritual growth chart)"]
    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_chat_context(chart_json: dict) -> str:
    """Compact full-chart summary for conversational chat context."""
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}
    sig = chart_json.get("parashari_significators") or {}
    dasha = chart_json.get("current_dasha")
    yogas = chart_json.get("yogas") or []

    asc = astro.get("ascendant", "?")
    moon_sign = astro.get("moon_sign") or astro.get("moonsign") or (planets.get("moon") or {}).get("sign") or "?"
    nakshatra = astro.get("nakshatra") or astro.get("Naksahtra") or (planets.get("moon") or {}).get("nakshatra") or "?"
    atmakaraka = get_atmakaraka(planets)

    lines = [
        "=== CHART SUMMARY ===",
        f"Ascendant: {asc} | Moon Sign: {moon_sign} | Birth Nakshatra: {nakshatra}",
        f"Atmakaraka: {atmakaraka or 'unknown'}",
        "",
        "ALL PLANETS:",
    ]
    for pname, pdata in planets.items():
        if isinstance(pdata, dict):
            lines.append(f"  {_planet_line(pname, pdata)}")

    lines += ["", "HOUSE LORDS (all 12):"]
    for h in range(1, 13):
        lord = (sig.get(str(h)) or {}).get("lord", "?")
        occ = ", ".join((sig.get(str(h)) or {}).get("occupants", [])) or "empty"
        lines.append(f"  H{h}: lord={lord.title()}, occupants=[{occ}]")

    if yogas:
        lines += ["", f"ACTIVE YOGAS: {', '.join(y.get('name', '') for y in yogas[:8])}"]

    lines += ["", _current_dasha(dasha)]
    return "\n".join(l for l in lines if l is not None)


def build_varshaphal_context(chart_json: dict) -> str:
    """
    Build context string for Varshaphal (annual solar return) analysis.

    Calls get_varshaphal(chart_json, current_year) to assemble the annual chart
    from pre-loaded chart_json['varshaphal_raw'].  Raises ValueError if the raw
    data is absent (caller should catch and surface as HTTP 422).
    """
    from datetime import date
    from app.services.varshaphal_service import get_varshaphal

    year = date.today().year
    varsha = get_varshaphal(chart_json, year)
    if not varsha:
        raise ValueError("Varshaphal data not loaded")

    astro = chart_json.get("astro_details") or {}
    natal_planets = chart_json.get("planets") or {}
    current_dasha = chart_json.get("current_dasha") or {}

    lines = [
        f"VARSHAPHAL YEAR: {varsha['year']} (Age {varsha.get('age', '?')})",
        f"NATAL ASCENDANT: {varsha['natal_ascendant']}",
        f"YEAR LORD (Varshapati): {varsha['year_lord'].title()}",
        f"CURRENT NATAL DASHA: {(current_dasha.get('major') or {}).get('planet') or current_dasha.get('major_dasha', '?')} MD / {(current_dasha.get('minor') or {}).get('planet') or current_dasha.get('antar_dasha', '?')} AD",
        "",
        "NATAL CHART (for reference):",
    ]
    for pname, pdata in natal_planets.items():
        sign = pdata.get("sign_name") or "?"
        house = pdata.get("house_parashari", "?")
        retro = " (R)" if pdata.get("isRetro") else ""
        lines.append(f"  Natal {pname.title()}{retro}: {sign}, House {house}")

    lines += ["", "ANNUAL CHART DATA:"]
    for pname, pdata in (varsha.get("planets") or {}).items():
        sign = pdata.get("sign_name") or "?"
        house = pdata.get("house", "?")
        retro = " (R)" if pdata.get("retrograde") else ""
        dignity = pdata.get("dignity") or ""
        lines.append(f"  Annual {pname.title()}{retro}: {sign}, House {house}, {dignity}")

    sig = varsha.get("significators") or {}
    if sig:
        lines += ["", "ANNUAL SIGNIFICATORS:"]
        for h in range(1, 13):
            data = sig.get(str(h)) or {}
            lord = data.get("lord", "?")
            occ = ", ".join(data.get("occupants", [])) or "none"
            lines.append(f"  House {h}: Lord={lord.title()}, Occupants=[{occ}]")

    return "\n".join(lines)


CONTEXT_BUILDERS = {
    "personality": build_personality_context,
    "career": build_career_context,
    "marriage": build_marriage_context,
    "mind": build_mind_context,
    "skills": build_skills_context,
    "wealth": build_wealth_context,
    "foreign": build_foreign_context,
    "romance": build_romance_context,
    "business": build_business_context,
    "property": build_property_context,
    "health": build_health_context,
    "education": build_education_context,
    "parents": build_parents_context,
    "siblings": build_siblings_context,
    "children": build_children_context,
    "spirituality": build_spirituality_context,
}
