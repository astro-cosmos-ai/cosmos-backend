"""Dosha computations: Manglik, Kaal Sarp, Pitra, Sade Sati (transit Saturn)."""
from datetime import datetime, timezone
import swisseph as swe

_FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

_KAAL_SARP_TYPES = [
    "", "Anant", "Kulik", "Vasuki", "Shankhpal", "Padma", "Mahapadma",
    "Takshak", "Karkotak", "Shankhachud", "Ghatak", "Vishdhar", "Sheshnag",
]


def _norm(lon: float) -> float:
    return ((lon % 360) + 360) % 360


def _sign_num(lon: float) -> int:
    return int(_norm(lon) / 30) + 1


def _current_saturn_sign() -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    jd = swe.julday(now.year, now.month, now.day,
                    now.hour + now.minute / 60.0 + now.second / 3600.0,
                    swe.GREG_CAL)
    try:
        xx, _ = swe.calc_ut(jd, swe.SATURN, _FLAGS)
        sn = _sign_num(xx[0])
        return _SIGNS[sn - 1], sn
    except Exception:
        return "", 0


def compute_doshas(planets: dict[str, dict], asc_sign: int) -> dict:
    mars = planets["mars"]
    jup = planets["jupiter"]
    venus = planets["venus"]
    sun = planets["sun"]
    moon = planets["moon"]
    rahu = planets["rahu"]
    ketu = planets["ketu"]
    saturn_natal = planets["saturn"]

    # ── Manglik ──────────────────────────────────────────────────────────────
    manglik_houses = [1, 2, 4, 7, 8, 12]
    mars_house = mars["house_parashari"]
    manglik_present = mars_house in manglik_houses

    present_rules: list[str] = []
    cancel_rules: list[str] = []
    aspect_rules: list[str] = []

    if manglik_present:
        present_rules.append(f"Mars sits in House {mars_house} ({mars['sign']}) from the ascendant.")
        mars_sign = mars["sign"]
        if mars_sign in ("Aries", "Scorpio"):
            cancel_rules.append(f"Mars is in its own sign ({mars_sign}) — energy flows naturally.")
        if mars_sign == "Capricorn":
            cancel_rules.append("Mars is exalted in Capricorn — constructive energy.")
        if mars_house == 2 and mars_sign in ("Gemini", "Virgo"):
            cancel_rules.append("Mars in 2nd in a Mercury sign — cancels Manglik.")
        if mars_house == 7 and mars_sign == "Cancer":
            cancel_rules.append("Mars in 7th in Cancer — cancels Manglik.")
        if mars_house == 8 and mars_sign in ("Sagittarius", "Pisces"):
            cancel_rules.append("Mars in 8th in a Jupiter sign — cancels Manglik.")
        if mars_house == 12 and mars_sign in ("Taurus", "Libra"):
            cancel_rules.append("Mars in 12th in a Venus sign — cancels Manglik.")
        if jup["house_parashari"] == mars_house:
            cancel_rules.append("Jupiter shares the house with Mars — softens significantly.")
        if venus["house_parashari"] == mars_house:
            cancel_rules.append("Venus shares the house with Mars — gentle influence.")
        jup_h = jup["house_parashari"]
        jup_aspects = [((jup_h - 1 + d) % 12) + 1 for d in [4, 6, 8]]
        if mars_house in jup_aspects:
            aspect_rules.append("Jupiter aspects Mars — wisdom moderates the heat.")

    cancellations = len(cancel_rules)
    percent = max(25, 100 - cancellations * 30) if manglik_present else 0
    cancelled = manglik_present and cancellations >= 2

    # ── Kaal Sarp ────────────────────────────────────────────────────────────
    rahu_lon = _norm(rahu["fullDegree"])
    sevens = [sun, moon, mars, planets["mercury"], jup, venus, saturn_natal]

    def in_arc(lon_raw: float) -> bool:
        lon = _norm(lon_raw)
        rel = (lon - rahu_lon + 360) % 360
        return 0 < rel < 180

    on_side_a = all(in_arc(p["fullDegree"]) for p in sevens)
    on_side_b = all(not in_arc(p["fullDegree"]) and _norm(p["fullDegree"]) != rahu_lon for p in sevens)
    kaal_sarp = on_side_a or on_side_b
    ks_type = _KAAL_SARP_TYPES[rahu["house_parashari"]] if kaal_sarp else ""
    ks_summary = (
        f"{ks_type} Kaal Sarp Yoga — Rahu in House {rahu['house_parashari']}, Ketu in House {ketu['house_parashari']}."
        if kaal_sarp else "Planets are not fully enclosed between Rahu and Ketu."
    )

    # ── Pitra Dosha ──────────────────────────────────────────────────────────
    pitra = False
    pitra_summary = "No Pitra Dosha detected in this chart."
    if sun["house_parashari"] == rahu["house_parashari"]:
        pitra = True
        pitra_summary = f"Sun conjunct Rahu in House {sun['house_parashari']} — classic Pitra Dosha indicator."
    elif sun["house_parashari"] == ketu["house_parashari"]:
        pitra = True
        pitra_summary = f"Sun conjunct Ketu in House {sun['house_parashari']} — Pitra Dosha indication."
    elif sun["house_parashari"] == 9 and any(
        p["house_parashari"] == 9 for p in [saturn_natal, rahu, ketu]
    ):
        pitra = True
        pitra_summary = "Sun in 9th house with malefic affliction — Pitra Dosha indication."

    # ── Sade Sati (transit Saturn vs natal Moon) ──────────────────────────────
    moon_sign = moon["sign"]
    moon_sign_num = _sign_num(moon["fullDegree"])
    sat_now_sign, sat_now_num = _current_saturn_sign()
    if not sat_now_num:
        sat_now_sign = saturn_natal["sign"]
        sat_now_num = _sign_num(saturn_natal["fullDegree"])

    from_moon = ((sat_now_num - moon_sign_num + 12) % 12) + 1
    sade_active = from_moon in (12, 1, 2)
    phase_map = {12: "Rising (Phase 1)", 1: "Peak (Phase 2)", 2: "Setting (Phase 3)"}
    phase = phase_map.get(from_moon, "")
    if sade_active:
        sade_summary = (
            f"Saturn currently transits {sat_now_sign}, "
            f"{'12th' if from_moon == 12 else '1st' if from_moon == 1 else '2nd'} "
            f"from your Moon sign {moon_sign}. {phase}."
        )
    else:
        sade_summary = (
            f"Saturn is in {sat_now_sign}, {from_moon} houses from your Moon. Sade Sati is not active."
        )

    return {
        "manglik": {
            "present": manglik_present,
            "status": ("CANCELLED" if cancelled else "EFFECTIVE") if manglik_present else "",
            "report": " ".join(present_rules),
            "cancelRules": cancel_rules,
            "presentRules": present_rules,
            "aspectRules": aspect_rules,
            "percent": percent,
            "cancelled": cancelled,
        },
        "kalsarpa": {"present": kaal_sarp, "summary": ks_summary, "intro": ""},
        "pitra": {"present": pitra, "summary": pitra_summary, "intro": ""},
        "sadhesati": {
            "present": sade_active,
            "moonSign": moon_sign,
            "saturnSign": sat_now_sign,
            "summary": sade_summary,
            "intro": "",
        },
    }
