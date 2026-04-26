"""
Tests for POST /api/charts/{id}/load endpoint.
Mocks: fetch_many (AstrologyAPI), queries.get_chart_by_id, queries.update_chart_field.
No live HTTP calls, no live Supabase writes.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user, get_db

# ---------------------------------------------------------------------------
# Dep overrides — no real Supabase client needed
# ---------------------------------------------------------------------------
FAKE_USER = {"id": "user-test-1", "email": "test@example.com", "token": "fake-jwt"}
FAKE_DB = MagicMock()  # never actually called; queries are patched at function level


def _fake_user():
    return FAKE_USER


def _fake_db():
    return FAKE_DB


app.dependency_overrides[get_current_user] = _fake_user
app.dependency_overrides[get_db] = _fake_db

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixture data — minimal planet lists that satisfy load_service expectations
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

# Raw planet list returned by AstrologyAPI — enough fields for compute_transit_houses
# and compute_annual_houses to run without error.
_ANNUAL_PLANETS = [
    {"name": "Sun", "current_sign": 3, "sign_name": "gemini", "nakshatra": "Mrigashira", "isRetro": False},
    {"name": "Moon", "current_sign": 4, "sign_name": "cancer", "nakshatra": "Punarvasu", "isRetro": False},
    {"name": "Mars", "current_sign": 1, "sign_name": "aries", "nakshatra": "Ashwini", "isRetro": False},
    {"name": "Mercury", "current_sign": 3, "sign_name": "gemini", "nakshatra": "Ardra", "isRetro": False},
    {"name": "Jupiter", "current_sign": 9, "sign_name": "sagittarius", "nakshatra": "Moola", "isRetro": False},
    {"name": "Venus", "current_sign": 5, "sign_name": "leo", "nakshatra": "Magha", "isRetro": False},
    {"name": "Saturn", "current_sign": 10, "sign_name": "capricorn", "nakshatra": "Uttara Ashadha", "isRetro": False},
    {"name": "Rahu", "current_sign": 2, "sign_name": "taurus", "nakshatra": "Rohini", "isRetro": True},
    {"name": "Ketu", "current_sign": 8, "sign_name": "scorpio", "nakshatra": "Jyeshtha", "isRetro": True},
]

_TRANSIT_PLANETS = [
    {"name": "Sun", "current_sign": 1, "sign_name": "aries", "nakshatra": "Ashwini", "isRetro": False},
    {"name": "Moon", "current_sign": 2, "sign_name": "taurus", "nakshatra": "Rohini", "isRetro": False},
    {"name": "Saturn", "current_sign": 11, "sign_name": "aquarius", "nakshatra": "Shatabhisha", "isRetro": False},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_success():
    """
    Happy path: fetch_many returns valid planet lists.
    Response must be {"loaded": True, "varshaphal_year": <current_year>, "transit_date": <today>}.
    update_chart_field must be called exactly twice — once for varshaphal_raw, once for transit_snapshot.
    """
    today = date.today()
    current_year = today.year

    with (
        patch("app.api.charts.queries.get_chart_full", return_value=MINIMAL_CHART_ROW),
        patch("app.services.load_service.fetch_many", new=AsyncMock(return_value=[_ANNUAL_PLANETS, _TRANSIT_PLANETS])),
        patch("app.services.load_service.queries.update_chart_field") as mock_update,
    ):
        response = client.post(f"/api/charts/{CHART_ID}/load")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["loaded"] is True
    assert body["varshaphal_year"] == current_year
    assert body["transit_date"] == str(today)

    # Two DB writes: varshaphal_raw and transit_snapshot
    assert mock_update.call_count == 2
    written_fields = {c.args[2] for c in mock_update.call_args_list}
    assert "varshaphal_raw" in written_fields
    assert "transit_snapshot" in written_fields


def test_load_chart_not_found():
    """
    When get_chart_by_id returns None the endpoint must 404.
    """
    with patch("app.api.charts.queries.get_chart_full", return_value=None):
        response = client.post(f"/api/charts/does-not-exist/load")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_load_api_failure():
    """
    When fetch_many returns [None, None] (both API calls failed) the endpoint must 502.
    """
    with (
        patch("app.api.charts.queries.get_chart_full", return_value=MINIMAL_CHART_ROW),
        patch("app.services.load_service.fetch_many", new=AsyncMock(return_value=[None, None])),
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

    chart_row_with_existing = {
        **MINIMAL_CHART_ROW,
        "varshaphal_raw": {str(existing_year): _ANNUAL_PLANETS},
    }

    captured: list = []

    def capture_update(db, chart_id, field, value):
        captured.append((field, value))

    with (
        patch("app.api.charts.queries.get_chart_full", return_value=chart_row_with_existing),
        patch("app.services.load_service.fetch_many", new=AsyncMock(return_value=[_ANNUAL_PLANETS, _TRANSIT_PLANETS])),
        patch("app.services.load_service.queries.update_chart_field", side_effect=capture_update),
    ):
        response = client.post(f"/api/charts/{CHART_ID}/load")

    assert response.status_code == 200
    varshaphal_write = next(v for f, v in captured if f == "varshaphal_raw")
    assert str(existing_year) in varshaphal_write, "existing year must be preserved"
    assert str(current_year) in varshaphal_write, "new year must be added"
