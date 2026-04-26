"""Vedic aspect computation: 7th for all planets; special aspects for Mars, Jupiter, Saturn."""

SPECIAL_ASPECTS: dict[str, list[int]] = {
    "mars":    [4, 7, 8],
    "jupiter": [5, 7, 9],
    "saturn":  [3, 7, 10],
    "rahu":    [5, 7, 9],
    "ketu":    [5, 7, 9],
}
DEFAULT_ASPECTS = [7]


def houses_aspected_by(planet_house: int, planet_name: str) -> list[int]:
    offsets = SPECIAL_ASPECTS.get(planet_name.lower(), DEFAULT_ASPECTS)
    return [((planet_house + offset - 2) % 12) + 1 for offset in offsets]


def planets_aspecting_house(house: int, planets: dict) -> list[str]:
    """
    planets: {planet_name: {house_parashari: int, ...}}
    Returns list of planet names that aspect the given house.
    """
    aspecting = []
    for name, data in planets.items():
        ph = data.get("house_parashari")
        if ph is None:
            continue
        if house in houses_aspected_by(ph, name):
            aspecting.append(name)
    return aspecting
