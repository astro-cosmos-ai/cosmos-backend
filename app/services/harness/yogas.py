"""Yoga detection: Raj Yoga, Dhana Yoga, Pancha Mahapurusha, Gaja Kesari, and more."""
from .dignity import get_dignity, DIGNITY

KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
TRIK_HOUSES = {6, 8, 12}

# Pancha Mahapurusha: planet → (own signs, exaltation sign, yoga name)
_PANCHA_MAHAPURUSHA = {
    "mars":    ([1, 8], 10, "Ruchaka Yoga"),
    "mercury": ([3, 6], 6,  "Bhadra Yoga"),
    "jupiter": ([9, 12], 4, "Hamsa Yoga"),
    "venus":   ([2, 7], 12, "Malavya Yoga"),
    "saturn":  ([10, 11], 7, "Sasa Yoga"),
}


def _house_relative(base_house: int, target_house: int) -> int:
    """Returns the house number of target relative to base (1-indexed)."""
    return ((target_house - base_house) % 12) + 1


def detect_pancha_mahapurusha(planets: dict) -> list[dict]:
    """Pancha Mahapurusha: specific planet in own/exaltation sign AND in kendra from lagna."""
    yogas = []
    for planet, (own_signs, exalt_sign, yoga_name) in _PANCHA_MAHAPURUSHA.items():
        p = planets.get(planet) or {}
        sign = p.get("current_sign")
        house = p.get("house_parashari")
        if sign and house and house in KENDRA_HOUSES:
            if sign in own_signs or sign == exalt_sign:
                yogas.append({"name": yoga_name, "planets": [planet], "type": "pancha_mahapurusha"})
    return yogas


def detect_gaja_kesari(planets: dict) -> list[dict]:
    """Gaja Kesari: Jupiter in kendra from Moon's house."""
    yogas = []
    moon = planets.get("moon") or {}
    jupiter = planets.get("jupiter") or {}
    moon_house = moon.get("house_parashari")
    jup_house = jupiter.get("house_parashari")
    if moon_house and jup_house:
        rel = _house_relative(moon_house, jup_house)
        if rel in KENDRA_HOUSES:
            yogas.append({"name": "Gaja Kesari Yoga", "planets": ["moon", "jupiter"], "type": "aspect"})
    return yogas


def detect_chandra_mangala(planets: dict) -> list[dict]:
    """Chandra Mangala: Moon and Mars in same house."""
    yogas = []
    moon_house = (planets.get("moon") or {}).get("house_parashari")
    mars_house = (planets.get("mars") or {}).get("house_parashari")
    if moon_house and mars_house and moon_house == mars_house:
        yogas.append({"name": "Chandra Mangala Yoga", "planets": ["moon", "mars"], "type": "conjunction"})
    return yogas


def detect_neecha_bhanga(planets: dict, significators: dict) -> list[dict]:
    """Neecha Bhanga: debilitated planet with its sign lord in a kendra from lagna."""
    yogas = []
    for planet_name, p_data in planets.items():
        sign = p_data.get("current_sign")
        if not sign:
            continue
        dignity = get_dignity(planet_name, sign)
        if dignity != "debilitated":
            continue
        # Find lord of the sign where planet is debilitated
        sign_lord = significators.get(str(_sign_to_house_approx(sign)), {}).get("lord")
        if not sign_lord:
            continue
        lord_house = (planets.get(sign_lord) or {}).get("house_parashari")
        if lord_house and lord_house in KENDRA_HOUSES:
            yogas.append({
                "name": f"Neecha Bhanga Raja Yoga ({planet_name.title()})",
                "planets": [planet_name, sign_lord],
                "type": "cancellation",
            })
    return yogas


def detect_viparita_raja(significators: dict, planets: dict) -> list[dict]:
    """Viparita Raja: lords of 6/8/12 in each other's houses or jointly in 6/8/12."""
    yogas = []
    trik_lords = []
    for h in [6, 8, 12]:
        lord = significators.get(str(h), {}).get("lord")
        if lord:
            trik_lords.append((h, lord))

    for i, (ha, la) in enumerate(trik_lords):
        for hb, lb in trik_lords[i + 1:]:
            if la == lb:
                continue
            pos_a = (planets.get(la) or {}).get("house_parashari")
            pos_b = (planets.get(lb) or {}).get("house_parashari")
            # Both in trik houses
            if pos_a and pos_b and pos_a in TRIK_HOUSES and pos_b in TRIK_HOUSES:
                yogas.append({
                    "name": f"Viparita Raja Yoga ({ha}/{hb})",
                    "planets": [la, lb],
                    "type": "viparita",
                })
            # Mutual exchange between 6/8/12
            elif pos_a == hb and pos_b == ha:
                yogas.append({
                    "name": f"Viparita Raja Yoga (exchange {ha}/{hb})",
                    "planets": [la, lb],
                    "type": "exchange",
                })
    return yogas


def detect_kemadruma(planets: dict) -> list[dict]:
    """Kemadruma: Moon with no planets in the 2nd or 12th house from Moon (negative yoga)."""
    yogas = []
    moon_house = (planets.get("moon") or {}).get("house_parashari")
    if not moon_house:
        return yogas
    second_from_moon = (moon_house % 12) + 1
    twelfth_from_moon = ((moon_house - 2) % 12) + 1
    occupied = {p.get("house_parashari") for n, p in planets.items() if n not in ("moon", "rahu", "ketu") and p.get("house_parashari")}
    if second_from_moon not in occupied and twelfth_from_moon not in occupied:
        yogas.append({"name": "Kemadruma Yoga", "planets": ["moon"], "type": "negative"})
    return yogas


def detect_daridra(significators: dict, planets: dict) -> list[dict]:
    """Daridra: lords of 2nd and 11th placed in 6/8/12 (negative yoga, wealth obstruction)."""
    yogas = []
    lord_2 = significators.get("2", {}).get("lord")
    lord_11 = significators.get("11", {}).get("lord")
    for lord, label in [(lord_2, "2nd"), (lord_11, "11th")]:
        if not lord:
            continue
        house = (planets.get(lord) or {}).get("house_parashari")
        if house and house in TRIK_HOUSES:
            yogas.append({
                "name": f"Daridra Yoga ({label} lord in {house}th)",
                "planets": [lord],
                "type": "negative",
            })
    return yogas


def _sign_to_house_approx(sign: int) -> int:
    """Approximate: use sign number as house number for sign lord lookup."""
    return sign


def detect_yogas(significators: dict, planets: dict) -> list[dict]:
    yogas = []

    # Dhana Yoga
    lord_2 = significators.get("2", {}).get("lord")
    lord_11 = significators.get("11", {}).get("lord")
    if lord_2 and lord_11 and lord_2 != lord_11:
        house_2_lord = planets.get(lord_2, {}).get("house_parashari")
        house_11_lord = planets.get(lord_11, {}).get("house_parashari")
        if house_2_lord == house_11_lord:
            yogas.append({"name": "Dhana Yoga", "planets": [lord_2, lord_11], "type": "conjunction"})
        elif house_2_lord and house_11_lord:
            if house_2_lord == 11 and house_11_lord == 2:
                yogas.append({"name": "Dhana Yoga (Parivartana)", "planets": [lord_2, lord_11], "type": "exchange"})

    # Raj Yoga
    for house_a, data_a in significators.items():
        for house_b, data_b in significators.items():
            ha, hb = int(house_a), int(house_b)
            if ha >= hb:
                continue
            if ha in KENDRA_HOUSES and hb in TRIKONA_HOUSES or ha in TRIKONA_HOUSES and hb in KENDRA_HOUSES:
                la, lb = data_a.get("lord"), data_b.get("lord")
                if la and lb and la != lb:
                    pos_a = planets.get(la, {}).get("house_parashari")
                    pos_b = planets.get(lb, {}).get("house_parashari")
                    if pos_a and pos_b and pos_a == pos_b and pos_a not in TRIK_HOUSES:
                        yogas.append({
                            "name": f"Raj Yoga ({ha}/{hb})",
                            "planets": [la, lb],
                            "type": "conjunction",
                        })

    yogas += detect_pancha_mahapurusha(planets)
    yogas += detect_gaja_kesari(planets)
    yogas += detect_chandra_mangala(planets)
    yogas += detect_neecha_bhanga(planets, significators)
    yogas += detect_viparita_raja(significators, planets)
    yogas += detect_kemadruma(planets)
    yogas += detect_daridra(significators, planets)

    return yogas
