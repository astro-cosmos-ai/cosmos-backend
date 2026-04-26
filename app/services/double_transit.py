"""
Double transit detection: checks whether Jupiter and Saturn jointly
occupy or aspect each of the 12 houses.
Based on the Krishnamurti/classical rule: events manifest when both
Jupiter and Saturn simultaneously influence the relevant house.
"""
from app.services.harness.aspects import houses_aspected_by


def _planet_influences(planet_house: int, planet_name: str) -> set[int]:
    """Returns all houses influenced by a planet (occupation + aspects)."""
    aspected = set(houses_aspected_by(planet_house, planet_name))
    aspected.add(planet_house)
    return aspected


def compute_double_transit(
    transit_snapshot: dict,
    natal_chart: dict,  # kept for future natal-overlay use
) -> dict[int, dict]:
    """
    Returns a dict keyed by house number (1–12) with:
      - jupiter: bool (Jupiter occupies or aspects this house in transit)
      - saturn:  bool (Saturn occupies or aspects this house in transit)
      - double:  bool (both simultaneously influence this house)
    """
    planets = transit_snapshot.get("planets") or {}

    jup = planets.get("jupiter") or {}
    sat = planets.get("saturn") or {}

    jup_house = jup.get("transit_house")
    sat_house = sat.get("transit_house")

    jup_influences: set[int] = _planet_influences(jup_house, "jupiter") if jup_house else set()
    sat_influences: set[int] = _planet_influences(sat_house, "saturn") if sat_house else set()

    result: dict[int, dict] = {}
    for h in range(1, 13):
        j = h in jup_influences
        s = h in sat_influences
        result[h] = {
            "jupiter": j,
            "saturn": s,
            "double": j and s,
        }
    return result
