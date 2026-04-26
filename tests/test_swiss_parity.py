"""
Parity tests between AstrologyAPI (assembler) and Swiss Ephemeris (calculator).

Both engines receive the same birth input and must agree on all categorical
astrological values: ascendant sign, planet signs, nakshatras, houses,
retrogradation, current major dasha lord, and sarvashtaka totals.

Degrees are intentionally NOT compared — sign-level and nakshatra-level
agreement is the contract.

Skipped automatically when ASTROLOGY_API_KEY is absent (safe for CI).
"""
import os
from dotenv import load_dotenv

# Load .env first so ASTROLOGY_API_KEY is available for the skip check
load_dotenv()

os.environ.setdefault("SUPABASE_URL", "x")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "x")
os.environ.setdefault("SUPABASE_ANON_KEY", "x")
os.environ.setdefault("ANTHROPIC_API_KEY", "x")

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("ASTROLOGY_API_KEY"),
    reason="ASTROLOGY_API_KEY not set — skipping parity test",
)

# ---------------------------------------------------------------------------
# Birth inputs
# ---------------------------------------------------------------------------

_DELHI = {
    "day": 15, "month": 1, "year": 1990,
    "hour": 8, "min": 30,
    "lat": 28.6139, "lon": 77.2090, "tzone": 5.5,
}

_MUMBAI = {
    "day": 10, "month": 6, "year": 1985,
    "hour": 14, "min": 0,
    "lat": 19.0760, "lon": 72.8777, "tzone": 5.5,
}

_NEW_YORK = {
    "day": 22, "month": 3, "year": 1995,
    "hour": 6, "min": 45,
    "lat": 40.7128, "lon": -74.0060, "tzone": -5.0,
}

_PLANETS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]

# AstrologyAPI uses non-standard nakshatra spellings in some cases.
# Map each known variant to the canonical name that Swiss outputs.
_NAK_ALIASES: dict[str, str] = {
    # Ashadha pair
    "uttra shadha":        "Uttara Ashadha",
    "uttara shadha":       "Uttara Ashadha",
    "uttarashadha":        "Uttara Ashadha",
    "purva shadha":        "Purva Ashadha",
    "poorva shadha":       "Purva Ashadha",
    "purvashadha":         "Purva Ashadha",
    # Phalguni pair
    "uttra phalguni":      "Uttara Phalguni",
    "uttara phalguni":     "Uttara Phalguni",
    "purva phalguni":      "Purva Phalguni",
    "poorva phalguni":     "Purva Phalguni",
    # Bhadrapada pair
    "uttra bhadra":        "Uttara Bhadrapada",
    "uttara bhadra":       "Uttara Bhadrapada",
    "uttra bhadrapada":    "Uttara Bhadrapada",
    "uttra bhadrapad":     "Uttara Bhadrapada",
    "uttara bhadrapad":    "Uttara Bhadrapada",
    "purva bhadra":        "Purva Bhadrapada",
    "poorva bhadra":       "Purva Bhadrapada",
    "purva bhadrapada":    "Purva Bhadrapada",
    "purva bhadrapad":     "Purva Bhadrapada",
    # Other common variants
    "bharni":              "Bharani",
    "mrigasira":           "Mrigashira",
    "mrigasirsha":         "Mrigashira",
    "mrigshira":           "Mrigashira",
    "moola":               "Mula",
    "jyesta":              "Jyeshtha",
    "jyestha":             "Jyeshtha",
    "dhanishtha":          "Dhanishta",
    "shravan":             "Shravana",
    "shravana":            "Shravana",
    "aslesha":             "Ashlesha",
    "shatbhisha":          "Shatabhisha",
    "shatabhisha":         "Shatabhisha",
    "shatabhisaj":         "Shatabhisha",
}


def _norm_nak(name: str | None) -> str | None:
    """Normalise a nakshatra name to canonical (Swiss) spelling."""
    if name is None:
        return None
    return _NAK_ALIASES.get(name.lower().strip(), name)


def _extract_sarvashtaka(sarva: object) -> dict[str, int]:
    """Extract {sign_lower: total_bindus} from either engine's sarvashtaka shape.

    Swiss emits a flat dict:  {sign: int, ...}
    AstrologyAPI emits:       {"ashtak_points": {sign: {"total": int, ...}}}
    """
    if not isinstance(sarva, dict):
        return {}
    if "ashtak_points" in sarva:
        pts = sarva["ashtak_points"]
        result: dict[str, int] = {}
        for sign, val in pts.items():
            if isinstance(val, dict):
                if "total" in val:
                    result[sign.lower()] = int(val["total"])
                else:
                    result[sign.lower()] = sum(
                        int(v) for v in val.values() if isinstance(v, (int, float))
                    )
            elif isinstance(val, (int, float)):
                result[sign.lower()] = int(val)
        return result
    return {k.lower(): int(v) for k, v in sarva.items() if isinstance(v, (int, float))}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_api_chart(birth_input: dict) -> dict:
    """Call AstrologyAPI assembler with chart_engine forced to 'astrology_api'."""
    # Temporarily override chart_engine so assemble_chart does NOT delegate
    # to the Swiss path — we want the real HTTP call.
    from app.core.config import settings
    from app.services.astrology_api import assembler as _assembler

    original_engine = settings.chart_engine
    object.__setattr__(settings, "chart_engine", "astrology_api")
    try:
        return await _assembler.assemble_chart(birth_input)
    finally:
        object.__setattr__(settings, "chart_engine", original_engine)


def _get_swiss_chart(birth_input: dict) -> dict:
    from app.services.swiss.calculator import compute_chart
    return compute_chart(birth_input)


def _assert_parity(api: dict, swiss: dict, label: str) -> None:
    """Assert all required fields agree between the two engines for one chart."""

    # --- Ascendant sign name ---
    api_asc = api["astro_details"]["ascendant"]
    sw_asc = swiss["astro_details"]["ascendant"]
    assert api_asc == sw_asc, (
        f"[{label}] ascendant mismatch: API={api_asc!r}  Swiss={sw_asc!r}"
    )

    # --- Per-planet fields ---
    api_planets = api["planets"]
    sw_planets = swiss["planets"]

    for planet in _PLANETS:
        api_p = api_planets.get(planet) or {}
        sw_p = sw_planets.get(planet) or {}

        # current_sign (1-12)
        assert api_p.get("current_sign") == sw_p.get("current_sign"), (
            f"[{label}] {planet}.current_sign: API={api_p.get('current_sign')}  Swiss={sw_p.get('current_sign')}"
        )

        # nakshatra name (normalize AstrologyAPI's non-standard spellings)
        api_nak = _norm_nak(api_p.get("nakshatra"))
        sw_nak = sw_p.get("nakshatra")
        assert api_nak == sw_nak, (
            f"[{label}] {planet}.nakshatra: API={api_p.get('nakshatra')!r} (→{api_nak!r})  Swiss={sw_nak!r}"
        )

        # house (Parashari whole-sign)
        assert api_p.get("house_parashari") == sw_p.get("house_parashari"), (
            f"[{label}] {planet}.house_parashari: API={api_p.get('house_parashari')}  Swiss={sw_p.get('house_parashari')}"
        )

        # retrograde flag (string "true"/"false")
        assert api_p.get("isRetro") == sw_p.get("isRetro"), (
            f"[{label}] {planet}.isRetro: API={api_p.get('isRetro')!r}  Swiss={sw_p.get('isRetro')!r}"
        )

    # --- Current major dasha lord ---
    api_major = api["current_dasha"]["major"]["planet"]
    sw_major = swiss["current_dasha"]["major"]["planet"]
    assert api_major == sw_major, (
        f"[{label}] current_dasha.major.planet: API={api_major!r}  Swiss={sw_major!r}"
    )

    # --- Sarvashtaka totals per sign ---
    api_sarva_norm = _extract_sarvashtaka(api.get("ashtakavarga", {}).get("sarvashtaka"))
    sw_sarva_norm = _extract_sarvashtaka(swiss.get("ashtakavarga", {}).get("sarvashtaka"))

    # Allow ±1 per sign: different BPHS editions have minor table variations.
    # The sign-placement agreement checked above is the primary correctness gate;
    # sarvashtaka is a derived computation that can differ by 1 bindu per sign
    # across implementations while still being correct.
    for sign_key in sw_sarva_norm:
        api_val = api_sarva_norm.get(sign_key)
        sw_val = sw_sarva_norm[sign_key]
        assert api_val is not None and abs(api_val - sw_val) <= 1, (
            f"[{label}] sarvashtaka[{sign_key}]: API={api_val}  Swiss={sw_val}  diff={None if api_val is None else api_val - sw_val}"
        )


# ---------------------------------------------------------------------------
# Tests — one async test per birth chart
# ---------------------------------------------------------------------------


async def test_parity_delhi():
    """Delhi 1990 birth: AstrologyAPI vs Swiss must agree on all categorical values."""
    api_chart = await _get_api_chart(_DELHI)
    swiss_chart = _get_swiss_chart(_DELHI)
    _assert_parity(api_chart, swiss_chart, "Delhi-1990")


async def test_parity_mumbai():
    """Mumbai 1985 birth: AstrologyAPI vs Swiss must agree on all categorical values."""
    api_chart = await _get_api_chart(_MUMBAI)
    swiss_chart = _get_swiss_chart(_MUMBAI)
    _assert_parity(api_chart, swiss_chart, "Mumbai-1985")


async def test_parity_new_york():
    """New York 1995 birth: AstrologyAPI vs Swiss must agree on all categorical values."""
    api_chart = await _get_api_chart(_NEW_YORK)
    swiss_chart = _get_swiss_chart(_NEW_YORK)
    _assert_parity(api_chart, swiss_chart, "NewYork-1995")
