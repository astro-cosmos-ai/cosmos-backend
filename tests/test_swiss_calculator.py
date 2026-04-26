"""Tests for Swiss Ephemeris calculator — known birth chart assertions."""
import os
os.environ.setdefault("SUPABASE_URL", "x")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "x")
os.environ.setdefault("SUPABASE_ANON_KEY", "x")
os.environ.setdefault("ANTHROPIC_API_KEY", "x")

import pytest
from app.services.swiss.calculator import compute_chart

# Known birth: Delhi, India — Jan 15 1990 08:30 IST
# Verified against independent Jyotish software with Lahiri ayanamsa, whole-sign
_DELHI_1990 = {
    "day": 15, "month": 1, "year": 1990,
    "hour": 8, "min": 30,
    "lat": 28.6139, "lon": 77.2090, "tzone": 5.5,
}


@pytest.fixture(scope="module")
def delhi_chart():
    return compute_chart(_DELHI_1990)


class TestPlanetPositions:
    def test_ascendant_sign(self, delhi_chart):
        assert delhi_chart["astro_details"]["ascendant"] == "Capricorn"

    def test_sun_sign(self, delhi_chart):
        assert delhi_chart["planets"]["sun"]["sign"] == "Capricorn"

    def test_sun_house(self, delhi_chart):
        assert delhi_chart["planets"]["sun"]["house_parashari"] == 1

    def test_moon_sign(self, delhi_chart):
        assert delhi_chart["planets"]["moon"]["sign"] == "Leo"

    def test_moon_house(self, delhi_chart):
        assert delhi_chart["planets"]["moon"]["house_parashari"] == 8

    def test_moon_nakshatra(self, delhi_chart):
        assert delhi_chart["planets"]["moon"]["nakshatra"] == "Purva Phalguni"

    def test_mars_sign(self, delhi_chart):
        assert delhi_chart["planets"]["mars"]["sign"] == "Scorpio"

    def test_rahu_sign(self, delhi_chart):
        assert delhi_chart["planets"]["rahu"]["sign"] == "Capricorn"

    def test_ketu_sign(self, delhi_chart):
        # Ketu always opposite Rahu
        rahu_sign = delhi_chart["planets"]["rahu"]["current_sign"]
        ketu_sign = delhi_chart["planets"]["ketu"]["current_sign"]
        assert (rahu_sign - 1 + 6) % 12 == (ketu_sign - 1)

    def test_all_nine_planets_present(self, delhi_chart):
        expected = {"sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"}
        assert expected.issubset(delhi_chart["planets"].keys())

    def test_planet_has_required_keys(self, delhi_chart):
        for name, p in delhi_chart["planets"].items():
            assert "current_sign" in p, f"{name} missing current_sign"
            assert "house_parashari" in p, f"{name} missing house_parashari"
            assert "nakshatra" in p, f"{name} missing nakshatra"
            assert "isRetro" in p, f"{name} missing isRetro"
            assert p["current_sign"] in range(1, 13), f"{name} sign out of range"
            assert p["house_parashari"] in range(1, 13), f"{name} house out of range"


class TestAstroDetails:
    def test_ascendant_present(self, delhi_chart):
        assert delhi_chart["astro_details"]["ascendant"] == "Capricorn"

    def test_moon_nakshatra_key(self, delhi_chart):
        # harness reads both "Naksahtra" (legacy) and "nakshatra"
        assert delhi_chart["astro_details"]["Naksahtra"] == "Purva Phalguni"
        assert delhi_chart["astro_details"]["nakshatra"] == "Purva Phalguni"

    def test_tithi_in_range(self, delhi_chart):
        t = delhi_chart["panchang"]["tithi"]
        assert 1 <= t <= 30

    def test_yoga_in_range(self, delhi_chart):
        y = delhi_chart["panchang"]["yoga"]
        assert 1 <= y <= 27

    def test_vaara_is_weekday(self, delhi_chart):
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        assert delhi_chart["panchang"]["vaara"] in weekdays


class TestDasha:
    def test_current_dasha_has_major(self, delhi_chart):
        cd = delhi_chart["current_dasha"]
        assert cd["major"]["planet"] != ""

    def test_mahadashas_count(self, delhi_chart):
        assert len(delhi_chart["dashas"]["vimshottari"]) == 9

    def test_mahadasha_structure(self, delhi_chart):
        for d in delhi_chart["dashas"]["vimshottari"]:
            assert "planet" in d
            assert "start" in d
            assert "end" in d


class TestAshtakavarga:
    def test_seven_planets_present(self, delhi_chart):
        for p in ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]:
            assert p in delhi_chart["ashtakavarga"]

    def test_sarvashtaka_present(self, delhi_chart):
        assert "sarvashtaka" in delhi_chart["ashtakavarga"]

    def test_sarvashtaka_total(self, delhi_chart):
        sarva = delhi_chart["ashtakavarga"]["sarvashtaka"]
        total = sum(sarva.values())
        # Classical total for sarvashtaka is always 337 bindus
        assert total == 337, f"Sarvashtaka total {total} != 337"


class TestDivisionalCharts:
    def test_d1_has_12_houses(self, delhi_chart):
        assert len(delhi_chart["divisional_charts"]["D1"]) == 12

    def test_d9_has_12_houses(self, delhi_chart):
        assert len(delhi_chart["divisional_charts"]["D9"]) == 12

    def test_moon_chart_has_12_houses(self, delhi_chart):
        assert len(delhi_chart["divisional_charts"]["Moon"]) == 12

    def test_d1_house1_sign_matches_ascendant(self, delhi_chart):
        d1_h1 = delhi_chart["divisional_charts"]["D1"][0]["sign_name"]
        asc = delhi_chart["astro_details"]["ascendant"]
        assert d1_h1 == asc

    def test_moon_chart_house1_is_moon_sign(self, delhi_chart):
        moon_sign = delhi_chart["planets"]["moon"]["sign"]
        moon_chart_h1 = delhi_chart["divisional_charts"]["Moon"][0]["sign_name"]
        assert moon_chart_h1 == moon_sign


class TestOutputContract:
    def test_all_required_keys(self, delhi_chart):
        required = [
            "birth_details", "astro_details", "planets", "divisional_charts",
            "kp_planets", "kp_cusps", "kp_house_significators", "kp_planet_significators",
            "dashas", "current_dasha", "ashtakavarga", "doshas", "panchang",
        ]
        for k in required:
            assert k in delhi_chart, f"Missing key: {k}"

    def test_doshas_keys(self, delhi_chart):
        for k in ["manglik", "kalsarpa", "pitra", "sadhesati"]:
            assert k in delhi_chart["doshas"]

    def test_kp_planets_list(self, delhi_chart):
        assert isinstance(delhi_chart["kp_planets"], list)
        assert len(delhi_chart["kp_planets"]) == 9  # 9 planets (no ascendant)
