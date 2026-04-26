"""
Parashari significator engine.

For each house 1-12 computes:
  lord      — sign ruler of the cusp
  occupants — planets in the house (whole-sign)
  aspecting — planets whose aspects reach this house
  karaka    — natural significator of the house
"""
from .aspects import planets_aspecting_house

SIGN_LORDS = {
    1: "mars", 2: "venus", 3: "mercury", 4: "moon", 5: "sun", 6: "mercury",
    7: "venus", 8: "mars", 9: "jupiter", 10: "saturn", 11: "saturn", 12: "jupiter",
}

NATURAL_KARAKAS = {
    1: "sun", 2: "jupiter", 3: "mars", 4: "moon", 5: "jupiter", 6: "mars",
    7: "venus", 8: "saturn", 9: "jupiter", 10: "mercury", 11: "jupiter", 12: "saturn",
}


def _sign_on_house(house: int, asc_sign: int) -> int:
    return ((asc_sign + house - 2) % 12) + 1


def compute_all_significators(chart_json: dict) -> dict:
    """
    Returns {house_num: {lord, occupants, aspecting, karaka}} for houses 1-12.
    Reads from chart_json['planets'] and chart_json['astro_details'].
    """
    planets = chart_json.get("planets") or {}
    astro = chart_json.get("astro_details") or {}

    asc_sign_name = (astro.get("ascendant") or "").lower()
    asc_sign = _sign_name_to_num(asc_sign_name) or 1

    result = {}
    for house in range(1, 13):
        sign_on_cusp = _sign_on_house(house, asc_sign)
        lord = SIGN_LORDS.get(sign_on_cusp, "unknown")

        occupants = [
            name for name, data in planets.items()
            if data.get("house_parashari") == house
        ]

        aspecting = planets_aspecting_house(house, planets)

        result[str(house)] = {
            "house": house,
            "sign": sign_on_cusp,
            "lord": lord,
            "occupants": occupants,
            "aspecting": aspecting,
            "karaka": NATURAL_KARAKAS.get(house),
        }

    return result


SIGN_NAMES = ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
              "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]


def _sign_name_to_num(sign_name: str) -> int | None:
    try:
        return SIGN_NAMES.index(sign_name.lower()) + 1
    except ValueError:
        return None
