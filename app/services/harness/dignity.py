"""Planet dignity lookup for all 9 planets × 12 signs."""

# sign numbers: 1=Aries, 2=Taurus, ... 12=Pisces
DIGNITY = {
    "sun":     {1: "friend", 2: "enemy", 3: "neutral", 4: "enemy", 5: "own", 6: "enemy", 7: "enemy", 8: "neutral", 9: "friend", 10: "debilitated", 11: "neutral", 12: "exalted"},
    "moon":    {1: "friend", 2: "exalted", 3: "neutral", 4: "own", 5: "friend", 6: "neutral", 7: "debilitated", 8: "neutral", 9: "neutral", 10: "neutral", 11: "neutral", 12: "neutral"},
    "mars":    {1: "own", 2: "neutral", 3: "neutral", 4: "exalted", 5: "friend", 6: "enemy", 7: "neutral", 8: "own", 9: "neutral", 10: "debilitated", 11: "neutral", 12: "neutral"},
    "mercury": {1: "neutral", 2: "neutral", 3: "own", 4: "enemy", 5: "neutral", 6: "exalted", 7: "friend", 8: "neutral", 9: "enemy", 10: "neutral", 11: "neutral", 12: "debilitated"},
    "jupiter": {1: "neutral", 2: "neutral", 3: "enemy", 4: "exalted", 5: "own", 6: "enemy", 7: "neutral", 8: "neutral", 9: "own", 10: "neutral", 11: "neutral", 12: "debilitated"},
    "venus":   {1: "neutral", 2: "own", 3: "neutral", 4: "friend", 5: "neutral", 6: "own", 7: "exalted", 8: "neutral", 9: "neutral", 10: "neutral", 11: "debilitated", 12: "friend"},
    "saturn":  {1: "debilitated", 2: "neutral", 3: "neutral", 4: "neutral", 5: "enemy", 6: "neutral", 7: "exalted", 8: "neutral", 9: "neutral", 10: "own", 11: "own", 12: "neutral"},
    "rahu":    {},  # no dignity in classical system; context-dependent
    "ketu":    {},
}


def get_dignity(planet: str, sign_num: int) -> str:
    return DIGNITY.get(planet.lower(), {}).get(sign_num, "neutral")
