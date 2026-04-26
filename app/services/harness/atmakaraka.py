"""Compute Atmakaraka: the planet with highest degree in its sign, excluding Rahu/Ketu."""

EXCLUDED = {"rahu", "ketu"}


def get_atmakaraka(planets: dict) -> str | None:
    best_planet = None
    best_degree = -1.0
    for name, data in planets.items():
        if name.lower() in EXCLUDED:
            continue
        degree = data.get("current_deg") or data.get("degree") or 0
        try:
            degree = float(degree) % 30  # degree within sign
        except (TypeError, ValueError):
            continue
        if degree > best_degree:
            best_degree = degree
            best_planet = name
    return best_planet
