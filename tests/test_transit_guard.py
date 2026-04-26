"""
Tests for the transit guard logic in GET /api/charts/{id}/transits.
Verifies that 422 is returned when transit_snapshot is absent or date-mismatched,
and 200 is returned when the loaded date matches today.
"""
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user, get_db

# ---------------------------------------------------------------------------
# Dep overrides
# ---------------------------------------------------------------------------
FAKE_USER = {"id": "user-transit-1", "email": "transit@example.com", "token": "fake-jwt"}
FAKE_DB = MagicMock()


def _fake_user():
    return FAKE_USER


def _fake_db():
    return FAKE_DB


app.dependency_overrides[get_current_user] = _fake_user
app.dependency_overrides[get_db] = _fake_db

client = TestClient(app)

CHART_ID = "chart-transit-456"

# Minimal chart row shared across tests; transit_snapshot varies per test.
_BASE_CHART_ROW = {
    "id": CHART_ID,
    "user_id": "user-transit-1",
    "name": "Transit Tester",
    "dob": "1985-03-20",
    "tob": "10:00:00",
    "pob_lat": 19.076,
    "pob_lon": 72.877,
    "timezone": 5.5,
    "astro_details": {"ascendant": "cancer"},
}


# ---------------------------------------------------------------------------
# Test 1: 422 when transit_snapshot is absent (None / missing key)
# ---------------------------------------------------------------------------

def test_transits_422_when_not_loaded():
    """
    chart_row has no transit_snapshot — endpoint must return 422 with a message
    that includes 'not loaded' (case-insensitive).
    """
    chart_row = {**_BASE_CHART_ROW, "transit_snapshot": None}

    with pytest.MonkeyPatch().context() as mp:
        import app.api.predict as predict_module
        mp.setattr(predict_module.queries, "get_chart_by_id", lambda db, cid, uid: chart_row)
        response = client.get(f"/api/charts/{CHART_ID}/transits")

    assert response.status_code == 422
    assert "not loaded" in response.json()["detail"].lower()


def test_transits_422_when_snapshot_key_absent():
    """
    chart_row with no transit_snapshot key at all — still 422.
    """
    chart_row = {k: v for k, v in _BASE_CHART_ROW.items()}  # no transit_snapshot key

    with pytest.MonkeyPatch().context() as mp:
        import app.api.predict as predict_module
        mp.setattr(predict_module.queries, "get_chart_by_id", lambda db, cid, uid: chart_row)
        response = client.get(f"/api/charts/{CHART_ID}/transits")

    assert response.status_code == 422
    assert "not loaded" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 2: 422 when loaded date doesn't match requested date
# ---------------------------------------------------------------------------

def test_transits_422_when_date_mismatch():
    """
    transit_snapshot has date '2026-01-01'; request asks for ?target_date=2026-04-25.
    Endpoint must return 422 with a message mentioning 'Re-run'.
    """
    chart_row = {
        **_BASE_CHART_ROW,
        "transit_snapshot": {
            "date": "2026-01-01",
            "natal_asc_sign": 4,
            "planets": {},
        },
    }

    with pytest.MonkeyPatch().context() as mp:
        import app.api.predict as predict_module
        mp.setattr(predict_module.queries, "get_chart_by_id", lambda db, cid, uid: chart_row)
        response = client.get(
            f"/api/charts/{CHART_ID}/transits",
            params={"target_date": "2026-04-25"},
        )

    assert response.status_code == 422
    assert "Re-run" in response.json()["detail"]


def test_transits_422_detail_mentions_loaded_date_on_mismatch():
    """
    The 422 detail on date mismatch should mention the date the snapshot was loaded for,
    so the client understands what's stale.
    """
    snapshot_date = "2025-12-31"
    chart_row = {
        **_BASE_CHART_ROW,
        "transit_snapshot": {
            "date": snapshot_date,
            "natal_asc_sign": 4,
            "planets": {},
        },
    }

    with pytest.MonkeyPatch().context() as mp:
        import app.api.predict as predict_module
        mp.setattr(predict_module.queries, "get_chart_by_id", lambda db, cid, uid: chart_row)
        response = client.get(
            f"/api/charts/{CHART_ID}/transits",
            params={"target_date": "2026-04-25"},
        )

    assert response.status_code == 422
    assert snapshot_date in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test 3: 200 when snapshot date matches today (no target_date param)
# ---------------------------------------------------------------------------

def test_transits_200_when_loaded_for_today():
    """
    transit_snapshot has today's date; no target_date param → defaults to today.
    Endpoint must return 200 and the snapshot body.
    """
    today_str = str(date.today())
    snapshot = {
        "date": today_str,
        "natal_asc_sign": 4,
        "planets": {
            "sun": {"transit_sign": 1, "sign_name": "aries", "transit_house": 10, "nakshatra": "Ashwini", "retrograde": False, "dignity": "neutral"},
            "saturn": {"transit_sign": 11, "sign_name": "aquarius", "transit_house": 8, "nakshatra": "Shatabhisha", "retrograde": False, "dignity": "own"},
        },
    }
    chart_row = {**_BASE_CHART_ROW, "transit_snapshot": snapshot}

    with pytest.MonkeyPatch().context() as mp:
        import app.api.predict as predict_module
        mp.setattr(predict_module.queries, "get_chart_by_id", lambda db, cid, uid: chart_row)
        response = client.get(f"/api/charts/{CHART_ID}/transits")

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == today_str
    assert body["natal_asc_sign"] == 4
    assert "planets" in body


def test_transits_200_when_loaded_and_target_date_matches_snapshot():
    """
    transit_snapshot has a specific date; target_date param equals that date → 200.
    """
    target = "2026-04-25"
    snapshot = {
        "date": target,
        "natal_asc_sign": 4,
        "planets": {},
    }
    chart_row = {**_BASE_CHART_ROW, "transit_snapshot": snapshot}

    with pytest.MonkeyPatch().context() as mp:
        import app.api.predict as predict_module
        mp.setattr(predict_module.queries, "get_chart_by_id", lambda db, cid, uid: chart_row)
        response = client.get(
            f"/api/charts/{CHART_ID}/transits",
            params={"target_date": target},
        )

    assert response.status_code == 200
    assert response.json()["date"] == target


# ---------------------------------------------------------------------------
# Test 4: 404 when chart doesn't exist
# ---------------------------------------------------------------------------

def test_transits_404_when_chart_not_found():
    """Sanity: chart lookup failure → 404, not 422."""
    with pytest.MonkeyPatch().context() as mp:
        import app.api.predict as predict_module
        mp.setattr(predict_module.queries, "get_chart_by_id", lambda db, cid, uid: None)
        response = client.get(f"/api/charts/no-such-chart/transits")

    assert response.status_code == 404
