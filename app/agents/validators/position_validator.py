"""
Sensor: checks every planetary reference in Claude's output against stored chart JSON.
Lightweight regex-based check — catches hallucinated positions, not style violations.
"""
import re

PLANET_NAMES = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]
SIGN_NAMES = ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
              "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]

# Pattern: "Jupiter in 7th house" or "Saturn in Scorpio"
_HOUSE_PATTERN = re.compile(
    r"(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\s+in\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+house",
    re.IGNORECASE,
)
_SIGN_PATTERN = re.compile(
    r"(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\s+in\s+(aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)",
    re.IGNORECASE,
)


def validate_output(llm_output: str, chart_json: dict) -> dict:
    planets = chart_json.get("planets") or {}
    violations = []

    # Check house references
    for match in _HOUSE_PATTERN.finditer(llm_output):
        planet = match.group(1).lower()
        claimed_house = int(match.group(2))
        planet_data = planets.get(planet) or {}
        actual_house = planet_data.get("house_parashari")
        if actual_house is not None and actual_house != claimed_house:
            violations.append(
                f"Position error: '{planet.title()} in {claimed_house}th house' — "
                f"actual: house {actual_house}"
            )

    # Check sign references
    for match in _SIGN_PATTERN.finditer(llm_output):
        planet = match.group(1).lower()
        claimed_sign = match.group(2).lower()
        planet_data = planets.get(planet) or {}
        actual_sign = (planet_data.get("sign_name") or planet_data.get("sign") or "").lower()
        if actual_sign and actual_sign != claimed_sign:
            violations.append(
                f"Sign error: '{planet.title()} in {claimed_sign.title()}' — "
                f"actual: {actual_sign.title()}"
            )

    return {"passed": len(violations) == 0, "violations": violations}
