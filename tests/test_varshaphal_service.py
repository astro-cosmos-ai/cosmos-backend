"""
Pure unit tests for app/services/varshaphal_service.py.
No HTTP calls, no DB, no mocks — feeds real chart_row shaped dicts.
"""
import pytest
from app.services.varshaphal_service import get_varshaphal

# ---------------------------------------------------------------------------
# Minimal planet list fixture — must satisfy compute_annual_houses:
#   required fields per planet: name, current_sign, sign_name, nakshatra, isRetro
# ---------------------------------------------------------------------------
_MINIMAL_PLANETS = [
    {"name": "Sun", "current_sign": 5, "sign_name": "leo", "nakshatra": "Magha", "isRetro": False},
    {"name": "Moon", "current_sign": 4, "sign_name": "cancer", "nakshatra": "Punarvasu", "isRetro": False},
    {"name": "Mars", "current_sign": 1, "sign_name": "aries", "nakshatra": "Ashwini", "isRetro": False},
    {"name": "Mercury", "current_sign": 3, "sign_name": "gemini", "nakshatra": "Ardra", "isRetro": False},
    {"name": "Jupiter", "current_sign": 9, "sign_name": "sagittarius", "nakshatra": "Moola", "isRetro": False},
    {"name": "Venus", "current_sign": 2, "sign_name": "taurus", "nakshatra": "Rohini", "isRetro": False},
    {"name": "Saturn", "current_sign": 10, "sign_name": "capricorn", "nakshatra": "Uttara Ashadha", "isRetro": False},
    {"name": "Rahu", "current_sign": 11, "sign_name": "aquarius", "nakshatra": "Shatabhisha", "isRetro": True},
    {"name": "Ketu", "current_sign": 5, "sign_name": "leo", "nakshatra": "Purva Phalguni", "isRetro": True},
]

_YEAR = 2025

# chart_row with varshaphal_raw loaded for _YEAR
_LOADED_CHART_ROW = {
    "id": "chart-unit-1",
    "dob": "1990-06-15",
    "astro_details": {"ascendant": "aries"},
    "varshaphal_raw": {str(_YEAR): _MINIMAL_PLANETS},
}

# chart_row with varshaphal_raw missing entirely
_EMPTY_CHART_ROW_NO_KEY = {
    "id": "chart-unit-2",
    "dob": "1990-06-15",
    "astro_details": {"ascendant": "aries"},
}

# chart_row with varshaphal_raw present but empty dict
_EMPTY_CHART_ROW_EMPTY_DICT = {
    "id": "chart-unit-3",
    "dob": "1990-06-15",
    "astro_details": {"ascendant": "aries"},
    "varshaphal_raw": {},
}

# chart_row with varshaphal_raw for a different year only
_CHART_ROW_WRONG_YEAR = {
    "id": "chart-unit-4",
    "dob": "1990-06-15",
    "astro_details": {"ascendant": "aries"},
    "varshaphal_raw": {"2024": _MINIMAL_PLANETS},
}


# ---------------------------------------------------------------------------
# Tests: None-return cases
# ---------------------------------------------------------------------------

def test_get_varshaphal_returns_none_when_key_missing():
    """chart_row with no varshaphal_raw key must return None."""
    result = get_varshaphal(_EMPTY_CHART_ROW_NO_KEY, _YEAR)
    assert result is None


def test_get_varshaphal_returns_none_when_dict_empty():
    """chart_row with varshaphal_raw = {} must return None."""
    result = get_varshaphal(_EMPTY_CHART_ROW_EMPTY_DICT, _YEAR)
    assert result is None


def test_get_varshaphal_returns_none_when_year_not_loaded():
    """chart_row that has data for 2024 but request is for 2025 must return None."""
    result = get_varshaphal(_CHART_ROW_WRONG_YEAR, _YEAR)
    assert result is None


# ---------------------------------------------------------------------------
# Tests: happy-path structure and correctness
# ---------------------------------------------------------------------------

def test_get_varshaphal_returns_dict_when_loaded():
    """Must return a dict (not None) when varshaphal_raw is loaded for the year."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    assert result is not None
    assert isinstance(result, dict)


def test_get_varshaphal_has_required_top_level_keys():
    """Result must have the documented shape: year, age, natal_ascendant, planets, year_lord, significators."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    for key in ("year", "age", "natal_ascendant", "planets", "year_lord", "significators"):
        assert key in result, f"Missing key: {key}"


def test_get_varshaphal_year_matches_requested():
    """result['year'] must equal the year passed in."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    assert result["year"] == _YEAR


def test_get_varshaphal_natal_ascendant_matches_chart():
    """natal_ascendant must reflect astro_details.ascendant."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    assert result["natal_ascendant"].lower() == "aries"


def test_get_varshaphal_age_computed_correctly():
    """age must be year − dob.year (1990 → 2025 = 35)."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    assert result["age"] == 35


def test_get_varshaphal_planets_is_dict_with_entries():
    """planets must be a non-empty dict keyed by lowercase planet name."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    planets = result["planets"]
    assert isinstance(planets, dict)
    assert len(planets) > 0
    # Keys should be lowercase
    for k in planets:
        assert k == k.lower(), f"Planet key not lowercase: {k}"


def test_get_varshaphal_each_planet_has_house_sign_dignity():
    """Every planet entry must have house, sign, sign_name, nakshatra, retrograde, dignity."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    for name, data in result["planets"].items():
        for field in ("house", "sign", "sign_name", "nakshatra", "retrograde", "dignity"):
            assert field in data, f"Planet '{name}' missing field '{field}'"


def test_get_varshaphal_sun_in_leo_yields_year_lord_sun():
    """Sun in Leo (sign 5) → sign lord is Sun → year_lord should be 'sun'."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    # Sun is in sign 5 (leo) in _MINIMAL_PLANETS; the _SIGN_LORD maps 5 → 'sun'
    assert result["year_lord"] == "sun"


def test_get_varshaphal_significators_is_dict():
    """significators must be a dict (output of compute_all_significators)."""
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    assert isinstance(result["significators"], dict)


def test_get_varshaphal_planet_houses_use_whole_sign_from_aries_asc():
    """
    With Aries ascendant (sign 1), a planet in sign 1 must be in house 1,
    a planet in sign 5 (Leo) must be in house 5.
    Whole-sign formula: ((planet_sign - asc_sign) % 12) + 1
    """
    result = get_varshaphal(_LOADED_CHART_ROW, _YEAR)
    planets = result["planets"]
    # Mars is in sign 1 (aries), Aries asc → house 1
    assert planets["mars"]["house"] == 1
    # Sun is in sign 5 (leo), Aries asc → house 5
    assert planets["sun"]["house"] == 5
