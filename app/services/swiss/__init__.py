"""Swiss Ephemeris computation layer — replaces AstrologyAPI for natal chart data."""
import threading
import swisseph as swe

_AYANAMSA_MAP = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
    "yukteshwar": swe.SIDM_YUKTESHWAR,
}

_configured = False
_lock = threading.Lock()


def configure(ayanamsa: str = "lahiri") -> None:
    global _configured
    with _lock:
        if _configured:
            return
        sid_mode = _AYANAMSA_MAP.get(ayanamsa.lower(), swe.SIDM_LAHIRI)
        swe.set_sid_mode(sid_mode, 0, 0)
        _configured = True
