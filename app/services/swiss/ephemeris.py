"""Core planet position and house computation via pyswisseph (Moshier, sidereal)."""
from datetime import datetime, timedelta
import swisseph as swe

# Moshier + sidereal + speed — no .se1 files needed
_FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_LORDS: dict[str, str] = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
]

NAKSHATRA_INFO: dict[str, dict] = {
    "Ashwini":           {"yoni": "Horse",     "gana": "Deva",     "nadi": "Adi",    "syllables": ["Chu", "Che", "Cho", "La"]},
    "Bharani":           {"yoni": "Elephant",  "gana": "Manushya", "nadi": "Madhya", "syllables": ["Li", "Lu", "Le", "Lo"]},
    "Krittika":          {"yoni": "Sheep",     "gana": "Rakshasa", "nadi": "Antya",  "syllables": ["A", "I", "U", "E"]},
    "Rohini":            {"yoni": "Serpent",   "gana": "Manushya", "nadi": "Antya",  "syllables": ["O", "Va", "Vi", "Vu"]},
    "Mrigashira":        {"yoni": "Serpent",   "gana": "Deva",     "nadi": "Madhya", "syllables": ["Ve", "Vo", "Ka", "Ki"]},
    "Ardra":             {"yoni": "Dog",       "gana": "Manushya", "nadi": "Adi",    "syllables": ["Ku", "Gha", "Nga", "Chha"]},
    "Punarvasu":         {"yoni": "Cat",       "gana": "Deva",     "nadi": "Adi",    "syllables": ["Ke", "Ko", "Ha", "Hi"]},
    "Pushya":            {"yoni": "Sheep",     "gana": "Deva",     "nadi": "Madhya", "syllables": ["Hu", "He", "Ho", "Da"]},
    "Ashlesha":          {"yoni": "Cat",       "gana": "Rakshasa", "nadi": "Antya",  "syllables": ["Di", "Du", "De", "Do"]},
    "Magha":             {"yoni": "Rat",       "gana": "Rakshasa", "nadi": "Antya",  "syllables": ["Ma", "Mi", "Mu", "Me"]},
    "Purva Phalguni":    {"yoni": "Rat",       "gana": "Manushya", "nadi": "Madhya", "syllables": ["Mo", "Ta", "Ti", "Tu"]},
    "Uttara Phalguni":   {"yoni": "Cow",       "gana": "Manushya", "nadi": "Adi",    "syllables": ["Te", "To", "Pa", "Pi"]},
    "Hasta":             {"yoni": "Buffalo",   "gana": "Deva",     "nadi": "Adi",    "syllables": ["Pu", "Sha", "Na", "Tha"]},
    "Chitra":            {"yoni": "Tiger",     "gana": "Rakshasa", "nadi": "Madhya", "syllables": ["Pe", "Po", "Ra", "Ri"]},
    "Swati":             {"yoni": "Buffalo",   "gana": "Deva",     "nadi": "Antya",  "syllables": ["Ru", "Re", "Ro", "Ta"]},
    "Vishakha":          {"yoni": "Tiger",     "gana": "Rakshasa", "nadi": "Antya",  "syllables": ["Ti", "Tu", "Te", "To"]},
    "Anuradha":          {"yoni": "Deer",      "gana": "Deva",     "nadi": "Madhya", "syllables": ["Na", "Ni", "Nu", "Ne"]},
    "Jyeshtha":          {"yoni": "Deer",      "gana": "Rakshasa", "nadi": "Adi",    "syllables": ["No", "Ya", "Yi", "Yu"]},
    "Mula":              {"yoni": "Dog",       "gana": "Rakshasa", "nadi": "Adi",    "syllables": ["Ye", "Yo", "Bha", "Bhi"]},
    "Purva Ashadha":     {"yoni": "Monkey",    "gana": "Manushya", "nadi": "Madhya", "syllables": ["Bhu", "Dha", "Pha", "Dha"]},
    "Uttara Ashadha":    {"yoni": "Mongoose",  "gana": "Manushya", "nadi": "Antya",  "syllables": ["Bhe", "Bho", "Ja", "Ji"]},
    "Shravana":          {"yoni": "Monkey",    "gana": "Deva",     "nadi": "Antya",  "syllables": ["Ju", "Je", "Jo", "Gha"]},
    "Dhanishta":         {"yoni": "Lion",      "gana": "Rakshasa", "nadi": "Madhya", "syllables": ["Ga", "Gi", "Gu", "Ge"]},
    "Shatabhisha":       {"yoni": "Horse",     "gana": "Rakshasa", "nadi": "Adi",    "syllables": ["Go", "Sa", "Si", "Su"]},
    "Purva Bhadrapada":  {"yoni": "Lion",      "gana": "Manushya", "nadi": "Adi",    "syllables": ["Se", "So", "Da", "Di"]},
    "Uttara Bhadrapada": {"yoni": "Cow",       "gana": "Manushya", "nadi": "Madhya", "syllables": ["Du", "Tha", "Jha", "Tra"]},
    "Revati":            {"yoni": "Elephant",  "gana": "Deva",     "nadi": "Antya",  "syllables": ["De", "Do", "Cha", "Chi"]},
}

# Planets to compute (Rahu node mode resolved at call time; Ketu derived)
_PLANET_IDS_BASE: list[tuple[str, int]] = [
    ("Sun",     swe.SUN),
    ("Moon",    swe.MOON),
    ("Mars",    swe.MARS),
    ("Mercury", swe.MERCURY),
    ("Jupiter", swe.JUPITER),
    ("Venus",   swe.VENUS),
    ("Saturn",  swe.SATURN),
]


def _rahu_id(node_mode: str) -> int:
    return swe.TRUE_NODE if node_mode == "true" else swe.MEAN_NODE


def _norm(lon: float) -> float:
    return ((lon % 360) + 360) % 360


def sign_from_lon(lon: float) -> tuple[str, int, float]:
    """Returns (sign_name, sign_num 1-12, degrees_in_sign)."""
    n = _norm(lon)
    sign_num = int(n / 30) + 1
    return SIGNS[sign_num - 1], sign_num, n - (sign_num - 1) * 30


def nakshatra_from_lon(lon: float) -> tuple[str, int, str, int]:
    """Returns (nakshatra_name, pada 1-4, nakshatra_lord, nak_index 0-26)."""
    n = _norm(lon)
    span = 360 / 27
    idx = int(n / span)
    within = n - idx * span
    pada = int(within / (span / 4)) + 1
    return NAKSHATRAS[idx], pada, NAKSHATRA_LORDS[idx], idx


def whole_sign_house(planet_sign: int, asc_sign: int) -> int:
    return ((planet_sign - asc_sign) % 12) + 1


def birth_to_jd_ut(year: int, month: int, day: int, hour: int, minute: int, tzone: float) -> float:
    """Convert local birth time + UTC offset to Julian Day (UT)."""
    local = datetime(year, month, day, hour, minute, 0)
    utc = local - timedelta(hours=tzone)
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute / 60.0 + utc.second / 3600.0)


def compute_planets(jd_ut: float, asc_sign: int, node_mode: str = "mean") -> dict[str, dict]:
    """Compute all 9 Jyotish planets (incl. Ketu) + Ascendant. Returns dict keyed lowercase."""
    planets: dict[str, dict] = {}
    rahu_lon: float = 0.0
    planet_ids = _PLANET_IDS_BASE + [("Rahu", _rahu_id(node_mode))]

    for name, pid in planet_ids:
        xx, _ = swe.calc_ut(jd_ut, pid, _FLAGS)
        lon = xx[0]
        speed = xx[3]
        if name == "Rahu":
            rahu_lon = lon

        sign_name, sign_num, deg_in_sign = sign_from_lon(lon)
        nak_name, pada, nak_lord, _ = nakshatra_from_lon(lon)
        house = whole_sign_house(sign_num, asc_sign)

        planets[name.lower()] = {
            "name": name,
            "current_sign": sign_num,
            "sign": sign_name,
            "sign_name": sign_name,
            "sign_lord": SIGN_LORDS[sign_name],
            "signLord": SIGN_LORDS[sign_name],
            "house_parashari": house,
            "nakshatra": nak_name,
            "nakshatra_pad": pada,
            "nakshatraLord": nak_lord,
            "fullDegree": lon,
            "normDegree": deg_in_sign,
            "isRetro": "true" if speed < 0 else "false",
            "speed": speed,
        }

    # Ketu = Rahu + 180°
    ketu_lon = _norm(rahu_lon + 180)
    sign_name, sign_num, deg_in_sign = sign_from_lon(ketu_lon)
    nak_name, pada, nak_lord, _ = nakshatra_from_lon(ketu_lon)
    planets["ketu"] = {
        "name": "Ketu",
        "current_sign": sign_num,
        "sign": sign_name,
        "sign_name": sign_name,
        "sign_lord": SIGN_LORDS[sign_name],
        "signLord": SIGN_LORDS[sign_name],
        "house_parashari": whole_sign_house(sign_num, asc_sign),
        "nakshatra": nak_name,
        "nakshatra_pad": pada,
        "nakshatraLord": nak_lord,
        "fullDegree": ketu_lon,
        "normDegree": deg_in_sign,
        "isRetro": planets["rahu"]["isRetro"],
        "speed": -planets["rahu"]["speed"],
    }

    return planets


def compute_ascendant(jd_ut: float, lat: float, lon: float) -> tuple[float, str, int, float]:
    """Returns (asc_lon, sign_name, sign_num, deg_in_sign) using whole-sign houses."""
    # houses_ex signature: (tjdut, lat, lon, hsys, flags)
    _, ascmc = swe.houses_ex(jd_ut, lat, lon, b"W", swe.FLG_SIDEREAL)
    asc_lon = ascmc[0]
    sign_name, sign_num, deg_in_sign = sign_from_lon(asc_lon)
    return asc_lon, sign_name, sign_num, deg_in_sign


def compute_placidus_cusps(jd_ut: float, lat: float, lon: float) -> list[float]:
    """Returns 12 Placidus house cusp longitudes (sidereal, 0-indexed 0..11) for KP system."""
    cusps, _ = swe.houses_ex(jd_ut, lat, lon, b"P", swe.FLG_SIDEREAL)
    return list(cusps)  # already 12 items, 0-indexed


def get_ayanamsa(jd_ut: float) -> float:
    return swe.get_ayanamsa_ut(jd_ut)
