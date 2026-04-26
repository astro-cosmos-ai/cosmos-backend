"""Divisional chart computation: D1 (Rashi), D9 (Navamsha), Moon chart (Chandra Lagna)."""
from .ephemeris import SIGNS, whole_sign_house


def _norm_sign(lon: float) -> int:
    """Sign number 1-12 from ecliptic longitude."""
    return int(((lon % 360) + 360) % 360 / 30) + 1


def _navamsha_sign(lon: float) -> int:
    """
    Navamsha sign (D9): divide zodiac into 108 equal parts of 3°20'.
    Each part maps to one of 12 signs cyclically starting from Aries.
    """
    norm = ((lon % 360) + 360) % 360
    part = int(norm / (360 / 108))   # 0..107
    return (part % 12) + 1           # 1..12


def _build_chart(
    planet_sign_map: dict[str, int],  # {planet_name: sign_num}
    asc_sign: int,
) -> list[dict]:
    """Build a 12-house chart list matching the assembler D1 structure."""
    house_planets: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    for planet_name, planet_sign in planet_sign_map.items():
        house = whole_sign_house(planet_sign, asc_sign)
        house_planets[house].append(planet_name.upper())

    chart = []
    for h in range(1, 13):
        sign_num = ((asc_sign - 1 + h - 1) % 12) + 1
        chart.append({
            "sign": sign_num,
            "sign_name": SIGNS[sign_num - 1],
            "planet": house_planets[h],
        })
    return chart


def build_d1(planets: dict[str, dict], asc_sign: int) -> list[dict]:
    """D1 Rashi chart."""
    sign_map = {
        name: p["current_sign"]
        for name, p in planets.items()
        if name not in ("ascendant",)
    }
    return _build_chart(sign_map, asc_sign)


def build_d9(planets: dict[str, dict], asc_lon: float) -> list[dict]:
    """D9 Navamsha chart. Ascendant navamsha sign derived from ascendant longitude."""
    asc_nav_sign = _navamsha_sign(asc_lon)
    sign_map = {
        name: _navamsha_sign(p["fullDegree"])
        for name, p in planets.items()
        if name not in ("ascendant",)
    }
    return _build_chart(sign_map, asc_nav_sign)


def build_moon_chart(planets: dict[str, dict]) -> list[dict]:
    """
    Chandra Lagna chart: Moon's sign becomes house 1.
    Planet positions (D1 signs) stay the same; houses are counted from Moon.
    """
    moon_sign = planets["moon"]["current_sign"]
    sign_map = {
        name: p["current_sign"]
        for name, p in planets.items()
        if name not in ("ascendant",)
    }
    return _build_chart(sign_map, moon_sign)
