"""
Muhurta (electional astrology) service: finds auspicious dates/times based on
Vedic nakshatra, tithi, vara (weekday), and dasha suitability criteria.

All computation is rule-based — no LLM calls.
"""
from datetime import date, timedelta
from typing import Optional

_NAKSHATRAS = [
    "ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra",
    "punarvasu", "pushya", "ashlesha", "magha", "purva phalguni", "uttara phalguni",
    "hasta", "chitra", "swati", "vishakha", "anuradha", "jyeshtha",
    "mula", "purva ashadha", "uttara ashadha", "shravana", "dhanishtha",
    "shatabhisha", "purva bhadrapada", "uttara bhadrapada", "revati",
]

# Classification of nakshatras by muhurta quality for auspicious events
_AUSPICIOUS_NAKSHATRAS: dict[str, list[str]] = {
    "marriage":  ["rohini", "mrigashira", "magha", "uttara phalguni", "hasta", "swati",
                  "anuradha", "uttara ashadha", "uttara bhadrapada", "revati"],
    "travel":    ["ashwini", "mrigashira", "punarvasu", "pushya", "hasta", "swati",
                  "shravana", "dhanishtha", "revati"],
    "business":  ["rohini", "ashwini", "hasta", "pushya", "anuradha", "uttara ashadha",
                  "dhanishtha", "uttara phalguni", "uttara bhadrapada"],
    "education": ["ashwini", "mrigashira", "punarvasu", "pushya", "hasta", "chitra",
                  "swati", "anuradha", "shravana", "revati"],
    "health":    ["ashwini", "punarvasu", "pushya", "hasta", "uttara phalguni",
                  "uttara ashadha", "uttara bhadrapada", "revati"],
    "general":   ["ashwini", "rohini", "mrigashira", "punarvasu", "pushya", "uttara phalguni",
                  "hasta", "swati", "anuradha", "uttara ashadha", "uttara bhadrapada", "revati"],
}

_INAUSPICIOUS_NAKSHATRAS = ["bharani", "ardra", "ashlesha", "magha", "jyeshtha", "mula"]

# Tithis (lunar days 1–30) classified
_AUSPICIOUS_TITHIS = [2, 3, 5, 7, 10, 11, 13]  # Dwitiya, Tritiya, Panchami, Saptami, Dashami, Ekadashi, Trayodashi
_INAUSPICIOUS_TITHIS = [4, 8, 9, 14, 15, 30]   # Chaturthi, Ashtami, Navami, Chaturdashi, Purnima, Amavasya

# Vara (weekday) suitability
_AUSPICIOUS_VARAS: dict[str, list[int]] = {
    "marriage":  [1, 3, 4, 5],   # Sun, Wed, Thu, Fri
    "travel":    [0, 1, 3, 5],   # Mon, Sun, Wed, Fri
    "business":  [3, 4, 5],      # Wed, Thu, Fri
    "education": [3, 4],         # Wed, Thu
    "general":   [1, 3, 4, 5],
}

# Nakshatra moon transit: ~27 days per cycle, each nakshatra ~13.3 hours
_NAKSHATRA_DURATION_HOURS = 24 * 27 / 27  # ≈ 24h average (simplified)

_DASHA_SUITABILITY: dict[str, dict[str, list[str]]] = {
    "marriage":  {"favorable": ["venus", "jupiter", "moon"], "unfavorable": ["saturn", "rahu", "ketu"]},
    "travel":    {"favorable": ["mercury", "moon", "jupiter"], "unfavorable": ["saturn", "mars"]},
    "business":  {"favorable": ["mercury", "jupiter", "sun"], "unfavorable": ["saturn", "ketu"]},
    "education": {"favorable": ["mercury", "jupiter", "sun"], "unfavorable": ["rahu", "ketu"]},
    "health":    {"favorable": ["sun", "jupiter", "moon"], "unfavorable": ["saturn", "rahu", "mars"]},
    "general":   {"favorable": ["jupiter", "venus", "moon"], "unfavorable": ["saturn", "rahu", "ketu"]},
}


def _nakshatra_for_date(target_date: date, moon_sign: Optional[int]) -> Optional[str]:
    """
    Approximate nakshatra from moon sign and date offset.
    Each sign spans 2.25 nakshatras; we cycle through starting from moon's natal nakshatra.
    This is an approximation — a full ephemeris would give exact positions.
    """
    if moon_sign is None:
        return None
    # Moon moves ~13.17° per day → ~1 nakshatra every ~0.91 days
    # We use the date's day-of-year as a proxy offset
    doy = target_date.timetuple().tm_yday
    # Start nakshatra index from moon sign (each sign = 2.25 nakshatras)
    base_idx = int((moon_sign - 1) * 2.25) % 27
    offset = int(doy * 1.1) % 27  # ~1.1 nakshatras/day (approximation)
    idx = (base_idx + offset) % 27
    return _NAKSHATRAS[idx]


def _tithi_for_date(target_date: date) -> int:
    """
    Approximate tithi (1–30) using a fixed lunation cycle offset from a known new moon.
    Reference: New moon approx 2000-01-06.
    """
    reference = date(2000, 1, 6)
    days_since = (target_date - reference).days
    cycle_day = days_since % 30
    return (cycle_day % 30) + 1


def _classify_purpose(target_houses: list[int]) -> str:
    """Map target houses to the nearest muhurta purpose category."""
    house_set = set(target_houses)
    if {2, 7, 11} & house_set:
        return "marriage"
    if {6, 10} & house_set:
        return "business"
    if {3, 9, 12} & house_set:
        return "travel"
    if {4, 5, 9} & house_set:
        return "education"
    if {1, 6, 8} & house_set:
        return "health"
    return "general"


def _score_date(
    target_date: date,
    purpose: str,
    moon_sign: Optional[int],
    md_lord: str,
    ad_lord: str,
) -> dict:
    """Score a candidate date for muhurta suitability."""
    score = 0
    factors: list[str] = []
    warnings: list[str] = []

    # Nakshatra check
    nakshatra = _nakshatra_for_date(target_date, moon_sign)
    good_naks = _AUSPICIOUS_NAKSHATRAS.get(purpose, _AUSPICIOUS_NAKSHATRAS["general"])
    if nakshatra:
        if nakshatra in good_naks:
            score += 3
            factors.append(f"Auspicious nakshatra: {nakshatra.title()}")
        elif nakshatra in _INAUSPICIOUS_NAKSHATRAS:
            score -= 2
            warnings.append(f"Inauspicious nakshatra: {nakshatra.title()}")

    # Tithi check
    tithi = _tithi_for_date(target_date)
    if tithi in _AUSPICIOUS_TITHIS:
        score += 2
        factors.append(f"Favorable tithi: {tithi}")
    elif tithi in _INAUSPICIOUS_TITHIS:
        score -= 3
        warnings.append(f"Inauspicious tithi: {tithi} — avoid this lunar day")

    # Vara (weekday) check
    weekday = target_date.weekday()  # 0=Mon, 6=Sun
    good_varas = _AUSPICIOUS_VARAS.get(purpose, _AUSPICIOUS_VARAS["general"])
    if weekday in good_varas:
        score += 1
        factors.append(f"Favorable weekday: {target_date.strftime('%A')}")

    # Dasha lord suitability
    dasha_rules = _DASHA_SUITABILITY.get(purpose, _DASHA_SUITABILITY["general"])
    if md_lord.lower() in dasha_rules["favorable"] or ad_lord.lower() in dasha_rules["favorable"]:
        score += 2
        factors.append(f"Dasha lords ({md_lord}/{ad_lord}) favorable for {purpose}")
    if md_lord.lower() in dasha_rules["unfavorable"] or ad_lord.lower() in dasha_rules["unfavorable"]:
        score -= 1
        warnings.append(f"Dasha lords ({md_lord}/{ad_lord}) have some tension for {purpose}")

    return {
        "date": str(target_date),
        "weekday": target_date.strftime("%A"),
        "nakshatra": nakshatra,
        "tithi": tithi,
        "score": score,
        "factors": factors,
        "warnings": warnings,
    }


def find_muhurta_dates(
    chart_row: dict,
    target_houses: list[int],
    search_start: date,
    search_end: date,
    top_n: int = 5,
) -> list[dict]:
    """
    Scans dates from search_start to search_end and returns the top_n most auspicious dates.

    Uses approximate nakshatra/tithi computation — a full ephemeris integration would improve accuracy.
    """
    planets = chart_row.get("planets") or {}
    moon = planets.get("moon") or {}
    moon_sign = moon.get("current_sign")

    current_dasha = chart_row.get("current_dasha") or {}
    md_lord = current_dasha.get("major_dasha") or current_dasha.get("maha_dasha") or "unknown"
    ad_lord = current_dasha.get("antar_dasha") or current_dasha.get("antar") or "unknown"

    purpose = _classify_purpose(target_houses)
    candidates = []

    current = search_start
    while current <= search_end:
        scored = _score_date(current, purpose, moon_sign, md_lord, ad_lord)
        if scored["score"] > 0:  # Only include net-positive dates
            candidates.append(scored)
        current += timedelta(days=1)

    candidates.sort(key=lambda d: -d["score"])
    return candidates[:top_n]
