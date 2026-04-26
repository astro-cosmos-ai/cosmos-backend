"""
Ashtakavarga bindu strength lookup for transiting planets.
Reads the ashtakavarga JSONB from the chart row.

AstrologyAPI planet_ashtak/{planet} response shapes handled:
  Shape A: {"ashtak_varga": [{"sign": 1, "benefic_points": 5}, ...]}
  Shape B: {"ashtak_varga": {"1": 5, "2": 3, ...}}
  Shape C: [5, 3, 4, ...]  (bare list indexed 0=sign1)
"""

_QUALITY_THRESHOLDS = {"strong": 5, "neutral": 3}  # ≥5 strong, ≥3 neutral, else weak


def _extract_bindus(planet_data: dict | list | None) -> dict[int, int] | None:
    """
    Normalizes any of the three shapes into {sign_num: bindu_count}.
    sign_num is 1-indexed (1=Aries … 12=Pisces).
    """
    if planet_data is None:
        return None

    # Shape C: bare list
    if isinstance(planet_data, list):
        return {i + 1: int(v) for i, v in enumerate(planet_data) if str(v).isdigit()}

    raw = planet_data.get("ashtak_varga") if isinstance(planet_data, dict) else None
    if raw is None:
        return None

    # Shape A: list of dicts
    if isinstance(raw, list):
        result = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            sign = item.get("sign") or item.get("sign_num")
            bindus = item.get("benefic_points") or item.get("bindus") or item.get("points")
            if sign and bindus is not None:
                result[int(sign)] = int(bindus)
        return result or None

    # Shape B: dict keyed by sign string
    if isinstance(raw, dict):
        return {int(k): int(v) for k, v in raw.items() if str(k).isdigit() and str(v).isdigit()}

    return None


def get_transit_bindu_strength(
    chart_row: dict,
    planet_name: str,
    transit_sign: int,
) -> int | None:
    """
    Returns the bindu count for planet_name in transit_sign.
    Returns None if data is unavailable.
    """
    av = chart_row.get("ashtakavarga") or {}
    planet_data = av.get(planet_name.lower()) or av.get(planet_name.title())
    bindus = _extract_bindus(planet_data)
    if not bindus:
        return None
    return bindus.get(transit_sign)


def assess_transit_quality(
    chart_row: dict,
    transit_snapshot: dict,
) -> dict[str, dict]:
    """
    For each transiting planet returns sign, bindu count, and quality label.
    quality: "strong" (≥5), "neutral" (3–4), "weak" (<3), or "unknown".
    """
    planets = transit_snapshot.get("planets") or {}
    result: dict[str, dict] = {}
    for pname, pdata in planets.items():
        sign = pdata.get("transit_sign")
        bindus = get_transit_bindu_strength(chart_row, pname, sign) if sign else None
        if bindus is None:
            quality = "unknown"
        elif bindus >= _QUALITY_THRESHOLDS["strong"]:
            quality = "strong"
        elif bindus >= _QUALITY_THRESHOLDS["neutral"]:
            quality = "neutral"
        else:
            quality = "weak"
        result[pname] = {
            "sign": sign,
            "sign_name": pdata.get("sign_name", ""),
            "transit_house": pdata.get("transit_house"),
            "bindus": bindus,
            "quality": quality,
        }
    return result
