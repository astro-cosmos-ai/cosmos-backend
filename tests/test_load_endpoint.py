"""
Tests for POST /api/charts/{id}/load endpoint.
Mocks: compute_chart (Swiss Ephemeris), queries.get_chart_full, queries.update_chart_field.
No live ephemeris calls, no live Supabase writes.
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user, get_db

# ---------------------------------------------------------------------------
# Dep overrides — no real Supabase client needed
# ---------------------------------------------------------------------------
FAKE_USER = {"id": "user-test-1", "email": "test@example.com", "token": "fake-jwt"}
FAKE_DB = MagicMock()


def _fake_user():
    return FAKE_USER


def _fake_db():
    return FAKE_DB


app.dependency_overrides[get_current_user] = _fake_user
app.dependency_overrides[get_db] = _fake_db

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixture data — minimal Swiss-shaped chart dicts
# ---------------------------------------------------------------------------
CHART_ID = "chart-abc-123"

MINIMAL_CHART_ROW = {
    "id": CHART_ID,
    "user_id": "user-test-1",
    "name": "Test Person",
    "dob": "1990-06-15",
    "tob": "08:30:00",
    "pob_lat": 28.6139,
    "pob_lon": 77.2090,
    "timezone": 5.5,
    "astro_details": {"ascendant": "aries"},
    "varshaphal_raw": None,
    "transit_snapshot": None,
}

# Swiss compute_chart returns {"planets": {planet_name: {...}}, ...}
_ANNUAL_CHART = {
    "planets": {
        "sun":     {"name": "Sun",     "current_sign": 3,  "sign": "Gemini",      "nakshatra": "Mrigashira",    "isRetro": "false"},
        "moon":    {"name": "Moon",    "current_sign": 4,  "sign": "Cancer",      "nakshatra": "Punarvasu",     "isRetro": "false"},
        "mars":    {"name": "Mars",    "current_sign": 1,  "sign": "Aries",       "nakshatra": "Ashwini",       "isRetro": "false"},
        "mercury": {"name": "Mercury", "current_sign": 3,  "sign": "Gemini",      "nakshatra": "Ardra",         "isRetro": "false"},
        "jupiter": {"name": "Jupiter", "current_sign": 9,  "sign": "Sagittarius", "nakshatra": "Mula",          "isRetro": "false"},
        "venus":   {"name": "Venus",   "current_sign": 5,  "sign": "Leo",         "nakshatra": "Magha",         "isRetro": "false"},
        "saturn":  {"name": "Saturn",  "current_sign": 10, "sign": "Capricorn",   "nakshatra": "Uttara Ashadha","isRetro": "false"},
        "rahu":    {"name": "Rahu",    "current_sign": 2,  "sign": "Taurus",      "nakshatra": "Rohini",        "isRetro": "true"},
        "ketu":    {"name": "Ketu",    "current_sign": 8,  "sign": "Scorpio",     "nakshatra": "Jyeshtha",      "isRetro": "true"},
    }
}

_TRANSIT_CHART = {
    "planets": {
        "sun":    {"name": "Sun",    "current_sign": 1,  "sign": "Aries",    "nakshatra": "Ashwini",     "isRetro": "false"},
        "moon":   {"name": "Moon",   "current_sign": 2,  "sign": "Taurus",   "nakshatra": "Rohini",      "isRetro": "false"},
        "saturn": {"name": "Saturn", "current_sign": 11, "sign": "Aquarius", "nakshatra": "Shatabhisha", "isRetro": "false"},
    }
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_success():
    """
    Happy path: compute_chart returns valid chart dicts for both annual and transit calls.
    Response must be {"loaded": True, "varshaphal_year": <current_year>, "transit_date": <today>}.
    update_chart_field must be called exactly twice.
    """
    today = date.today()
    current_year = today.year

    with (
        patch("app.api.charts.queries.get_chart_full", return_value=MINIMAL_CHART_ROW),
        patch("app.services.load_service.compute_chart", side_effect=[_ANNUAL_CHART, _TRANSIT_CHART]),
        patch("app.services.load_service.queries.update_chart_field") as mock_update,
    ):
        response = client.post(f"/api/charts/{CHART_ID}/load")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["loaded"] is True
    assert body["varshaphal_year"] == current_year
    assert body["transit_date"] == str(today)

    assert mock_update.call_count == 2
    written_fields = {c.args[2] for c in mock_update.call_args_list}
    assert "varshaphal_raw" in written_fields
    assert "transit_snapshot" in written_fields


def test_load_chart_not_found():
    """When get_chart_full returns None the endpoint must 404."""
    with patch("app.api.charts.queries.get_chart_full", return_value=None):
        response = client.post(f"/api/charts/does-not-exist/load")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_load_api_failure():
    """When compute_chart raises an exception the endpoint must 502."""
    with (
        patch("app.api.charts.queries.get_chart_full", return_value=MINIMAL_CHART_ROW),
        patch("app.services.load_service.compute_chart", side_effect=RuntimeError("ephemeris error")),
    ):
        response = client.post(f"/api/charts/{CHART_ID}/load")

    assert response.status_code == 502


def test_load_varshaphal_raw_merged_with_existing():
    """
    If chart_row already has varshaphal_raw for a prior year, the new year is merged in,
    not overwritten. Verifies that the update_chart_field call for varshaphal_raw
    includes both the existing year and the new year.
    """
    today = date.today()
    current_year = today.year
    existing_year = current_year - 1

    prior_planets = list(_ANNUAL_CHART["planets"].values())
    chart_row_with_existing = {
        **MINIMAL_CHART_ROW,
        "varshaphal_raw": {str(existing_year): prior_planets},
    }

    captured: list = []

    def capture_update(db, chart_id, field, value):
        captured.append((field, value))

    with (
        patch("app.api.charts.queries.get_chart_full", return_value=chart_row_with_existing),
        patch("app.services.load_service.compute_chart", side_effect=[_ANNUAL_CHART, _TRANSIT_CHART]),
        patch("app.services.load_service.queries.update_chart_field", side_effect=capture_update),
    ):
        response = client.post(f"/api/charts/{CHART_ID}/load")

    assert response.status_code == 200
    varshaphal_write = next(v for f, v in captured if f == "varshaphal_raw")
    assert str(existing_year) in varshaphal_write, "existing year must be preserved"
    assert str(current_year) in varshaphal_write, "new year must be added"
