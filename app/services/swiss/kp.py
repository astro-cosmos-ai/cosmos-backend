"""KP sub-lord computation + Placidus house assignment."""
from .ephemeris import sign_from_lon, nakshatra_from_lon, SIGN_LORDS, whole_sign_house

_DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
_DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}
_NAK_SPAN = 360 / 27
_DASHA_TOTAL = 120.0


def _sub_lord(longitude: float) -> str:
    norm = ((longitude % 360) + 360) % 360
    nak_idx = int(norm / _NAK_SPAN)
    pos_in_nak = norm - nak_idx * _NAK_SPAN
    start_idx = nak_idx % 9
    cursor = 0.0
    for i in range(9):
        lord = _DASHA_ORDER[(start_idx + i) % 9]
        dur = (_DASHA_YEARS[lord] * _NAK_SPAN) / _DASHA_TOTAL
        if pos_in_nak < cursor + dur:
            return lord
        cursor += dur
    return _DASHA_ORDER[(start_idx + 8) % 9]


def _sub_sub_lord(longitude: float) -> str:
    norm = ((longitude % 360) + 360) % 360
    nak_idx = int(norm / _NAK_SPAN)
    pos_in_nak = norm - nak_idx * _NAK_SPAN
    start_idx = nak_idx % 9
    cursor = 0.0
    for i in range(9):
        sub_idx = (start_idx + i) % 9
        sub_dur = (_DASHA_YEARS[_DASHA_ORDER[sub_idx]] * _NAK_SPAN) / _DASHA_TOTAL
        if pos_in_nak < cursor + sub_dur:
            pos_in_sub = pos_in_nak - cursor
            s_cursor = 0.0
            for j in range(9):
                ss = _DASHA_ORDER[(sub_idx + j) % 9]
                ss_dur = (_DASHA_YEARS[ss] * sub_dur) / _DASHA_TOTAL
                if pos_in_sub < s_cursor + ss_dur:
                    return ss
                s_cursor += ss_dur
            return _DASHA_ORDER[(sub_idx + 8) % 9]
        cursor += sub_dur
    return _DASHA_ORDER[(start_idx + 8) % 9]


def _placidus_house(planet_lon: float, cusps12: list[float]) -> int:
    norm = ((planet_lon % 360) + 360) % 360
    for i in range(12):
        start = ((cusps12[i] % 360) + 360) % 360
        end = ((cusps12[(i + 1) % 12] % 360) + 360) % 360
        in_house = (norm >= start and norm < end) if end > start else (norm >= start or norm < end)
        if in_house:
            return i + 1
    return 1


def _fmt_dms(deg_in_sign: float) -> str:
    d = int(deg_in_sign)
    m_total = (deg_in_sign - d) * 60
    m = int(m_total)
    s = round((m_total - m) * 60)
    return f"{d}° {m:02d}' {s:02d}\""


def build_kp_planets(planets: dict[str, dict], cusps12: list[float]) -> list[dict]:
    out = []
    for key, p in planets.items():
        if key == "ascendant":
            continue
        lon = p["fullDegree"]
        sub_lord = _sub_lord(lon)
        sub_sub = _sub_sub_lord(lon)
        plac_house = _placidus_house(lon, cusps12)
        out.append({
            "planet_name": p["name"],
            "sign": p["sign"],
            "house": plac_house,
            "sub_lord": sub_lord,
            "nakshatra": p["nakshatra"],
            "sign_lord": p["sign_lord"],
            "sub_sub_lord": sub_sub,
            "nakshatra_lord": p["nakshatraLord"],
            "formatted_norm_degree": _fmt_dms(p["normDegree"]),
            "is_retro": p["isRetro"] == "true",
        })
    return out


def build_kp_cusps(cusps12: list[float]) -> list[dict]:
    out = []
    for i, lon in enumerate(cusps12):
        sign_name, _, deg_in_sign = sign_from_lon(lon)
        nak_name, _, _, _ = nakshatra_from_lon(lon)
        out.append({
            "house_id": i + 1,
            "sign": sign_name,
            "sign_lord": SIGN_LORDS[sign_name],
            "nakshatra": nak_name,
            "sub_lord": _sub_lord(lon),
            "formatted_degree": _fmt_dms(deg_in_sign),
        })
    return out
